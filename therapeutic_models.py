"""
UPGRADE 3: Therapeutic Area Sub-Models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Train separate Random Forest models per therapeutic indication.
Oncology attrition patterns differ fundamentally from CNS or rare disease.

Indications supported:
  - oncology:    CDK inhibitors, kinase inhibitors, targeted therapies
  - cns:         BBB-penetrant compounds, CNS receptor modulators
  - rare:        Enzyme replacement, gene therapy targets
  - cardiology:  Ion channel modulators, anticoagulants
  - infectious:  Antibiotics, antivirals, antifungals
  - metabolic:   Diabetes, obesity, NASH targets

Usage:
  python therapeutic_models.py --train          # train all sub-models
  python therapeutic_models.py --predict --ta oncology --smiles "..."
"""

import numpy as np
import pandas as pd
import joblib
import json
import os
from datetime import datetime
from typing import Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, f1_score

MODELS_DIR = "ta_models"
os.makedirs(MODELS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# THERAPEUTIC AREA DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

THERAPEUTIC_AREAS = {
    "oncology": {
        "label":        "Oncology",
        "description":  "Cancer — kinase inhibitors, targeted therapies, immunotherapy",
        "chembl_targets": ["CHEMBL203", "CHEMBL301", "CHEMBL5145", "CHEMBL1862"],  # EGFR, CDK2, BRAF, VEGFR
        "attrition_rates": {
            "phase1": 0.67, "phase2": 0.40, "phase3": 0.58  # Higher phase 2 failure in oncology
        },
        "feature_weights": {
            # Binding and selectivity matter most; MW tolerance higher for oncology
            "binding": 0.40, "toxicity": 0.30, "bioavailability": 0.15,
            "solubility": 0.10, "molecular_weight": 0.05
        },
        "success_threshold_nm": 100.0,   # more stringent — oncology needs potent drugs
        "mw_tolerance": 700,              # larger MW acceptable (e.g. antibody-drug conjugates)
        "color": "#E24B4A",
    },
    "cns": {
        "label":        "CNS",
        "description":  "Central nervous system — BBB penetration required",
        "chembl_targets": ["CHEMBL2056", "CHEMBL1900", "CHEMBL4282"],  # SERT, D2, GABA
        "attrition_rates": {
            "phase1": 0.52, "phase2": 0.22, "phase3": 0.50  # Very high phase 2 failure in CNS
        },
        "feature_weights": {
            # Solubility and low MW critical for BBB; low toxicity essential
            "binding": 0.30, "toxicity": 0.30, "bioavailability": 0.20,
            "solubility": 0.15, "molecular_weight": 0.05
        },
        "success_threshold_nm": 500.0,
        "mw_tolerance": 450,    # strict MW < 450 for BBB penetration
        "color": "#7F77DD",
    },
    "rare": {
        "label":        "Rare Disease",
        "description":  "Orphan drugs — enzyme replacement, gene therapy, rare genetic diseases",
        "chembl_targets": ["CHEMBL2742", "CHEMBL4523"],
        "attrition_rates": {
            "phase1": 0.72, "phase2": 0.52, "phase3": 0.70  # Higher success — smaller trials, unmet need
        },
        "feature_weights": {
            "binding": 0.35, "toxicity": 0.25, "bioavailability": 0.20,
            "solubility": 0.10, "molecular_weight": 0.10
        },
        "success_threshold_nm": 1000.0,  # more lenient threshold
        "mw_tolerance": 900,
        "color": "#1D9E75",
    },
    "cardiology": {
        "label":        "Cardiovascular",
        "description":  "Heart failure, hypertension, anticoagulation, dyslipidemia",
        "chembl_targets": ["CHEMBL1865", "CHEMBL206", "CHEMBL2973"],  # ACE, beta1, thrombin
        "attrition_rates": {
            "phase1": 0.60, "phase2": 0.45, "phase3": 0.60
        },
        "feature_weights": {
            "binding": 0.30, "toxicity": 0.35, "bioavailability": 0.20,  # cardiac safety paramount
            "solubility": 0.10, "molecular_weight": 0.05
        },
        "success_threshold_nm": 500.0,
        "mw_tolerance": 600,
        "color": "#D85A30",
    },
    "infectious": {
        "label":        "Infectious Disease",
        "description":  "Antibiotics, antivirals, antifungals, antiparasitics",
        "chembl_targets": ["CHEMBL3778", "CHEMBL5619", "CHEMBL4523"],
        "attrition_rates": {
            "phase1": 0.62, "phase2": 0.48, "phase3": 0.68
        },
        "feature_weights": {
            "binding": 0.35, "toxicity": 0.25, "bioavailability": 0.20,
            "solubility": 0.15, "molecular_weight": 0.05
        },
        "success_threshold_nm": 1000.0,
        "mw_tolerance": 600,
        "color": "#EF9F27",
    },
    "metabolic": {
        "label":        "Metabolic Disease",
        "description":  "Diabetes, obesity, NAFLD/NASH, dyslipidemia",
        "chembl_targets": ["CHEMBL2492", "CHEMBL1977", "CHEMBL4523"],  # GLP-1R, PPAR-gamma
        "attrition_rates": {
            "phase1": 0.65, "phase2": 0.42, "phase3": 0.62
        },
        "feature_weights": {
            "binding": 0.30, "toxicity": 0.30, "bioavailability": 0.25,
            "solubility": 0.10, "molecular_weight": 0.05
        },
        "success_threshold_nm": 300.0,
        "mw_tolerance": 550,
        "color": "#378ADD",
    },
}

FEATURE_NAMES = ["toxicity", "bioavailability", "solubility", "binding", "molecular_weight"]


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHETIC DATA GENERATION PER THERAPEUTIC AREA
# ─────────────────────────────────────────────────────────────────────────────

def _generate_ta_dataset(ta_key: str, n_samples: int = 800) -> pd.DataFrame:
    """Generate synthetic data tailored to therapeutic area characteristics."""
    np.random.seed(42 + hash(ta_key) % 1000)  # reproducible per TA
    
    ta = THERAPEUTIC_AREAS[ta_key]
    weights = ta["feature_weights"]
    
    # Generate base features
    tox = np.random.rand(n_samples)
    bio = np.random.rand(n_samples)
    sol = np.random.rand(n_samples)
    bind = np.random.rand(n_samples)
    mw = np.random.rand(n_samples)
    
    # Apply therapeutic area biases
    if ta_key == "oncology":
        # Higher binding, tolerate higher MW/toxicity
        bind = np.clip(bind * 1.3, 0, 1)
        mw = np.clip(mw * 1.2, 0, 1)
        tox = np.clip(tox * 1.1, 0, 1)
    elif ta_key == "cns":
        # Strict MW limits, low toxicity critical
        mw = np.clip(mw * 0.6, 0, 1)
        tox = np.clip(tox * 0.7, 0, 1)
        sol = np.clip(sol * 1.2, 0, 1)  # need good solubility
    elif ta_key == "rare":
        # More lenient across the board
        bio = np.clip(bio * 1.1, 0, 1)
        bind = np.clip(bind * 1.15, 0, 1)
    
    # Weighted success formula using TA-specific weights
    success_prob = (
        tox * weights["toxicity"] * -1 +
        bio * weights["bioavailability"] +
        sol * weights["solubility"] +
        bind * weights["binding"] -
        mw * weights["molecular_weight"] * 0.5  # MW penalty
    )
    
    # Apply therapeutic area-specific success threshold
    threshold = 0.35 + (0.1 if ta_key == "rare" else 0) - (0.05 if ta_key == "oncology" else 0)
    labels = (success_prob > threshold).astype(int)
    
    return pd.DataFrame({
        "toxicity": tox, "bioavailability": bio, "solubility": sol,
        "binding": bind, "molecular_weight": mw, "label": labels,
        "therapeutic_area": ta_key,
        "source": "synthetic_ta"
    })


# ─────────────────────────────────────────────────────────────────────────────
# MODEL TRAINING PER THERAPEUTIC AREA
# ─────────────────────────────────────────────────────────────────────────────

def train_ta_model(ta_key: str, df: pd.DataFrame = None) -> dict:
    """Train a Random Forest model for a specific therapeutic area."""
    if df is None:
        df = _generate_ta_dataset(ta_key)
    
    features = FEATURE_NAMES
    X = df[features].values
    y = df["label"].values
    
    # TA-specific hyperparameters
    ta = THERAPEUTIC_AREAS[ta_key]
    if ta_key == "oncology":
        rf_params = {"n_estimators": 300, "max_depth": 12, "min_samples_leaf": 2}
    elif ta_key == "cns":
        rf_params = {"n_estimators": 250, "max_depth": 8, "min_samples_leaf": 5}
    else:
        rf_params = {"n_estimators": 200, "max_depth": 10, "min_samples_leaf": 3}
    
    # Train calibrated model
    base_rf = RandomForestClassifier(
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
        **rf_params
    )
    model = CalibratedClassifierCV(base_rf, cv=5, method="isotonic")
    model.fit(X, y)
    
    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
    
    metrics = {
        "therapeutic_area": ta_key,
        "cv_auc_mean": round(cv_scores.mean(), 4),
        "cv_auc_std": round(cv_scores.std(), 4),
        "n_samples": len(df),
        "pos_rate": round(y.mean(), 3),
        "feature_weights": ta["feature_weights"],
        "trained_at": datetime.utcnow().isoformat(),
    }
    
    # Save model
    model_path = os.path.join(MODELS_DIR, f"{ta_key}_model.joblib")
    joblib.dump(model, model_path)
    
    # Save metadata
    meta_path = os.path.join(MODELS_DIR, f"{ta_key}_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✅ {ta['label']} model trained: AUC={metrics['cv_auc_mean']:.4f}±{metrics['cv_auc_std']:.4f}")
    return {"model": model, "metrics": metrics}


def train_all_ta_models() -> dict:
    """Train all therapeutic area models."""
    results = {}
    print("Training all therapeutic area models...")
    
    for ta_key in THERAPEUTIC_AREAS.keys():
        try:
            result = train_ta_model(ta_key)
            results[ta_key] = result
        except Exception as e:
            print(f"❌ Failed to train {ta_key}: {e}")
            results[ta_key] = {"error": str(e)}
    
    return results


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION AND COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def load_ta_models() -> dict:
    """Load all trained therapeutic area models."""
    models = {}
    for ta_key in THERAPEUTIC_AREAS.keys():
        model_path = os.path.join(MODELS_DIR, f"{ta_key}_model.joblib")
        if os.path.exists(model_path):
            models[ta_key] = joblib.load(model_path)
        else:
            print(f"⚠️  {ta_key} model not found at {model_path}")
    return models


def predict_ta(features: list, therapeutic_area: str) -> dict:
    """Predict using a specific therapeutic area model."""
    models = load_ta_models()
    
    if therapeutic_area not in models:
        return {"error": f"Therapeutic area '{therapeutic_area}' not available"}
    
    model = models[therapeutic_area]
    prob = float(model.predict_proba([features])[0][1])
    
    # Load TA metadata for phase probabilities
    ta = THERAPEUTIC_AREAS[therapeutic_area]
    phases = _get_ta_phase_probabilities(prob, ta)
    
    return {
        "therapeutic_area": therapeutic_area,
        "probability": round(prob, 4),
        "phase_probabilities": phases,
        "feature_weights": ta["feature_weights"],
        "attrition_rates": ta["attrition_rates"],
    }


def compare_all_tas(features: list) -> dict:
    """Compare a compound across all therapeutic areas."""
    models = load_ta_models()
    results = {}
    
    for ta_key, ta_info in THERAPEUTIC_AREAS.items():
        if ta_key not in models:
            continue
            
        model = models[ta_key]
        prob = float(model.predict_proba([features])[0][1])
        phases = _get_ta_phase_probabilities(prob, ta_info)
        
        results[ta_key] = {
            "label": ta_info["label"],
            "probability": round(prob, 4),
            "phase_probabilities": phases,
            "color": ta_info["color"],
            "description": ta_info["description"],
        }
    
    # Sort by probability
    sorted_results = dict(sorted(results.items(), key=lambda x: x[1]["probability"], reverse=True))
    
    return {
        "compound_features": dict(zip(FEATURE_NAMES, [round(f, 3) for f in features])),
        "therapeutic_areas": sorted_results,
        "best_fit": max(results.items(), key=lambda x: x[1]["probability"]),
        "recommendation": _get_ta_recommendation(sorted_results),
    }


def _get_ta_phase_probabilities(prob: float, ta_info: dict) -> dict:
    """Calculate phase probabilities using TA-specific attrition rates."""
    rates = ta_info["attrition_rates"]
    
    # Apply TA-specific adjustments to base probability
    adj_prob = prob * (1.2 if ta_info["label"] == "Rare Disease" else 1.0)
    
    p1 = min(0.95, adj_prob * rates["phase1"])
    p2 = min(0.85, adj_prob * rates["phase2"]) 
    p3 = min(0.90, adj_prob * rates["phase3"])
    overall = p1 * p2 * p3
    
    return {
        "phase1": round(p1 * 100, 1),
        "phase2": round(p2 * 100, 1),
        "phase3": round(p3 * 100, 1),
        "overall_pos": round(overall * 100, 1),
        "uplift_vs_baseline": round(overall / 0.082, 2),
        "industry_baseline": 8.2,
    }


def _get_ta_recommendation(results: dict) -> str:
    """Generate recommendation based on TA comparison."""
    if not results:
        return "No therapeutic area models available"
    
    best_ta = max(results.items(), key=lambda x: x[1]["probability"])
    best_prob = best_ta[1]["probability"]
    
    if best_prob > 0.7:
        return f"Strong fit for {best_ta[1]['label']} (probability: {best_prob:.1%}). Consider prioritizing this indication."
    elif best_prob > 0.5:
        return f"Moderate fit for {best_ta[1]['label']} (probability: {best_prob:.1%}). Further optimization recommended."
    else:
        return f"Weak fit across all TAs. Best match: {best_ta[1]['label']} ({best_prob:.1%}). Consider redesign."


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ENDPOINTS (add to api.py)
# ─────────────────────────────────────────────────────────────────────────────

TA_ROUTES = '''
# ── ADD THESE ROUTES TO api.py ───────────────────────────────────────────────

from therapeutic_models import (
    predict_ta, compare_all_tas, THERAPEUTIC_AREAS,
    train_all_ta_models, load_ta_models
)

@app.route("/predict-ta", methods=["POST"])
def predict_therapeutic_area():
    """
    POST body:
      {"features": [0.3, 0.7, 0.6, 0.8, 0.5], "therapeutic_area": "oncology"}
      OR {"features": [...], "compare_all": true}
    """
    data = request.get_json()
    features = data.get("features", [])
    
    if len(features) != 5:
        return jsonify({"error": "Need exactly 5 features"}), 400
    
    if data.get("compare_all"):
        result = compare_all_tas(features)
        return jsonify(result)
    
    ta = data.get("therapeutic_area", "auto")
    if ta == "auto":
        # Auto-detect best TA based on compound properties
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
    """List all available therapeutic areas with descriptions."""
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
    """Retrain all therapeutic area models."""
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
    """Check status of all TA models."""
    status = {}
    for ta_key in THERAPEUTIC_AREAS.keys():
        model_path = os.path.join(MODELS_DIR, f"{ta_key}_model.joblib")
        meta_path = os.path.join(MODELS_DIR, f"{ta_key}_metadata.json")
        
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
'''


# ─────────────────────────────────────────────────────────────────────────────
# CLI INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NovaCura Therapeutic Area Models")
    parser.add_argument("--train", action="store_true", help="Train all TA models")
    parser.add_argument("--predict", action="store_true", help="Predict for a compound")
    parser.add_argument("--ta", type=str, help="Therapeutic area for prediction")
    parser.add_argument("--features", type=str, help="Comma-separated features")
    parser.add_argument("--compare", action="store_true", help="Compare across all TAs")
    parser.add_argument("--smiles", type=str, help="SMILES string (requires RDKit)")
    
    args = parser.parse_args()
    
    if args.train:
        results = train_all_ta_models()
        print(f"\n✅ Training complete. {len(results)} models trained.")
        
    elif args.predict:
        if args.smiles:
            # Try to get features from SMILES
            try:
                from smiles_pipeline import smiles_to_descriptors
                desc = smiles_to_descriptors(args.smiles)
                if desc["validity"]["valid"]:
                    features = [desc["model_features"][f] for f in FEATURE_NAMES]
                else:
                    print(f"Invalid SMILES: {desc['validity']['error_message']}")
                    exit(1)
            except ImportError:
                print("RDKit not available. Use --features instead.")
                exit(1)
        elif args.features:
            features = [float(x.strip()) for x in args.features.split(",")]
        else:
            print("Provide either --smiles or --features")
            exit(1)
        
        if args.compare:
            result = compare_all_tas(features)
            print("\nTherapeutic Area Comparison:")
            print("=" * 50)
            for ta, data in result["therapeutic_areas"].items():
                print(f"{data['label']:12} | {data['probability']:.3f} | {data['description']}")
            print(f"\nRecommendation: {result['recommendation']}")
        else:
            ta = args.ta or "auto"
            result = predict_ta(features, ta)
            print(f"\nPrediction for {result.get('therapeutic_area', ta)}:")
            print(f"Probability: {result['probability']:.3f}")
            if "phase_probabilities" in result:
                phases = result["phase_probabilities"]
                print(f"Phase 1: {phases['phase1']}% | Phase 2: {phases['phase2']}% | Phase 3: {phases['phase3']}%")
    else:
        parser.print_help()
