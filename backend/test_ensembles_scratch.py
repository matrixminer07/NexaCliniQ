import models

print("Loading Ensemble...")
ensemble = models.load_ensemble()
print("Ensemble Loaded!")

features = [0.3, 0.7, 0.6, 0.8, 0.5]
print("Running Predict Ensemble...")
res = models.predict_ensemble(ensemble, features)
print(res)

print("Loading Random Forest Model...")
model = models.load_model()
print("Running Counterfactual Generator...")
cf = models.generate_counterfactual(model, features)
print(cf)

print("Running SHAP breakdown...")
shap_res = models.get_shap_breakdown(model, features)
print(shap_res)
