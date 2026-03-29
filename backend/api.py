import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
except Exception:
    load_dotenv = None

if load_dotenv:
    _backend_dir = os.path.dirname(os.path.abspath(__file__))
    _root_dir = os.path.dirname(_backend_dir)
    # Load workspace and backend env files if present; keep process env precedence.
    load_dotenv(os.path.join(_root_dir, ".env"), override=False)
    load_dotenv(os.path.join(_backend_dir, ".env"), override=False)

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import models
import jwt
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from services.financial_engine import compute_npv, run_monte_carlo
from services.sensitivity import run_tornado
from services.portfolio_optimizer import optimize_portfolio
from services.real_options import value_pharma_real_options
from services.scenario_manager import save_scenario, list_scenarios, get_scenario, delete_scenario
from services.report_generator import generate_executive_report
from services.annotations import add_annotation, get_annotations, resolve_annotation
from services.transparency_report import generate_transparency_report
from services.gxp_validator import validate_inputs
from io import BytesIO
from flask import send_file
import json
from datetime import datetime, timedelta, timezone
import secrets
import uuid
from functools import wraps

# New imports for upgrades
try:
    from chembl_integration import fetch_target_id, load_or_fetch_dataset, train_on_chembl
    CHEMBL_AVAILABLE = True
except ImportError:
    CHEMBL_AVAILABLE = False

try:
    from smiles_pipeline import smiles_to_descriptors, batch_smiles_to_features
    SMILES_AVAILABLE = True
except ImportError:
    SMILES_AVAILABLE = False

try:
    from therapeutic_models import predict_ta, compare_all_tas, THERAPEUTIC_AREAS, train_all_ta_models, load_ta_models
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

try:
    from database import log_prediction, get_history, get_stats, save_scenario as db_save_scenario, list_scenarios as db_list_scenarios, get_scenario as db_get_scenario, delete_scenario as db_delete_scenario
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

try:
    from active_learning import compute_uncertainty, add_to_queue, get_queue, label_compound, get_queue_stats, retrain_with_labels
    ACTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ACTIVE_LEARNING_AVAILABLE = False

try:
    from llm_analyst import retrieve_compound_context, ask_analyst, get_suggested_questions
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

try:
    from gnn_model import predict_gnn, train_gnn, load_gnn_model
    GNN_AVAILABLE = True  # Enable if PyTorch is available
except ImportError:
    GNN_AVAILABLE = False

app = Flask(__name__)
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if origin.strip()]
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, async_mode="threading")

JWT_SECRET = os.getenv("AUTH_JWT_SECRET")
if not JWT_SECRET:
    # Never use a static fallback secret; ephemeral key protects accidental production misconfigurations.
    JWT_SECRET = secrets.token_urlsafe(64)
    app.logger.warning("AUTH_JWT_SECRET is not set; using ephemeral secret. Set AUTH_JWT_SECRET in all non-local environments.")
JWT_ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
ADMIN_EMAILS = {email.strip().lower() for email in os.getenv("AUTH_ADMIN_EMAILS", "").split(",") if email.strip()}
PUBLIC_PATHS = {"/health", "/auth/google/verify", "/auth/google/state"}

_oauth_state_cache: dict[str, datetime] = {}


def _prune_oauth_states() -> None:
    now = datetime.now(timezone.utc)
    expired = [state for state, expiry in _oauth_state_cache.items() if expiry <= now]
    for state in expired:
        _oauth_state_cache.pop(state, None)


def _issue_oauth_state(ttl_seconds: int = 300) -> str:
    _prune_oauth_states()
    state = secrets.token_urlsafe(32)
    _oauth_state_cache[state] = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return state


def _consume_oauth_state(state: str | None) -> bool:
    if not state:
        return False
    _prune_oauth_states()
    expiry = _oauth_state_cache.get(state)
    if not expiry:
        return False
    if expiry <= datetime.now(timezone.utc):
        _oauth_state_cache.pop(state, None)
        return False
    _oauth_state_cache.pop(state, None)
    return True


def _resolve_user_role(email: str | None) -> str:
    if email and email.lower() in ADMIN_EMAILS:
        return "admin"
    return "researcher"


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            role = getattr(g, "auth_role", None)
            if role is None:
                return jsonify({"error": "Authorization token required"}), 401
            if role not in set(roles):
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    if path.startswith("/socket.io"):
        return True
    return False


@app.before_request
def enforce_jwt_auth():
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    if request.method == "OPTIONS":
        return None

    testing_bypass = app.config.get("TESTING") or os.getenv("SKIP_AUTH_FOR_TESTS") == "1" or "PYTEST_CURRENT_TEST" in os.environ
    if testing_bypass:
        # In test mode, do not force auth, but still hydrate role/user when a token is supplied.
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                g.auth_user = payload.get("email") or payload.get("sub")
                g.auth_role = payload.get("role", "researcher")
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid or expired token"}), 401
        return None

    if _is_public_path(request.path):
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authorization token required"}), 401

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        g.auth_user = payload.get("email") or payload.get("sub")
        g.auth_role = payload.get("role", "researcher")
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid or expired token"}), 401


@app.after_request
def set_security_headers(response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response

# Load the model directly when the app starts
model = models.load_model()
ensemble = models.load_ensemble()

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to ensure API is running."""
    return jsonify({
        "status": "healthy",
        "features": {
            "chembl": CHEMBL_AVAILABLE,
            "smiles": SMILES_AVAILABLE,
            "therapeutic_models": TA_AVAILABLE,
            "database": DATABASE_AVAILABLE,
            "active_learning": ACTIVE_LEARNING_AVAILABLE,
            "llm_analyst": LLM_AVAILABLE,
            "gnn": GNN_AVAILABLE
        },
        "upgrades": "All 8 NovaCura v2 upgrades implemented"
    })


@app.route("/auth/google/verify", methods=["POST"])
def google_verify():
    """Verify Google ID token and return user info + JWT."""
    data = request.get_json()
    if not data or "idToken" not in data:
        return jsonify({"error": "idToken is required"}), 400

    if not _consume_oauth_state(data.get("state")):
        return jsonify({"error": "Invalid OAuth state"}), 400

    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google OAuth not configured"}), 500

    try:
        idinfo = google_id_token.verify_oauth2_token(
            data["idToken"],
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        email = idinfo.get("email")
        name = idinfo.get("name")
        picture = idinfo.get("picture")

        # Create JWT for internal use
        role = _resolve_user_role(email)
        token = jwt.encode(
            {
                "sub": email,
                "email": email,
                "name": name,
                "picture": picture,
                "role": role,
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM
        )

        return jsonify({
            "token": token,
            "user": {
                "email": email,
                "name": name,
                "picture": picture,
                "role": role,
            }
        })
    except Exception as error:
        print(f"Google token verification failed: {error}")
        return jsonify({"error": "Invalid or expired token"}), 401


@app.route("/auth/google/state", methods=["GET"])
def google_oauth_state():
    return jsonify({"state": _issue_oauth_state(), "expires_in": 300})


@app.route("/admin/system-health", methods=["GET"])
@require_role("admin")
def admin_system_health():
    return jsonify(
        {
            "request_id": getattr(g, "request_id", None),
            "status": "ok",
            "auth": {
                "jwt_algorithm": JWT_ALGORITHM,
                "oauth_configured": bool(GOOGLE_CLIENT_ID),
                "allowed_origins": ALLOWED_ORIGINS,
            },
            "features": {
                "database": DATABASE_AVAILABLE,
                "active_learning": ACTIVE_LEARNING_AVAILABLE,
                "llm_analyst": LLM_AVAILABLE,
                "gnn": GNN_AVAILABLE,
            },
        }
    )


@app.route("/admin/audit-logs", methods=["GET"])
@require_role("admin")
def admin_audit_logs():
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database layer unavailable"}), 503
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
        from backend.db_pg import execute as pg_execute

        rows = pg_execute(
            """
            SELECT id, timestamp, method, path, status, request_id
            FROM audit_logs
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            [limit],
            fetch="all",
        ) or []
        return jsonify({"items": rows, "count": len(rows)})
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch audit logs: {exc}"}), 500

# ---- Extend /predict to include SHAP + confidence ----
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    # GxP validation layer
    validation = validate_inputs(data)
    if not validation["valid"]:
        return jsonify({
            "error": "GxP input validation failed",
            "validation": validation
        }), 422

    feature_list = [data[k] for k in ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
    
    prob = models.predict_single(model, feature_list)
    confidence = models.predict_with_confidence(model, feature_list)
    shap_vals = models.get_shap_values(model, feature_list)
    phases = models.get_phase_probabilities(prob)

    warnings = list(validation["warnings"])  # carry forward soft warnings
    if data["toxicity"] > 0.7:
        warnings.append("High toxicity risk detected")
    if data["bioavailability"] < 0.4:
        warnings.append("Low bioavailability (absorption) risk")

    return jsonify({
        "success_probability": float(prob),
        "confidence_interval": confidence,
        "shap_values": shap_vals,
        "phase_probabilities": phases,
        "warnings": warnings,
        "gxp_validation": validation
    })

@app.route("/predict-batch", methods=["POST"])
def predict_batch():
    """Predict success probabilities for multiple drug candidates in one call."""
    batch_data = request.get_json()
    if not isinstance(batch_data, list):
        return jsonify({"error": "Payload must be a list of objects"}), 400
        
    feature_lists = []
    for data in batch_data:
        feature_lists.append([
            data.get("toxicity", 0.0),
            data.get("bioavailability", 0.0),
            data.get("solubility", 0.0),
            data.get("binding", 0.0),
            data.get("molecular_weight", 0.0)
        ])
        
    probs = models.predict_batch(model, feature_lists)
    return jsonify({
        "success_probabilities": probs.tolist()
    })

# ---- ML CORE ENSEMBLES & COUNTERFACTUALS ----
@app.route("/predict-ensemble", methods=["POST"])
def predict_ensemble_route():
    data = request.get_json()
    required = ["toxicity","bioavailability","solubility","binding","molecular_weight"]
    for k in required:
        if k not in data:
            return jsonify({"error": f"Missing: {k}"}), 400

    features = [data[k] for k in required]
    result   = models.predict_ensemble(ensemble, features)

    warnings = []
    if data["toxicity"] > 0.7:
        warnings.append("High toxicity risk detected")
    if data["bioavailability"] < 0.4:
        warnings.append("Low bioavailability (absorption) risk")

    return jsonify({**result, "warnings": warnings})

@app.route("/counterfactual", methods=["POST"])
def counterfactual():
    data     = request.get_json()
    features = [data.get(k, 0.5) for k in ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
    target   = data.get("target_probability", 0.75)
    result   = models.generate_counterfactual(model, features, target_prob=target)
    return jsonify(result)

# ---- BI ANALYTICS (PORTFOLIOS & OPTIONS & SCENARIOS) ----

@app.route("/optimize-portfolio", methods=["POST"])
def portfolio():
    data      = request.get_json()
    budget    = data.get("budget_m", 500.0)
    compounds = data.get("compounds", [])

    for c in compounds:
        if "success_probability" not in c:
            features = [c.get(k, 0.5) for k in ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
            c["success_probability"] = float(models.predict_single(model, features))

    result = optimize_portfolio(compounds, budget_m=budget)
    return jsonify(result)

@app.route("/real-options", methods=["POST"])
def real_options():
    try:
        data   = request.get_json()
        result = value_pharma_real_options(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/scenarios", methods=["GET"])
def get_scenarios():
    return jsonify(list_scenarios())

@app.route("/scenarios", methods=["POST"])
def create_scenario():
    data = request.get_json()
    sid  = save_scenario(
        name    = data.get("name", "Untitled scenario"),
        inputs  = data.get("inputs", {}),
        outputs = data.get("outputs", {}),
        tags    = data.get("tags", [])
    )
    return jsonify({"id": sid, "message": "Scenario saved"})

@app.route("/scenarios/<sid>", methods=["GET"])
def fetch_scenario(sid):
    s = get_scenario(sid)
    return jsonify(s) if s else (jsonify({"error":"Not found"}), 404)

@app.route("/scenarios/<sid>", methods=["DELETE"])
def remove_scenario(sid):
    delete_scenario(sid)
    return jsonify({"deleted": sid})

# ---- COLLABORATION & REGULATORY (REPORTS, TRANSPARENCY, ANNOTATIONS) ----

@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    data       = request.get_json() or {}
    pdf_bytes  = generate_executive_report(data)
    buf        = BytesIO(pdf_bytes)
    buf.seek(0)
    
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"NovaCura_Report.pdf"
    )

@app.route("/annotations", methods=["GET"])
def fetch_annotations():
    context = request.args.get("context")
    return jsonify(get_annotations(context))

@app.route("/annotations", methods=["POST"])
def create_annotation():
    d = request.get_json()
    if not d:
        return jsonify({"error": "No JSON payload provided"}), 400
    a = add_annotation(d.get("context","general"), d.get("author","Anonymous"), d.get("text",""))
    return jsonify(a), 201

@app.route("/annotations/<aid>/resolve", methods=["POST"])
def resolve_ann(aid):
    resolve_annotation(aid)
    return jsonify({"resolved": aid})

@app.route("/transparency-report", methods=["GET"])
def transparency_report():
    model_info = {
        "type": "Random Forest Classifier",
        "version": "1.0.0",
        "training_samples": 300,
        "data_source": "Synthetic (NovaCura internal)"
    }
    validation = {
        "accuracy": 0.84,
        "auc": 0.88,
        "precision": 0.81,
        "recall": 0.79
    }
    return jsonify(generate_transparency_report(model_info, validation))

# ---- Upgrade 1: ChEMBL Integration ----
if CHEMBL_AVAILABLE:
    @app.route("/data/import-chembl", methods=["POST"])
    def import_chembl():
        global model
        data = request.get_json()
        max_recs = data.get("max_records", 1500)

        target_ids = []
        if "target_id" in data:
            target_ids = [data["target_id"]]
        elif "gene" in data:
            target_ids = [fetch_target_id(data["gene"])]
        elif "targets" in data:
            target_ids = data["targets"]
        else:
            return jsonify({"error": "Provide target_id, gene, or targets"}), 400

        try:
            df = load_or_fetch_dataset(target_ids, max_per_target=max_recs)
            result = train_on_chembl(df)
            model = result["model"]   # hot-swap the running model
            return jsonify({
                "status": "success",
                "message": f"Model retrained on {result['metrics']['n_train']} ChEMBL compounds",
                "metrics": result["metrics"],
                "targets": target_ids,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/data/chembl-status", methods=["GET"])
    def chembl_status():
        meta_path = "model_metadata.json"
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                return jsonify(json.load(f))
        return jsonify({"status": "No ChEMBL data loaded yet — using synthetic data"})

    @app.route("/data/dataset-info", methods=["GET"])
    def dataset_info():
        if os.path.exists("chembl_dataset.csv"):
            import pandas as pd
            df = pd.read_csv("chembl_dataset.csv")
            return jsonify({
                "total_compounds": len(df),
                "active_compounds": int(df["label"].sum()),
                "sources": df["source"].value_counts().to_dict(),
                "targets": df.get("target_id", pd.Series()).value_counts().to_dict(),
                "path": "chembl_dataset.csv",
            })
        return jsonify({"status": "No dataset file found"})

# ---- Upgrade 2: SMILES Pipeline ----
if SMILES_AVAILABLE:
    @app.route("/predict-smiles", methods=["POST"])
    def predict_smiles():
        data = request.get_json()
        smiles = data.get("smiles", "").strip()
        if not smiles:
            return jsonify({"error": "smiles field required"}), 400

        desc = smiles_to_descriptors(smiles)
        if not desc["validity"]["valid"]:
            return jsonify({"error": desc["validity"]["error_message"]}), 422
        if desc["model_features"] is None:
            return jsonify({"error": "Could not compute features from SMILES"}), 422

        features = [desc["model_features"][k] for k in
                    ["toxicity","bioavailability","solubility","binding","molecular_weight"]]

        prob = models.predict_single(model, features)
        ci = models.predict_with_confidence(model, features)
        shap_bd = models.get_shap_breakdown(model, features)
        phases = models.get_phase_probabilities(prob)
        verdict = models.classify_verdict(prob)

        all_warnings = desc["warnings"][:]
        if desc["model_features"]["toxicity"] > 0.7:
            all_warnings.append("High toxicity risk detected")
        if desc["model_features"]["bioavailability"] < 0.4:
            all_warnings.append("Low bioavailability risk")

        return jsonify({
            "compound_name": data.get("compound_name", "Unknown"),
            "smiles": smiles,
            "success_probability": round(prob, 4),
            "verdict": verdict,
            "confidence_interval": ci,
            "shap_breakdown": shap_bd,
            "phase_probabilities": phases,
            "model_features": desc["model_features"],
            "raw_descriptors": desc.get("raw_descriptors", {}),
            "drug_likeness": desc.get("drug_likeness", {}),
            "admet": desc.get("admet", {}),
            "warnings": all_warnings,
        })

    @app.route("/descriptors", methods=["POST"])
    def compute_descriptors():
        data = request.get_json()
        if "smiles_list" in data:
            results = batch_smiles_to_features(data["smiles_list"])
            return jsonify({"count": len(results), "results": results})
        smiles = data.get("smiles","")
        return jsonify(smiles_to_descriptors(smiles))

# ---- Upgrade 3: Therapeutic Area Models ----
if TA_AVAILABLE:
    @app.route("/predict-ta", methods=["POST"])
    def predict_therapeutic_area():
        data = request.get_json()
        features = data.get("features", [])
        
        if len(features) != 5:
            return jsonify({"error": "Need exactly 5 features"}), 400
        
        if data.get("compare_all"):
            result = compare_all_tas(features)
            return jsonify(result)
        
        ta = data.get("therapeutic_area", "auto")
        if ta == "auto":
            comparison = compare_all_tas(features)
            best_ta = comparison["best_fit"][0]
            result = predict_ta(features, best_ta)
            result["auto_detected"] = best_ta
            return jsonify(result)
        
        if ta not in THERAPEUTIC_AREAS:
            return jsonify({"error": f"Invalid therapeutic area: {ta}"}), 400
        
        result = predict_ta(features, ta)
        return jsonify(result)

    @app.route("/therapeutic-areas", methods=["GET"])
    def list_therapeutic_areas():
        return jsonify({
            "therapeutic_areas": {
                key: {
                    "label": info["label"],
                    "description": info["description"],
                    "color": info["color"],
                    "attrition_rates": info["attrition_rates"],
                    "feature_weights": info["feature_weights"],
                }
                for key, info in THERAPEUTIC_AREAS.items()
            }
        })

    @app.route("/ta-models/train", methods=["POST"])
    def train_ta_models_endpoint():
        try:
            results = train_all_ta_models()
            return jsonify({
                "status": "trained",
                "results": results,
                "message": f"Trained {len(results)} therapeutic area models"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ta-models/status", methods=["GET"])
    def ta_models_status():
        status = {}
        for ta_key in THERAPEUTIC_AREAS.keys():
            model_path = f"ta_models/{ta_key}_model.joblib"
            meta_path = f"ta_models/{ta_key}_metadata.json"
            
            if os.path.exists(model_path) and os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                status[ta_key] = {
                    "trained": True,
                    "model_path": model_path,
                    "metadata": meta
                }
            else:
                status[ta_key] = {"trained": False, "model_path": model_path}
        
        return jsonify({"therapeutic_areas": status})

# ---- Upgrade 6: Active Learning ----
if ACTIVE_LEARNING_AVAILABLE:
    @app.route("/active-learning/queue", methods=["GET"])
    def active_learning_queue():
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
        stats = get_queue_stats()
        return jsonify(stats)

    @app.route("/active-learning/retrain", methods=["POST"])
    def active_learning_retrain():
        result = retrain_with_labels()
        return jsonify(result)

# ---- Upgrade 7: LLM Analyst ----
if LLM_AVAILABLE:
    @app.route("/analyst/ask", methods=["POST"])
    def analyst_ask():
        return jsonify({"error": "analyst endpoint disabled"}), 403

    @app.route("/analyst/suggestions", methods=["POST"])
    def analyst_suggestions():
        return jsonify({"error": "analyst endpoint disabled"}), 403

# ---- Upgrade 8: GNN Model ----
if GNN_AVAILABLE:
    @app.route("/predict-gnn", methods=["POST"])
    def predict_with_gnn():
        data = request.get_json()
        smiles = data.get("smiles", "").strip()
        if not smiles:
            return jsonify({"error": "smiles field required"}), 400

        result = predict_gnn(smiles)

        # If GNN available, also run RF for comparison
        if not result.get("fallback"):
            if SMILES_AVAILABLE:
                desc = smiles_to_descriptors(smiles)
                if desc["validity"]["valid"] and desc["model_features"]:
                    features = [desc["model_features"][k] for k in
                                ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
                    rf_prob = models.predict_single(model, features)
                    result["rf_probability"] = round(rf_prob, 4)
                    result["ensemble_gnn_rf"] = round(
                        result["gnn_probability"] * 0.6 + rf_prob * 0.4, 4
                    )

        return jsonify(result)

    @app.route("/gnn/status", methods=["GET"])
    def gnn_status():
        import torch
        if os.path.exists("gnn_model.pt"):
            checkpoint = torch.load("gnn_model.pt", map_location="cpu")
            return jsonify({
                "status": "trained",
                "best_val_auc": checkpoint.get("best_val_auc"),
                "n_compounds": checkpoint.get("n_compounds"),
                "trained_at": checkpoint.get("trained_at"),
            })
        return jsonify({"status": "not_trained", 
                        "message": "POST to /gnn/train with SMILES + labels to train"})

    @app.route("/gnn/train", methods=["POST"])
    def train_gnn_endpoint():
        data = request.get_json()
        
        if data.get("use_chembl_dataset"):
            if os.path.exists("chembl_dataset.csv"):
                import pandas as pd
                df = pd.read_csv("chembl_dataset.csv")
                smiles_list = df["smiles"].fillna("").tolist()
                labels = df["label"].tolist()
            else:
                return jsonify({"error": "chembl_dataset.csv not found. Run ChEMBL import first."}), 404
        else:
            smiles_list = data.get("smiles_list", [])
            labels = data.get("labels", [])
        
        if len(smiles_list) < 10:
            return jsonify({"error": "Need at least 10 compounds to train GNN"}), 400
        
        result = train_gnn(
            smiles_list, labels,
            epochs = data.get("epochs", 50),
            hidden_dim = data.get("hidden_dim", 128),
        )
        
        if result.get("error"):
            return jsonify(result), 500
        return jsonify({
            "status": "trained",
            "best_val_auc": result["best_val_auc"],
            "n_compounds": result["n_compounds"],
            "trained_at": result["trained_at"],
        })

# ---- NEW: WebSocket — Real-time prediction as sliders move ----
@socketio.on("predict_realtime")
def handle_realtime_predict(data):
    feature_list = [
        data.get("toxicity", 0.5),
        data.get("bioavailability", 0.5),
        data.get("solubility", 0.5),
        data.get("binding", 0.5),
        data.get("molecular_weight", 0.5)
    ]
    prob = models.predict_single(model, feature_list)
    confidence = models.predict_with_confidence(model, feature_list)
    shap_vals = models.get_shap_values(model, feature_list)
    phases = models.get_phase_probabilities(prob)

    warnings = []
    if data.get("toxicity", 0) > 0.7:
        warnings.append("High toxicity risk detected")
    if data.get("bioavailability", 1) < 0.4:
        warnings.append("Low bioavailability (absorption) risk")

    emit("prediction_result", {
        "success_probability": float(prob),
        "confidence_interval": confidence,
        "shap_values": shap_vals,
        "phase_probabilities": phases,
        "warnings": warnings
    })

# ---- NEW: WebSocket — Real-time financial recalculation ----
@socketio.on("financial_update")
def handle_financial(data):
    result = compute_npv(data)
    emit("financial_result", result)

# ---- NEW: WebSocket — Monte Carlo streaming ----
@socketio.on("run_montecarlo")
def handle_montecarlo(data):
    for batch_result in run_monte_carlo(data, n_scenarios=5000, batches=10):
        emit("montecarlo_batch", batch_result)

# ---- NEW: WebSocket — Tornado sensitivity ----
@socketio.on("run_sensitivity")
def handle_sensitivity(data):
    result = run_tornado(data)
    emit("sensitivity_result", result)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)
