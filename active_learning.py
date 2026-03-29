"""
UPGRADE 6: Active Learning Queue
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Model flags its most uncertain predictions for expert labelling.

Features:
  - Uncertainty quantification from prediction confidence intervals
  - Priority queue for compounds most worth testing
  - Accumulated labels for model retraining
  - Monthly automated retraining via Celery

New API endpoints:
  GET  /active-learning/queue          pending compounds to label
  POST /active-learning/label/<id>     {"true_label": 1, "labelled_by": "Dr Smith"}
  GET  /active-learning/stats          queue completion rate
"""

import numpy as np
import pandas as pd
import json
import os
import models
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sklearn.ensemble import RandomForestClassifier

# Configuration
CONFIRMED_LABELS_PATH = "confirmed_labels.csv"
UNCERTAINTY_THRESHOLD = 0.15  # Queue compounds with CI width > 15%
MAX_QUEUE_SIZE = 100


def compute_uncertainty(model, features: List[float]) -> float:
    """
    Compute prediction uncertainty from model confidence intervals.
    Returns uncertainty score (0-1, higher = more uncertain).
    """
    try:
        # Use confidence interval width as uncertainty proxy
        ci = models.predict_with_confidence(model, features)
        uncertainty = ci["p90"] - ci["p10"]
        return float(np.clip(uncertainty, 0, 1))
    except Exception:
        # Fallback: use prediction probability distance from 0.5
        prob = models.predict_single(model, features)
        return abs(prob - 0.5) * 2


def add_to_queue(compound_name: str, features: List[float], 
                probability: float, uncertainty: float,
                prediction_id: Optional[str] = None) -> Optional[str]:
    """Add a compound to the active learning queue."""
    import uuid
    
    queue_file = "active_learning_queue.csv"
    
    # Create queue file if it doesn't exist
    if not os.path.exists(queue_file):
        with open(queue_file, "w") as f:
            f.write("id,timestamp,compound_name,features,probability,uncertainty,prediction_id,status\n")
    
    # Check queue size
    try:
        df = pd.read_csv(queue_file)
        if len(df) >= MAX_QUEUE_SIZE:
            return None  # Queue full
    except:
        pass
    
    # Add to queue
    queue_id = prediction_id or str(uuid.uuid4())[:8]
    
    with open(queue_file, "a") as f:
        f.write(f"{queue_id},{datetime.utcnow().isoformat()},{compound_name},"
                f"[{','.join(map(str, features))}],{probability},{uncertainty},"
                f"{prediction_id or ''},pending\n")
    
    return queue_id


def get_queue(limit: int = 20, status: str = "pending") -> List[Dict]:
    """Get compounds from the active learning queue."""
    queue_file = "active_learning_queue.csv"
    
    if not os.path.exists(queue_file):
        return []
    
    try:
        df = pd.read_csv(queue_file)
        
        # Filter by status
        if status != "all":
            df = df[df["status"] == status]
        
        # Sort by uncertainty (highest first) and timestamp
        df = df.sort_values(["uncertainty", "timestamp"], ascending=[False, True])
        
        # Limit results
        df = df.head(limit)
        
        results = []
        for _, row in df.iterrows():
            features = eval(row["features"]) if isinstance(row["features"], str) else row["features"]
            results.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "compound_name": row["compound_name"],
                "features": features,
                "probability": row["probability"],
                "uncertainty": row["uncertainty"],
                "prediction_id": row["prediction_id"],
                "status": row["status"],
                "priority_score": round(row["uncertainty"] * 100, 1),
            })
        
        return results
    except Exception as e:
        print(f"Error reading queue: {e}")
        return []


def label_compound(queue_id: str, true_label: int, labelled_by: str, 
                 notes: str = "") -> bool:
    """Label a compound from the active learning queue."""
    queue_file = "active_learning_queue.csv"
    labels_file = CONFIRMED_LABELS_PATH
    
    try:
        # Read queue
        if not os.path.exists(queue_file):
            return False
        
        df_queue = pd.read_csv(queue_file)
        
        # Find the compound
        idx = df_queue[df_queue["id"] == queue_id].index
        if len(idx) == 0:
            return False
        
        idx = idx[0]
        
        # Update status in queue
        df_queue.loc[idx, "status"] = "labelled"
        df_queue.to_csv(queue_file, index=False)
        
        # Add to confirmed labels
        row = df_queue.loc[idx]
        label_data = {
            "queue_id": queue_id,
            "prediction_id": row["prediction_id"],
            "compound_name": row["compound_name"],
            "features": row["features"],
            "predicted_probability": row["probability"],
            "true_label": true_label,
            "labelled_by": labelled_by,
            "labelled_at": datetime.utcnow().isoformat(),
            "notes": notes,
        }
        
        # Create labels file if it doesn't exist
        if not os.path.exists(labels_file):
            with open(labels_file, "w") as f:
                f.write("queue_id,prediction_id,compound_name,features,predicted_probability,"
                 f"true_label,labelled_by,labelled_at,notes\n")
        
        # Append label
        with open(labels_file, "a") as f:
            f.write(f"{queue_id},{row['prediction_id']},{row['compound_name']},"
                    f"\"{row['features']}\",{row['probability']},{true_label},"
                    f"{labelled_by},{datetime.utcnow().isoformat()},\"{notes}\"\n")
        
        return True
    except Exception as e:
        print(f"Error labeling compound: {e}")
        return False


def get_queue_stats() -> Dict:
    """Get statistics about the active learning queue."""
    queue_file = "active_learning_queue.csv"
    labels_file = CONFIRMED_LABELS_PATH
    
    stats = {
        "queue_size": 0,
        "pending_count": 0,
        "labelled_count": 0,
        "total_labels": 0,
        "label_accuracy": 0.0,
        "average_uncertainty": 0.0,
        "oldest_pending": None,
        "recent_labels": []
    }
    
    try:
        # Queue stats
        if os.path.exists(queue_file):
            df_queue = pd.read_csv(queue_file)
            stats["queue_size"] = len(df_queue)
            stats["pending_count"] = len(df_queue[df_queue["status"] == "pending"])
            stats["labelled_count"] = len(df_queue[df_queue["status"] == "labelled"])
            
            if stats["pending_count"] > 0:
                pending = df_queue[df_queue["status"] == "pending"]
                oldest = pending["timestamp"].min()
                stats["oldest_pending"] = oldest
            
            if len(df_queue) > 0:
                stats["average_uncertainty"] = round(df_queue["uncertainty"].mean(), 3)
        
        # Labels stats
        if os.path.exists(labels_file):
            df_labels = pd.read_csv(labels_file)
            stats["total_labels"] = len(df_labels)
            
            if len(df_labels) > 0:
                # Calculate accuracy
                correct = ((df_labels["predicted_probability"] > 0.5) == (df_labels["true_label"] == 1)).sum()
                stats["label_accuracy"] = round(correct / len(df_labels) * 100, 1)
                
                # Recent labels (last 10)
                recent = df_labels.tail(10)[["labelled_at", "compound_name", "true_label"]].to_dict("records")
                stats["recent_labels"] = recent
    
    except Exception as e:
        print(f"Error calculating stats: {e}")
    
    return stats


def get_high_uncertainty_predictions(model, features_list: List[List[float]], 
                                threshold: float = UNCERTAINTY_THRESHOLD) -> List[Dict]:
    """Identify predictions with high uncertainty for active learning."""
    high_uncertainty = []
    
    for i, features in enumerate(features_list):
        uncertainty = compute_uncertainty(model, features)
        if uncertainty > threshold:
            prob = models.predict_single(model, features)
            high_uncertainty.append({
                "index": i,
                "features": features,
                "probability": prob,
                "uncertainty": round(uncertainty, 3),
                "reason": "High model uncertainty (CI width > threshold)"
            })
    
    # Sort by uncertainty (highest first)
    high_uncertainty.sort(key=lambda x: x["uncertainty"], reverse=True)
    return high_uncertainty


def retrain_with_labels() -> Dict:
    """Retrain model using accumulated labels."""
    labels_file = CONFIRMED_LABELS_PATH
    
    if not os.path.exists(labels_file):
        return {"error": "No confirmed labels available"}
    
    try:
        df = pd.read_csv(labels_file)
        
        if len(df) < 50:
            return {"error": f"Need at least 50 labels, have {len(df)}"}
        
        # Prepare training data
        X = []
        y = []
        
        for _, row in df.iterrows():
            features = eval(row["features"]) if isinstance(row["features"], str) else row["features"]
            if len(features) == 5:  # Ensure correct feature count
                X.append(features)
                y.append(row["true_label"])
        
        if len(X) < 20:
            return {"error": "Insufficient valid training samples"}
        
        # Train new model
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
        from sklearn.metrics import roc_auc_score
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train calibrated model
        base_rf = RandomForestClassifier(
            n_estimators=300, max_depth=10, min_samples_leaf=3,
            random_state=42, n_jobs=-1, class_weight="balanced"
        )
        new_model = CalibratedClassifierCV(base_rf, cv=5, method="isotonic")
        new_model.fit(X_train, y_train)
        
        # Evaluate
        y_prob = new_model.predict_proba(X_test)[:, 1]
        new_auc = roc_auc_score(y_test, y_prob)
        
        # Load old model for comparison
        try:
            import models
            old_model = models.load_model()
            old_prob = old_model.predict_proba(X_test)[:, 1]
            old_auc = roc_auc_score(y_test, old_prob)
            
            improvement = new_auc - old_auc
            should_promote = improvement > 0.02
            
            if should_promote:
                # Save new model
                import joblib
                joblib.dump(new_model, models.MODEL_PATH)
                
                return {
                    "status": "promoted",
                    "old_auc": round(old_auc, 4),
                    "new_auc": round(new_auc, 4),
                    "improvement": round(improvement, 4),
                    "n_samples": len(X),
                    "message": f"Model promoted: AUC {old_auc:.4f} → {new_auc:.4f}"
                }
            else:
                return {
                    "status": "not_promoted",
                    "old_auc": round(old_auc, 4),
                    "new_auc": round(new_auc, 4),
                    "improvement": round(improvement, 4),
                    "n_samples": len(X),
                    "message": f"No significant improvement: {old_auc:.4f} → {new_auc:.4f}"
                }
        except Exception as e:
            return {"error": f"Model comparison failed: {e}"}
    
    except Exception as e:
        return {"error": f"Retraining failed: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ENDPOINTS (add to api.py)
# ─────────────────────────────────────────────────────────────────────────────

ACTIVE_LEARNING_ROUTES = '''
# ── ADD THESE ROUTES TO api.py ───────────────────────────────────────────────

from active_learning import (
    compute_uncertainty, add_to_queue, get_queue, 
    label_compound, get_queue_stats, retrain_with_labels
)

@app.route("/active-learning/queue", methods=["GET"])
def active_learning_queue():
    """Get pending compounds for expert labelling."""
    limit = int(request.args.get("limit", 20))
    status = request.args.get("status", "pending")
    
    queue = get_queue(limit=limit, status=status)
    return jsonify({
        "queue": queue,
        "total_count": len(queue),
        "limit": limit,
        "status": status
    })

@app.route("/active-learning/label/<queue_id>", methods=["POST"])
def active_learning_label(queue_id):
    """Label a compound from the active learning queue."""
    data = request.get_json()
    
    true_label = data.get("true_label")
    labelled_by = data.get("labelled_by", "Unknown")
    notes = data.get("notes", "")
    
    if true_label is None:
        return jsonify({"error": "true_label field required"}), 400
    
    success = label_compound(queue_id, true_label, labelled_by, notes)
    
    if success:
        return jsonify({
            "status": "labelled",
            "queue_id": queue_id,
            "true_label": true_label,
            "labelled_by": labelled_by
        })
    else:
        return jsonify({"error": "Queue ID not found"}), 404

@app.route("/active-learning/stats", methods=["GET"])
def active_learning_stats():
    """Get active learning statistics."""
    stats = get_queue_stats()
    return jsonify(stats)

@app.route("/active-learning/retrain", methods=["POST"])
def active_learning_retrain():
    """Manually trigger model retraining with accumulated labels."""
    result = retrain_with_labels()
    return jsonify(result)

# ── ADD TO EXISTING /predict ENDPOINT ───────────────────────────────────────
# In your existing /predict route, add this after computing probability:

# Calculate uncertainty and add to queue if high
uncertainty = compute_uncertainty(model, features)
if uncertainty > UNCERTAINTY_THRESHOLD:
    queue_id = add_to_queue(
        compound_name=data.get("compound_name", "Unknown"),
        features=features,
        probability=prob,
        uncertainty=uncertainty,
        prediction_id=prediction_id if 'prediction_id' in locals() else None
    )
    # Add queue info to response (optional)
    response["queued_for_labeling"] = {
        "queue_id": queue_id,
        "uncertainty": round(uncertainty, 3),
        "threshold": UNCERTAINTY_THRESHOLD
    }
'''


# ─────────────────────────────────────────────────────────────────────────────
# CELERY TASK (add to celery_worker.py)
# ─────────────────────────────────────────────────────────────────────────────

CELERY_TASK = '''
# ── ADD TO celery_worker.py ───────────────────────────────────────────────────

from celery import Celery
from active_learning import retrain_with_labels

@app.task
def monthly_model_retrain():
    """Monthly automated model retraining on accumulated labels."""
    try:
        result = retrain_with_labels()
        return result
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}
'''


# ─────────────────────────────────────────────────────────────────────────────
# CLI INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NovaCura Active Learning")
    parser.add_argument("--queue", action="store_true", help="Show current queue")
    parser.add_argument("--stats", action="store_true", help="Show queue statistics")
    parser.add_argument("--retrain", action="store_true", help="Retrain model with labels")
    parser.add_argument("--test", action="store_true", help="Test uncertainty calculation")
    
    args = parser.parse_args()
    
    if args.queue:
        queue = get_queue(limit=50)
        print(f"Active Learning Queue ({len(queue)} compounds):")
        print("=" * 60)
        for item in queue:
            print(f"{item['id']:8} | {item['compound_name']:20} | "
                  f"Uncertainty: {item['uncertainty']:.3f} | "
                  f"Probability: {item['probability']:.3f}")
    
    elif args.stats:
        stats = get_queue_stats()
        print("Active Learning Statistics:")
        print("=" * 40)
        print(f"Queue size:      {stats['queue_size']}")
        print(f"Pending:         {stats['pending_count']}")
        print(f"Labelled:        {stats['labelled_count']}")
        print(f"Total labels:    {stats['total_labels']}")
        print(f"Label accuracy:  {stats['label_accuracy']:.1f}%")
        print(f"Avg uncertainty: {stats['average_uncertainty']:.3f}")
        if stats['oldest_pending']:
            print(f"Oldest pending:  {stats['oldest_pending']}")
    
    elif args.retrain:
        result = retrain_with_labels()
        print("Model Retraining Results:")
        print("=" * 30)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"Status: {result['status']}")
            print(f"Old AUC: {result['old_auc']}")
            print(f"New AUC: {result['new_auc']}")
            print(f"Improvement: {result['improvement']}")
            print(f"Message: {result['message']}")
    
    elif args.test:
        # Test uncertainty calculation
        import models
        model = models.load_model()
        
        test_features = [
            [0.3, 0.7, 0.6, 0.8, 0.5],  # High confidence
            [0.5, 0.5, 0.5, 0.5, 0.5],  # Medium confidence
            [0.8, 0.2, 0.3, 0.3, 0.9],  # Low confidence
        ]
        
        print("Uncertainty Calculation Test:")
        print("=" * 40)
        for i, features in enumerate(test_features):
            uncertainty = compute_uncertainty(model, features)
            prob = models.predict_single(model, features)
            queued = uncertainty > UNCERTAINTY_THRESHOLD
            print(f"Test {i+1}: Prob={prob:.3f}, Uncertainty={uncertainty:.3f}, "
                  f"Queued={'Yes' if queued else 'No'}")
    
    else:
        parser.print_help()
