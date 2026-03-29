from datetime import datetime, UTC

def generate_transparency_report(model_info: dict, 
                                  validation_results: dict) -> dict:
    """
    Generates a structured AI model card / transparency report.
    Aligned with FDA AI/ML Action Plan (2021) and EU AI Act requirements.
    """
    return {
        "report_type": "AI Model Transparency Report",
        "generated_at": datetime.now(UTC).isoformat(),
        "version": "1.0",

        "model_identity": {
            "name":        "NovaCura Drug Success Predictor",
            "type":        model_info.get("type", "Random Forest Classifier"),
            "version":     model_info.get("version", "1.0.0"),
            "framework":   "scikit-learn",
            "intended_use": (
                "Predict the probability of a drug candidate's clinical success "
                "based on physicochemical properties. For decision support only - "
                "not a substitute for expert scientific judgment."
            ),
            "out_of_scope": [
                "Primary endpoint for regulatory submission",
                "Replacement for in vitro or in vivo testing",
                "Predictions on compound classes outside training distribution"
            ]
        },

        "training_data": {
            "source":           model_info.get("data_source", "Synthetic - replace with ChEMBL"),
            "sample_size":      model_info.get("training_samples", 300),
            "feature_count":    5,
            "features":         ["toxicity","bioavailability","solubility",
                                  "binding affinity","molecular weight"],
            "label_definition": "Success = probability of approval > 50% based on simulated industry attrition rates",
            "known_limitations": [
                "Training data is synthetic - validation against real clinical outcomes required",
                "Does not model formulation, manufacturing, or commercial factors",
                "Molecular weight normalised 0-1; absolute MW not used"
            ]
        },

        "performance": {
            "cross_validated_accuracy": validation_results.get("accuracy", "N/A"),
            "auc_roc":                  validation_results.get("auc", "N/A"),
            "precision":                validation_results.get("precision", "N/A"),
            "recall":                   validation_results.get("recall", "N/A"),
            "calibration":              "Probability outputs calibrated via isotonic regression",
            "validation_method":        "5-fold stratified cross-validation"
        },

        "explainability": {
            "method":      "SHAP TreeExplainer",
            "output_type": "Per-prediction signed feature contributions",
            "audit_trail": "All predictions logged with input features and SHAP values",
            "human_review": "Predictions flagged as high-risk (toxicity > 0.7) require scientist review"
        },

        "bias_and_fairness": {
            "subgroup_analysis":  "Not yet performed - recommended before regulatory submission",
            "known_biases": [
                "Training data does not reflect rare disease compound profiles",
                "Binding affinity metric may vary by assay type"
            ],
            "mitigation_plan": "Expand training data to cover CNS, oncology, and rare disease compound libraries"
        },

        "regulatory_alignment": {
            "fda_ai_ml_action_plan": "Partially aligned - audit trail and human review implemented",
            "eu_ai_act_risk_class":  "High-risk (healthcare AI) - full compliance roadmap required",
            "ich_e9_r1":             "Estimand framework not yet applied to model outputs",
            "21_cfr_part_11":        "Electronic signature and audit trail - in development"
        },

        "update_policy": {
            "retraining_frequency": "Monthly or upon new clinical outcome data",
            "drift_monitoring":     "Prediction distribution monitored weekly",
            "version_control":      "All model versions archived with training data snapshot",
            "change_notification":  "Significant performance changes trigger stakeholder alert"
        }
    }
