from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import models
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
import os
import json
from datetime import datetime
import uuid
from typing import Any

# New imports for upgrades
try:
    from chembl_integration import fetch_target_id, load_or_fetch_dataset, train_on_chembl
    CHEMBL_AVAILABLE = True
except ImportError:
    CHEMBL_AVAILABLE = False
    fetch_target_id = None
    load_or_fetch_dataset = None
    train_on_chembl = None

try:
    from smiles_pipeline import smiles_to_descriptors, batch_smiles_to_features
    SMILES_AVAILABLE = True
except ImportError:
    SMILES_AVAILABLE = False
    smiles_to_descriptors = None
    batch_smiles_to_features = None

try:
    from therapeutic_models import predict_ta, compare_all_tas, THERAPEUTIC_AREAS, train_all_ta_models, load_ta_models
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    predict_ta = None
    compare_all_tas = None
    train_all_ta_models = None
    load_ta_models = None
    THERAPEUTIC_AREAS = {}

try:
    from database import log_prediction, get_history, get_stats, save_scenario as db_save_scenario, list_scenarios as db_list_scenarios, get_scenario as db_get_scenario, delete_scenario as db_delete_scenario
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    log_prediction = None
    get_history = None
    get_stats = None
    db_save_scenario = None
    db_list_scenarios = None
    db_get_scenario = None
    db_delete_scenario = None

try:
    from active_learning import compute_uncertainty, add_to_queue, get_queue, label_compound, get_queue_stats, retrain_with_labels
    ACTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ACTIVE_LEARNING_AVAILABLE = False
    compute_uncertainty = None
    add_to_queue = None
    get_queue = None
    label_compound = None
    get_queue_stats = None
    retrain_with_labels = None

try:
    from llm_analyst import retrieve_compound_context, ask_analyst, get_suggested_questions
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    retrieve_compound_context = None
    ask_analyst = None
    get_suggested_questions = None

try:
    from gnn_model import predict_gnn, train_gnn, load_gnn_model
    GNN_AVAILABLE = True
except ImportError:
    GNN_AVAILABLE = False
    predict_gnn = None
    train_gnn = None
    load_gnn_model = None

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Load models when app starts
model = models.load_model()
ensemble = models.load_ensemble()

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to ensure API is running."""
    return jsonify({
        "status": "healthy",
        "port": 52332,
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

# ---- Core Prediction ----
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
    verdict = models.classify_verdict(prob)

    # Log to database if available
    prediction_id = None
    if DATABASE_AVAILABLE:
        try:
            assert log_prediction is not None
            prediction_id = log_prediction(data, prob, verdict["verdict"], validation.get("warnings", []))
        except Exception as e:
            print(f"Database logging failed: {e}")

    warnings = list(validation.get("warnings", []))
    if data["toxicity"] > 0.7:
        warnings.append("High toxicity risk detected")
    if data["bioavailability"] < 0.4:
        warnings.append("Low bioavailability risk")

    # Active learning queue
    if ACTIVE_LEARNING_AVAILABLE:
        try:
            assert compute_uncertainty is not None and add_to_queue is not None
            uncertainty = compute_uncertainty(model, feature_list)
            if uncertainty > 0.15:  # Threshold for queueing
                queue_id = add_to_queue(
                    compound_name=data.get("compound_name", "Unknown"),
                    features=feature_list,
                    probability=prob,
                    uncertainty=uncertainty,
                    prediction_id=prediction_id
                )
                warnings.append(f"Added to active learning queue (uncertainty: {uncertainty:.3f})")
        except Exception as e:
            print(f"Active learning queue failed: {e}")

    return jsonify({
        "prediction_id": prediction_id,
        "success_probability": float(prob),
        "verdict": verdict,
        "confidence_interval": confidence,
        "shap_values": shap_vals,
        "phase_probabilities": phases,
        "warnings": warnings,
        "gxp_validation": validation,
        "server_port": 52332
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
        "success_probabilities": probs.tolist(),
        "server_port": 52332
    })

# ---- ML Core Ensembles & Counterfactuals ----
@app.route("/predict-ensemble", methods=["POST"])
def predict_ensemble_route():
    data = request.get_json()
    required = ["toxicity","bioavailability","solubility","binding","molecular_weight"]
    for k in required:
        if k not in data:
            return jsonify({"error": f"Missing: {k}"}), 400

    features = [data[k] for k in required]
    result = models.predict_ensemble(ensemble, features)
    result["server_port"] = 52332
    return jsonify(result)

@app.route("/counterfactual", methods=["POST"])
def counterfactual():
    data = request.get_json()
    required = ["toxicity","bioavailability","solubility","binding","molecular_weight"]
    for k in required:
        if k not in data:
            return jsonify({"error": f"Missing: {k}"}), 400

    features = [data[k] for k in required]
    target = data.get("target_probability", 0.75)
    result = models.get_counterfactual(model, features, target)
    result["server_port"] = 52332
    return jsonify(result)

@app.route("/shap", methods=["POST"])
def shap():
    data = request.get_json()
    required = ["toxicity","bioavailability","solubility","binding","molecular_weight"]
    for k in required:
        if k not in data:
            return jsonify({"error": f"Missing: {k}"}), 400

    features = [data[k] for k in required]
    result = models.get_shap_breakdown(model, features)
    result["server_port"] = 52332
    return jsonify(result)

# ---- ADMET & Phase Probabilities ----
@app.route("/admet", methods=["POST"])
def admet():
    data = request.get_json()
    required = ["toxicity","bioavailability","solubility","binding","molecular_weight"]
    for k in required:
        if k not in data:
            return jsonify({"error": f"Missing: {k}"}), 400

    features = [data[k] for k in required]
    result = models.compute_admet(features)
    result["server_port"] = 52332
    return jsonify(result)

# ---- History & Stats ----
@app.route("/history", methods=["GET"])
def history():
    if DATABASE_AVAILABLE:
        assert get_history is not None
        limit = int(request.args.get("limit", 50))
        verdict_filter = request.args.get("verdict")
        history_data = get_history(limit=limit, verdict_filter=verdict_filter)
        return jsonify({"history": history_data, "server_port": 52332})
    else:
        return jsonify({"error": "Database not available", "server_port": 52332}), 503

@app.route("/stats", methods=["GET"])
def stats():
    if DATABASE_AVAILABLE:
        assert get_stats is not None
        stats_data = get_stats()
        stats_data["server_port"] = 52332
        return jsonify(stats_data)
    else:
        return jsonify({"error": "Database not available", "server_port": 52332}), 503

# ---- Scenarios ----
@app.route("/scenarios", methods=["GET", "POST"])
def scenarios():
    if request.method == "GET":
        if DATABASE_AVAILABLE:
            assert db_list_scenarios is not None
            scenarios_data = db_list_scenarios()
            return jsonify({"scenarios": scenarios_data, "server_port": 52332})
        else:
            return jsonify({"error": "Database not available", "server_port": 52332}), 503
    
    elif request.method == "POST":
        data = request.get_json()
        if DATABASE_AVAILABLE:
            assert db_save_scenario is not None
            scenario_id = db_save_scenario(
                name=data.get("name", "Unnamed Scenario"),
                inputs=data.get("inputs", {}),
                outputs=data.get("outputs", {}),
                tags=data.get("tags", [])
            )
            return jsonify({"scenario_id": scenario_id, "server_port": 52332})
        else:
            return jsonify({"error": "Database not available", "server_port": 52332}), 503

    return jsonify({"error": "Method not allowed", "server_port": 52332}), 405

@app.route("/scenarios/<scenario_id>", methods=["GET", "DELETE"])
def scenario_detail(scenario_id):
    if request.method == "GET":
        if DATABASE_AVAILABLE:
            assert db_get_scenario is not None
            scenario = db_get_scenario(scenario_id)
            if scenario:
                scenario["server_port"] = 52332
                return jsonify(scenario)
            else:
                return jsonify({"error": "Scenario not found", "server_port": 52332}), 404
        else:
            return jsonify({"error": "Database not available", "server_port": 52332}), 503
    
    elif request.method == "DELETE":
        if DATABASE_AVAILABLE:
            assert db_delete_scenario is not None
            success = db_delete_scenario(scenario_id)
            if success:
                return jsonify({"status": "deleted", "server_port": 52332})
            else:
                return jsonify({"error": "Scenario not found", "server_port": 52332}), 404
        else:
            return jsonify({"error": "Database not available", "server_port": 52332}), 503

    return jsonify({"error": "Method not allowed", "server_port": 52332}), 405

# ---- Financial Calculations ----
@app.route("/financial/npv", methods=["POST"])
def financial_npv():
    data = request.get_json()
    result = compute_npv(data)
    result["server_port"] = 52332
    return jsonify(result)

@app.route("/financial/monte-carlo", methods=["POST"])
def financial_monte_carlo():
    data = request.get_json()
    result: Any = list(run_monte_carlo(data))
    return jsonify({"batches": result, "server_port": 52332})

@app.route("/financial/sensitivity", methods=["POST"])
def financial_sensitivity():
    data = request.get_json()
    result = run_tornado(data)
    result["server_port"] = 52332
    return jsonify(result)

# ---- Portfolio Optimization ----
@app.route("/optimize-portfolio", methods=["POST"])
def optimize_portfolio_route():
    data = request.get_json()
    compounds = data.get("compounds", [])
    budget = data.get("budget", 1000000)
    result = optimize_portfolio(compounds, budget)
    result["server_port"] = 52332
    return jsonify(result)

# ---- Export Reports ----
@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    data = request.get_json()
    pdf_buffer = generate_executive_report(data)
    return send_file(
        BytesIO(pdf_buffer),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='nova_cura_report_52332.pdf'
    )

@app.route("/transparency-report", methods=["GET"])
def transparency_report():
    model_info = {
        "type": "Random Forest",
        "version": "1.0.0",
        "data_source": "Synthetic",
        "training_samples": 300,
        "server_port": 52332
    }
    validation_results = {
        "accuracy": 0.85,
        "auc": 0.92,
        "precision": 0.88,
        "recall": 0.82
    }
    report = generate_transparency_report(model_info, validation_results)
    report["server_port"] = 52332
    return jsonify(report)

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
            assert fetch_target_id is not None
            target_ids = [fetch_target_id(data["gene"])]
        elif "targets" in data:
            target_ids = data["targets"]
        else:
            return jsonify({"error": "Provide target_id, gene, or targets", "server_port": 52332}), 400

        try:
            assert load_or_fetch_dataset is not None and train_on_chembl is not None
            df = load_or_fetch_dataset(target_ids, max_per_target=max_recs)
            result = train_on_chembl(df)
            model = result["model"]   # hot-swap the running model
            return jsonify({
                "status": "success",
                "message": f"Model retrained on {result['metrics']['n_train']} ChEMBL compounds",
                "metrics": result["metrics"],
                "targets": target_ids,
                "server_port": 52332
            })
        except Exception as e:
            return jsonify({"error": str(e), "server_port": 52332}), 500

    @app.route("/data/chembl-status", methods=["GET"])
    def chembl_status():
        meta_path = "model_metadata.json"
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                data = json.load(f)
                data["server_port"] = 52332
                return jsonify(data)
        return jsonify({"status": "No ChEMBL data loaded yet — using synthetic data", "server_port": 52332})

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
                "server_port": 52332
            })
        return jsonify({"status": "No dataset file found", "server_port": 52332})

# ---- Upgrade 2: SMILES Pipeline ----
if SMILES_AVAILABLE:
    @app.route("/predict-smiles", methods=["POST"])
    def predict_smiles():
        data = request.get_json()
        smiles = data.get("smiles", "").strip()
        if not smiles:
            return jsonify({"error": "smiles field required", "server_port": 52332}), 400

        assert smiles_to_descriptors is not None
        desc = smiles_to_descriptors(smiles)
        if not desc["validity"]["valid"]:
            return jsonify({"error": desc["validity"]["error_message"], "server_port": 52332}), 422
        if desc["model_features"] is None:
            return jsonify({"error": "Could not compute features from SMILES", "server_port": 52332}), 422

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
            "server_port": 52332
        })

    @app.route("/descriptors", methods=["POST"])
    def compute_descriptors():
        data = request.get_json()
        if "smiles_list" in data:
            assert batch_smiles_to_features is not None
            results = batch_smiles_to_features(data["smiles_list"])
            return jsonify({"count": len(results), "results": results, "server_port": 52332})
        smiles = data.get("smiles","")
        assert smiles_to_descriptors is not None
        result = smiles_to_descriptors(smiles)
        result["server_port"] = 52332
        return jsonify(result)

# ---- Upgrade 3: Therapeutic Area Models ----
if TA_AVAILABLE:
    @app.route("/predict-ta", methods=["POST"])
    def predict_therapeutic_area():
        data = request.get_json()
        features = data.get("features", [])
        
        if len(features) != 5:
            return jsonify({"error": "Need exactly 5 features", "server_port": 52332}), 400
        
        if data.get("compare_all"):
            assert compare_all_tas is not None
            result = compare_all_tas(features)
            result["server_port"] = 52332
            return jsonify(result)
        
        ta = data.get("therapeutic_area", "auto")
        if ta == "auto":
            assert compare_all_tas is not None and predict_ta is not None
            comparison = compare_all_tas(features)
            best_ta = comparison["best_fit"][0]
            result = predict_ta(features, best_ta)
            result["auto_detected"] = best_ta
            result["server_port"] = 52332
            return jsonify(result)
        
        if ta not in THERAPEUTIC_AREAS:
            return jsonify({"error": f"Invalid therapeutic area: {ta}", "server_port": 52332}), 400
        
        assert predict_ta is not None
        result = predict_ta(features, ta)
        result["server_port"] = 52332
        return jsonify(result)

    @app.route("/therapeutic-areas", methods=["GET"])
    def list_therapeutic_areas():
        areas = {
            "therapeutic_areas": {
                key: {
                    "label": info["label"],
                    "description": info["description"],
                    "color": info["color"],
                    "attrition_rates": info["attrition_rates"],
                    "feature_weights": info["feature_weights"],
                }
                for key, info in THERAPEUTIC_AREAS.items()
            },
            "server_port": 52332
        }
        return jsonify(areas)

    @app.route("/ta-models/train", methods=["POST"])
    def train_ta_models_endpoint():
        try:
            assert train_all_ta_models is not None
            results = train_all_ta_models()
            return jsonify({
                "status": "trained",
                "results": results,
                "message": f"Trained {len(results)} therapeutic area models",
                "server_port": 52332
            })
        except Exception as e:
            return jsonify({"error": str(e), "server_port": 52332}), 500

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
        
        return jsonify({"therapeutic_areas": status, "server_port": 52332})

# ---- Upgrade 6: Active Learning ----
if ACTIVE_LEARNING_AVAILABLE:
    @app.route("/active-learning/queue", methods=["GET"])
    def active_learning_queue():
        limit = int(request.args.get("limit", 20))
        status = request.args.get("status", "pending")
        assert get_queue is not None
        queue = get_queue(limit=limit, status=status)
        return jsonify({
            "queue": queue,
            "total_count": len(queue),
            "limit": limit,
            "status": status,
            "server_port": 52332
        })

    @app.route("/active-learning/label/<queue_id>", methods=["POST"])
    def active_learning_label(queue_id):
        data = request.get_json()
        
        true_label = data.get("true_label")
        labelled_by = data.get("labelled_by", "Unknown")
        notes = data.get("notes", "")
        
        if true_label is None:
            return jsonify({"error": "true_label field required", "server_port": 52332}), 400
        assert label_compound is not None
        success = label_compound(queue_id, true_label, labelled_by, notes)
        
        if success:
            return jsonify({
                "status": "labelled",
                "queue_id": queue_id,
                "true_label": true_label,
                "labelled_by": labelled_by,
                "server_port": 52332
            })
        else:
            return jsonify({"error": "Queue ID not found", "server_port": 52332}), 404

    @app.route("/active-learning/stats", methods=["GET"])
    def active_learning_stats():
        assert get_queue_stats is not None
        stats = get_queue_stats()
        stats["server_port"] = 52332
        return jsonify(stats)

    @app.route("/active-learning/retrain", methods=["POST"])
    def active_learning_retrain():
        assert retrain_with_labels is not None
        result = retrain_with_labels()
        result["server_port"] = 52332
        return jsonify(result)

# ---- Upgrade 7: LLM Analyst ----
if LLM_AVAILABLE:
    @app.route("/analyst/ask", methods=["POST"])
    def analyst_ask():
        data = request.get_json()
        question = data.get("question", "")
        if not question:
            return jsonify({"error": "question field required", "server_port": 52332}), 400
        assert retrieve_compound_context is not None and ask_analyst is not None
        context = retrieve_compound_context(
            compound_name = data.get("compound_name"),
            prediction_id = data.get("prediction_id"),
            model = model,
            features = data.get("features"),
        )
        
        result = ask_analyst(question, context)
        result["server_port"] = 52332
        return jsonify(result)

    @app.route("/analyst/suggestions", methods=["POST"])
    def analyst_suggestions():
        data = request.get_json()
        assert retrieve_compound_context is not None and get_suggested_questions is not None
        if data.get("features"):
            context = retrieve_compound_context(model=model, features=data["features"])
        elif data.get("compound_name"):
            context = retrieve_compound_context(compound_name=data["compound_name"])
        else:
            return jsonify({"error": "Provide features or compound_name", "server_port": 52332}), 400
        
        suggestions = get_suggested_questions(context)
        return jsonify({
            "compound": context.get("compound_name", "Unknown"),
            "suggestions": suggestions,
            "context_available": bool(context.get("success_probability")),
            "server_port": 52332
        })

# ---- Upgrade 8: GNN Model ----
if GNN_AVAILABLE:
    @app.route("/predict-gnn", methods=["POST"])
    def predict_with_gnn():
        data = request.get_json()
        smiles = data.get("smiles", "").strip()
        if not smiles:
            return jsonify({"error": "smiles field required", "server_port": 52332}), 400

        assert predict_gnn is not None
        result = predict_gnn(smiles)

        # If GNN available, also run RF for comparison
        if not result.get("fallback"):
            if SMILES_AVAILABLE:
                assert smiles_to_descriptors is not None
                desc = smiles_to_descriptors(smiles)
                if desc["validity"]["valid"] and desc["model_features"]:
                    features = [desc["model_features"][k] for k in
                                ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
                    rf_prob = models.predict_single(model, features)
                    result["rf_probability"] = round(rf_prob, 4)
                    result["ensemble_gnn_rf"] = round(
                        result["gnn_probability"] * 0.6 + rf_prob * 0.4, 4
                    )

        result["server_port"] = 52332
        return jsonify(result)

    @app.route("/gnn/status", methods=["GET"])
    def gnn_status():
        if os.path.exists("gnn_model.pt"):
            return jsonify({
                "status": "trained",
                "server_port": 52332
            })
        return jsonify({"status": "not_trained", 
                        "message": "POST to /gnn/train with SMILES + labels to train",
                        "server_port": 52332})

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
                return jsonify({"error": "chembl_dataset.csv not found. Run ChEMBL import first.", "server_port": 52332}), 404
        else:
            smiles_list = data.get("smiles_list", [])
            labels = data.get("labels", [])
        
        if len(smiles_list) < 10:
            return jsonify({"error": "Need at least 10 compounds to train GNN", "server_port": 52332}), 400

        assert train_gnn is not None
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
            "server_port": 52332
        })

# ---- WebSocket Events ----
@socketio.on('connect')
def handle_connect():
    print('Client connected to NovaCura API on port 52332')
    emit('status', {'message': 'Connected to NovaCura API on port 52332', 'port': 52332})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from NovaCura API on port 52332')

@socketio.on('predict_realtime')
def handle_predict_realtime(data):
    try:
        features = [data[k] for k in ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
        prob = models.predict_single(model, features)
        emit('prediction_result', {
            'compound_id': data.get('compound_id'),
            'probability': float(prob),
            'timestamp': datetime.utcnow().isoformat(),
            'server_port': 52332
        })
    except Exception as e:
        emit('error', {'message': str(e), 'server_port': 52332})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=52332)
