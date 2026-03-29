"""
Celery Worker — Background Jobs
Monthly model retraining + email alerts + drift monitoring
"""

import os
import json
from datetime import datetime

import joblib
import numpy as np
import redis
from sklearn.metrics import brier_score_loss, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from backend import models
from backend.db_pg import (
    add_drift_alert,
    execute,
    fetch_latest_deployed_model,
    init_db_schema,
    insert_model_version,
)
from celery import Celery
from celery.schedules import crontab
from flask_socketio import SocketIO

broker = os.environ.get("CELERY_BROKER", "redis://localhost:6379/1")
app = Celery("novacura", broker=broker, backend=broker)

init_db_schema()

app.conf.beat_schedule = {
    # Retrain weekly on Sunday at 2am
    "monthly-retrain": {
        "task": "celery_worker.retrain_model_task",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
    # Check prediction drift every day at midnight
    "daily-drift-check": {
        "task": "celery_worker.check_model_drift_task",
        "schedule": crontab(hour=0, minute=0),
    },
    # Sync public datasets every Sunday 3am
    "weekly-dataset-sync": {
        "task": "celery_worker.sync_datasets_task",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
    },
}


@app.task
def retrain_model_task():
    """Retrain stacked ensemble from labeled training_data and deploy only on AUC improvement."""
    rows = execute(
        """
        SELECT toxicity, bioavailability, solubility, binding, molecular_weight, label
        FROM training_data
        WHERE label IS NOT NULL
        """,
        fetch="all",
    ) or []
    if len(rows) < 50:
        return {"success": False, "error": f"Need at least 50 labeled rows, found {len(rows)}"}

    X = np.array(
        [[r["toxicity"], r["bioavailability"], r["solubility"], r["binding"], r["molecular_weight"]] for r in rows],
        dtype=float,
    )
    y = np.array([int(r["label"]) for r in rows], dtype=int)

    X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.1, random_state=42, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.1111, random_state=42, stratify=y_temp)

    ensemble = models.train_ensemble(X_train, y_train)
    val_preds = []
    test_preds = []
    for row in X_val:
        val_preds.append(models.predict_ensemble(ensemble, row.tolist())["ensemble_probability"])
    for row in X_test:
        test_preds.append(models.predict_ensemble(ensemble, row.tolist())["ensemble_probability"])

    val_auc = float(roc_auc_score(y_val, np.array(val_preds)))
    val_f1 = float(f1_score(y_val, np.array(val_preds) >= 0.5))
    val_brier = float(brier_score_loss(y_val, np.array(val_preds)))
    test_auc = float(roc_auc_score(y_test, np.array(test_preds)))
    test_f1 = float(f1_score(y_test, np.array(test_preds) >= 0.5))
    test_brier = float(brier_score_loss(y_test, np.array(test_preds)))

    deployed_row = fetch_latest_deployed_model() or {}
    previous_auc = float(deployed_row.get("val_auc") or 0.0)
    deploy = val_auc > previous_auc

    version = datetime.utcnow().strftime("%Y.%m.%d.%H%M%S")
    artifact_path = models.ENSEMBLE_DIR
    stats_payload = {
        "feature_names": models.FEATURE_NAMES,
        "mean": {name: float(np.mean(X_train[:, i])) for i, name in enumerate(models.FEATURE_NAMES)},
        "std": {name: float(np.std(X_train[:, i]) + 1e-9) for i, name in enumerate(models.FEATURE_NAMES)},
    }
    with open(os.path.join(artifact_path, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats_payload, f, indent=2)

    row = insert_model_version(
        {
            "version": version,
            "algorithm": "stacked_ensemble",
            "training_dataset_size": int(len(X_train)),
            "val_auc": val_auc,
            "val_f1": val_f1,
            "val_brier": val_brier,
            "artifact_path": artifact_path,
            "deployed": deploy,
        }
    )

    if deploy:
        joblib.dump(ensemble.get("base_models", {}).get("rf"), models.MODEL_PATH)
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                redis.from_url(redis_url).set("model_reload_required", "1")
        except Exception:
            pass

    _emit_socket_event(
        "retrain_complete",
        {
            "version": version,
            "val_auc": round(val_auc, 4),
            "test_auc": round(test_auc, 4),
            "test_f1": round(test_f1, 4),
            "test_brier": round(test_brier, 4),
            "deployed": deploy,
        },
    )

    return {
        "success": True,
        "version": version,
        "previous_val_auc": round(previous_auc, 4),
        "val_auc": round(val_auc, 4),
        "val_f1": round(val_f1, 4),
        "val_brier": round(val_brier, 4),
        "test_auc": round(test_auc, 4),
        "test_f1": round(test_f1, 4),
        "test_brier": round(test_brier, 4),
        "deployed": deploy,
        "model_version_row": row,
    }


@app.task
def check_model_drift_task(threshold: float = 0.3):
    """Compute KL divergence for last 500 predictions against stored training stats."""
    latest = fetch_latest_deployed_model()
    if not latest:
        return {"success": False, "error": "No deployed model version found"}

    stats_path = os.path.join(str(latest["artifact_path"]), "stats.json")
    if not os.path.exists(stats_path):
        return {"success": False, "error": f"Training stats not found at {stats_path}"}

    with open(stats_path, "r", encoding="utf-8") as f:
        stats = json.load(f)

    rows = execute(
        """
        SELECT input_params
        FROM predictions
        ORDER BY created_at DESC
        LIMIT 500
        """,
        fetch="all",
    ) or []
    if len(rows) < 500:
        return {"success": False, "error": f"Need 500 predictions, found {len(rows)}"}

    alerts = []
    for feature in models.FEATURE_NAMES:
        vals = []
        for row in rows:
            params = row["input_params"] or {}
            try:
                vals.append(float(params.get(feature, 0.0)))
            except Exception:
                vals.append(0.0)

        obs_mean = float(np.mean(vals))
        obs_std = float(np.std(vals) + 1e-9)
        tr_mean = float(stats.get("mean", {}).get(feature, 0.0))
        tr_std = float(stats.get("std", {}).get(feature, 1e-6))

        kl = float(np.log(tr_std / obs_std) + ((obs_std**2 + (obs_mean - tr_mean) ** 2) / (2 * tr_std**2)) - 0.5)
        if kl > threshold:
            alert = add_drift_alert(feature, kl)
            alerts.append(alert)
            _emit_socket_event("model_drift_alert", alert)

    return {
        "success": True,
        "checked_predictions": len(rows),
        "alerts_triggered": len(alerts),
        "alerts": alerts,
        "threshold": threshold,
    }


@app.task
def sync_datasets_task():
    from backend.tasks.data_pipeline import sync_datasets_task as impl

    return impl()


# Backward-compatible aliases
@app.task(name="celery_worker.retrain_model")
def retrain_model():
    return retrain_model_task()


@app.task(name="celery_worker.check_drift")
def check_drift():
    return check_model_drift_task()


def _emit_socket_event(event: str, payload: dict):
    """Emit worker-side Socket.IO event through Redis message queue when configured."""
    try:
        mq = os.getenv("SOCKETIO_MESSAGE_QUEUE") or os.getenv("REDIS_URL")
        if not mq:
            return
        sio = SocketIO(message_queue=mq)
        sio.emit(event, payload)
    except Exception:
        return
