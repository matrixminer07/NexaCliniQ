"""
Prediction Blueprint — Routes for model predictions and analysis.

This blueprint handles:
- Single predictions with SHAP and ADMET
- Batch predictions
- Ensemble predictions
- Counterfactual analysis
- Therapeutic area comparisons
- SHAP and ADMET computation
"""
from typing import Any, cast

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from functools import wraps
import logging

from backend.utils.api_responses import success, error, service_unavailable
from backend.utils.validation import validate_json
from backend.schemas.prediction_schema import (
    PredictRequestSchema,
    PredictBatchRequestSchema,
    CounterfactualRequestSchema,
    ADMETRequestSchema,
    SHAPRequestSchema,
    PredictTherapeuticAreaRequestSchema,
)

# Blueprint initialization
prediction_bp = Blueprint('prediction', __name__)
logger = logging.getLogger(__name__)

# Global state (imported from app)
# These will be injected from main app context
model = None
ensemble = None
FEATURE_NAMES = ['toxicity', 'bioavailability', 'solubility', 'binding', 'molecular_weight']


def get_validated_json() -> dict[str, Any]:
    """Typed accessor for JSON payload attached by validate_json decorator."""
    return cast(dict[str, Any], getattr(request, 'validated_json', {}))

def set_globals(m, ens, feature_names):
    """Inject globals from main app."""
    global model, ensemble, FEATURE_NAMES
    model = m
    ensemble = ens
    FEATURE_NAMES = feature_names

def validate_model():
    """Decorator to check if model is loaded."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if model is None:
                return service_unavailable('Model not loaded. Please check server logs.')
            return f(*args, **kwargs)
        return wrapper
    return decorator

def require_role(*roles):
    """Decorator to check user role."""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            from flask_jwt_extended import get_jwt
            claims = get_jwt()
            role = claims.get('role')
            if role not in set(roles):
                return error('Insufficient permissions', status=403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── PREDICTION ROUTES ────────────────────────────────────────────────────────

@prediction_bp.route('/predict', methods=['POST'])
@validate_json(PredictRequestSchema)
@validate_model()
@require_role('researcher', 'admin')
def predict():
    """
    Single prediction endpoint.
    
    Request:
        {
            "toxicity": 0.5,
            "bioavailability": 0.7,
            "solubility": 0.6,
            "binding": 0.8,
            "molecular_weight": 0.5,
            "compound_name": "Optional name"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "success_probability": 0.75,
                "verdict": { "verdict": "PASS", "rationale": "..." },
                "confidence_interval": [0.70, 0.80],
                "shap_breakdown": { "feature": "value", ... },
                "phase_probabilities": { "phase1": 0.8, ... },
                "admet": { ... },
                "warnings": [...],
                "gxp_validation": { "valid": true, ... }
            }
        }
    """
    try:
        # Use validated data from decorator
        data = get_validated_json()
        features = [data[name] for name in FEATURE_NAMES]
        
        # Import models module (from app context)
        from backend import models as ml_models
        
        # Run predictions
        prob = ml_models.predict_single(model, features)
        ci = ml_models.predict_with_confidence(model, features)
        shap_bd = ml_models.get_shap_breakdown(model, features)
        phases = ml_models.get_phase_probabilities(prob)
        admet = ml_models.compute_admet(features)
        verdict = ml_models.classify_verdict(prob)
        
        # Build warnings
        warnings = list(admet.get("admet_warnings", []))
        if data.get("toxicity", 0) > 0.7:
            warnings.append("High toxicity risk detected")
        if data.get("bioavailability", 1) < 0.4:
            warnings.append("Low bioavailability risk")
        
        # Log prediction when database support is available.
        try:
            from backend.db_pg import log_prediction as log_pred
            log_pred(data, prob, verdict["verdict"], warnings)
        except Exception:
            logger.warning("Prediction logging unavailable", exc_info=True)
        
        return success({
            "success_probability": round(prob, 4),
            "verdict": verdict,
            "confidence_interval": ci,
            "shap_breakdown": shap_bd,
            "phase_probabilities": phases,
            "admet": admet,
            "warnings": warnings,
            "gxp_validation": {"valid": True},  # Placeholder
        })
    except Exception as e:
        logger.exception("Prediction error")
        return error(f"Prediction error: {str(e)}", status=500)


@prediction_bp.route('/predict-batch', methods=['POST'])
@validate_json(PredictBatchRequestSchema)
@validate_model()
@require_role('researcher', 'admin')
def predict_batch():
    """Batch prediction endpoint (max 100 compounds per request)."""
    try:
        data = get_validated_json()
        compounds = data.get("items", [])
        
        if len(compounds) > 100:
            return error("Batch size cannot exceed 100", status=400)
        
        from backend import models as ml_models
        
        results = []
        errors = []
        
        for i, item in enumerate(compounds):
            try:
                if not isinstance(item, dict):
                    errors.append({"index": i, "error": "Item must be a dict"})
                    continue
                
                # Extract features
                features = []
                for fname in FEATURE_NAMES:
                    if fname not in item:
                        errors.append({"index": i, "error": f"Missing feature: {fname}"})
                        continue
                    features.append(float(item[fname]))
                
                if len(features) != len(FEATURE_NAMES):
                    continue
                
                # Predict
                prob = ml_models.predict_single(model, features)
                verdict = ml_models.classify_verdict(prob)
                admet = ml_models.compute_admet(features)
                shap_bd = ml_models.get_shap_breakdown(model, features)
                
                warnings = []
                if item.get("toxicity", 0) > 0.7:
                    warnings.append("High toxicity")
                if item.get("bioavailability", 1) < 0.4:
                    warnings.append("Low bioavailability")
                
                results.append({
                    "index": i,
                    "compound_name": item.get("compound_name", f"Compound_{i+1}"),
                    "success_probability": round(prob, 4),
                    "verdict": verdict["verdict"],
                    "top_driver": shap_bd.get("top_driver", "unknown"),
                    "drug_likeness": admet.get("drug_likeness", "unknown"),
                    "warnings": warnings,
                })
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        
        # Sort by probability
        results.sort(key=lambda x: x["success_probability"], reverse=True)
        
        response = {
            "count": len(results),
            "results": results,
            "summary": {
                "pass_count": sum(1 for r in results if r["verdict"] == "PASS"),
                "caution_count": sum(1 for r in results if r["verdict"] == "CAUTION"),
                "fail_count": sum(1 for r in results if r["verdict"] == "FAIL"),
                "top_compound": results[0]["compound_name"] if results else None,
            }
        }
        
        if errors:
            response["errors"] = errors
        
        return success(response)
    except Exception as e:
        logger.exception("Batch prediction error")
        return error(f"Batch prediction error: {str(e)}", status=500)


@prediction_bp.route('/predict-ensemble', methods=['POST'])
@validate_json(PredictRequestSchema)
@validate_model()
def predict_ensemble():
    """Ensemble prediction combining multiple models."""
    if ensemble is None:
        return service_unavailable("Ensemble model not available")
    
    try:
        data = get_validated_json()
        features = [data[name] for name in FEATURE_NAMES]
        
        from backend import models as ml_models
        
        result = ml_models.predict_ensemble(ensemble, features)
        phases = ml_models.get_phase_probabilities(result["ensemble_probability"])
        result["phase_probabilities"] = phases
        
        return success(result)
    except Exception as e:
        logger.exception("Ensemble prediction error")
        return error(f"Ensemble prediction error: {str(e)}", status=500)


@prediction_bp.route('/counterfactual', methods=['POST'])
@validate_json(CounterfactualRequestSchema)
@validate_model()
def counterfactual_analysis():
    """
    Counterfactual analysis — what changes would improve the prediction?
    """
    try:
        data = get_validated_json()
        features = [data[name] for name in FEATURE_NAMES]
        target_prob = data.get("target_probability", 0.75)
        
        from backend import models as ml_models
        
        result = ml_models.generate_counterfactual(model, features, target_prob=target_prob)
        return success(result)
    except Exception as e:
        logger.exception("Counterfactual analysis error")
        return error(f"Counterfactual analysis error: {str(e)}", status=500)


@prediction_bp.route('/shap', methods=['POST'])
@validate_json(SHAPRequestSchema)
@validate_model()
def shap_breakdown():
    """Get SHAP feature importance breakdown."""
    try:
        data = get_validated_json()
        features = [data[name] for name in FEATURE_NAMES]
        
        from backend import models as ml_models
        
        result = ml_models.get_shap_breakdown(model, features)
        return success(result)
    except Exception as e:
        logger.exception("SHAP analysis error")
        return error(f"SHAP analysis error: {str(e)}", status=500)


@prediction_bp.route('/admet', methods=['POST'])
@validate_json(ADMETRequestSchema)
@validate_model()
def admet_analysis():
    """Get ADMET (pharmacokinetics) properties."""
    try:
        data = get_validated_json()
        features = [data[name] for name in FEATURE_NAMES]
        
        from backend import models as ml_models
        
        result = ml_models.compute_admet(features)
        return success(result)
    except Exception as e:
        logger.exception("ADMET analysis error")
        return error(f"ADMET analysis error: {str(e)}", status=500)


@prediction_bp.route('/predict-ta', methods=['POST'])
@prediction_bp.route('/predict-therapeutic-area', methods=['POST'])
@validate_json(PredictTherapeuticAreaRequestSchema)
@validate_model()
def predict_therapeutic_area():
    """
    Predict success probability by therapeutic area.
    Compares against therapeutic area-specific baselines.
    """
    try:
        data = get_validated_json()
        features = [data[name] for name in FEATURE_NAMES]
        
        from backend import models as ml_models
        
        ta_key = data.get("therapeutic_area") or data.get("theraputic_area") or "oncology"
        compare_all = data.get("compare_all", False)
        
        # TA-specific success rates (from app.py)
        TA_RATES = {
            "oncology": {"phase1": 0.67, "phase2": 0.40, "phase3": 0.58, "baseline": 0.051},
            "cns": {"phase1": 0.52, "phase2": 0.22, "phase3": 0.50, "baseline": 0.082},
            "rare": {"phase1": 0.72, "phase2": 0.52, "phase3": 0.70, "baseline": 0.165},
            "cardiology": {"phase1": 0.60, "phase2": 0.45, "phase3": 0.60, "baseline": 0.073},
            "infectious": {"phase1": 0.62, "phase2": 0.48, "phase3": 0.68, "baseline": 0.096},
            "metabolic": {"phase1": 0.65, "phase2": 0.42, "phase3": 0.62, "baseline": 0.088},
        }
        
        def calc_ta_result(ta):
            rates = TA_RATES.get(ta, TA_RATES["oncology"])
            prob = ml_models.predict_single(model, features)
            p1 = rates["phase1"] * (0.7 + prob * 0.3)
            p2 = rates["phase2"] * (0.6 + prob * 0.4)
            p3 = rates["phase3"] * (0.7 + prob * 0.3)
            overall = p1 * p2 * p3
            return {
                "therapeutic_area": ta,
                "success_probability": round(prob, 4),
                "phase_probabilities": {
                    "phase1": round(p1*100, 1),
                    "phase2": round(p2*100, 1),
                    "phase3": round(p3*100, 1),
                    "overall_pos": round(overall*100, 1),
                    "uplift_vs_ta_baseline": round(overall/max(rates["baseline"], 0.001), 2),
                }
            }
        
        if compare_all:
            results = sorted([calc_ta_result(ta) for ta in TA_RATES],
                            key=lambda x: x["success_probability"], reverse=True)
            best = results[0] if results else None
            return success({
                "compound_name": data.get("compound_name", "Unknown"),
                "all_ta_results": results,
                "best_indication": best["therapeutic_area"] if best else None,
                "worst_indication": results[-1]["therapeutic_area"] if results else None,
            })
        
        return success(calc_ta_result(ta_key))
    except Exception as e:
        logger.exception("Therapeutic area prediction error")
        return error(f"Therapeutic area error: {str(e)}", status=500)
