import jwt
from api import app, JWT_SECRET, JWT_ALGORITHM


def _make_token(role: str = 'researcher') -> str:
    payload = {
        "sub": "test-user@nexuscliniq.ai",
        "email": "test-user@nexuscliniq.ai",
        "role": role,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def test_health():
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        print("Health check passed.")

def test_predict():
    with app.test_client() as client:
        payload = {
            "toxicity": 0.8,
            "bioavailability": 0.5,
            "solubility": 0.5,
            "binding": 0.8,
            "molecular_weight": 0.5
        }
        response = client.post('/predict', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert "success_probability" in data
        assert "warnings" in data
        assert "High toxicity risk detected" in data["warnings"]
        print(f"Predict single passed.")

def test_predict_batch():
    with app.test_client() as client:
        payload = [
            {
                "toxicity": 0.8, "bioavailability": 0.5, "solubility": 0.5, 
                "binding": 0.8, "molecular_weight": 0.5
            },
            {
                "toxicity": 0.2, "bioavailability": 0.9, "solubility": 0.8, 
                "binding": 0.9, "molecular_weight": 0.4
            }
        ]
        response = client.post('/predict-batch', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert "success_probabilities" in data
        assert len(data["success_probabilities"]) == 2
        print(f"Predict batch passed.")

def test_predict_extended():
    """Verify new fields are returned in enhanced /predict response."""
    with app.test_client() as client:
        payload = {
            "toxicity": 0.3,
            "bioavailability": 0.7,
            "solubility": 0.6,
            "binding": 0.8,
            "molecular_weight": 0.5
        }
        response = client.post('/predict', json=payload)
        data = response.get_json()
        
        assert "success_probability" in data      # existing field
        assert "warnings" in data                  # existing field
        assert "confidence_interval" in data       # NEW
        assert "shap_values" in data               # NEW
        assert "phase_probabilities" in data       # NEW
        
        ci = data["confidence_interval"]
        assert ci["p10"] <= ci["p50"] <= ci["p90"]
        
        shap = data["shap_values"]
        assert all(k in shap for k in [
            "toxicity","bioavailability",
            "solubility","binding","molecular_weight"
        ])
        
        phases = data["phase_probabilities"]
        assert "overall_pos" in phases
        assert "uplift_vs_baseline" in phases
        assert phases["uplift_vs_baseline"] > 0
        
        print(f"Extended predict passed: PoS={phases['overall_pos']}%, Uplift={phases['uplift_vs_baseline']}x")

def test_financial_engine():
    """Unit test financial calculations."""
    from services.financial_engine import compute_npv
    result = compute_npv({"ai":180,"clinical":150,"ma":90,"ops":50,"reg":30})
    assert result["ai"]["npv"] > 0
    assert result["traditional"]["npv"] > 0
    assert result["total_allocated"] == 500
    assert result["budget_status"] == "on_budget"
    print(f"Financial engine passed: AI NPV = ${result['ai']['npv']}M")

def test_sensitivity():
    """Tornado chart bars should be sorted by absolute swing."""
    from services.sensitivity import run_tornado
    result = run_tornado({"ai":180,"clinical":150,"ma":90,"ops":50,"reg":30})
    bars = result["bars"]
    swings = [abs(b["swing"]) for b in bars]
    assert swings == sorted(swings, reverse=True), "Bars not sorted by impact"
    print(f"Sensitivity passed: top driver = {bars[0]['label']}")

def test_ensemble():
    with app.test_client() as c:
        r = c.post('/predict-ensemble', json={
            "toxicity":0.3,"bioavailability":0.7,
            "solubility":0.6,"binding":0.8,"molecular_weight":0.5
        })
        d = r.get_json()
        assert "ensemble_probability" in d
        assert "confidence_band" in d
        assert d["confidence_band"]["low"] <= d["ensemble_probability"]
        assert d["confidence_label"] in ["Very high", "High", "Moderate", "Low - models disagree", "Low — models disagree"]
        print(f"Ensemble: {d['ensemble_probability']:.2%} — {d['confidence_label']}")

def test_counterfactual():
    with app.test_client() as c:
        r = c.post('/counterfactual', json={
            "toxicity":0.85,"bioavailability":0.2,
            "solubility":0.3,"binding":0.4,"molecular_weight":0.5,
            "target_probability": 0.70
        })
        d = r.get_json()
        assert "reachable" in d
        if d["reachable"]:
            assert "changes_required" in d
            assert d["achieved_prob"] >= 0.70
        print(f"Counterfactual: {d.get('recommendation','N/A')}")

def test_portfolio():
    with app.test_client() as c:
        r = c.post('/optimize-portfolio', json={
            "budget_m": 500,
            "compounds": [
                {"id":"A","name":"Cmpd A","toxicity":0.2,"bioavailability":0.8,
                 "solubility":0.7,"binding":0.9,"molecular_weight":0.4,
                 "development_cost_m":120,"peak_revenue_m":800,"time_to_market_yr":8},
                {"id":"B","name":"Cmpd B","toxicity":0.7,"bioavailability":0.3,
                 "solubility":0.4,"binding":0.5,"molecular_weight":0.6,
                 "development_cost_m":90,"peak_revenue_m":400,"time_to_market_yr":10},
                {"id":"C","name":"Cmpd C","toxicity":0.1,"bioavailability":0.9,
                 "solubility":0.8,"binding":0.85,"molecular_weight":0.35,
                 "development_cost_m":200,"peak_revenue_m":1200,"time_to_market_yr":7},
            ]
        })
        d = r.get_json()
        assert "optimal_portfolio" in d
        assert d["total_cost_m"] <= 500
        print(f"Portfolio: {d['recommendation']}")

def test_pdf_export():
    with app.test_client() as c:
        r = c.post('/export/pdf', json={"company":"NovaCura Test"})
        assert r.status_code == 200
        assert r.content_type == "application/pdf"
        assert len(r.data) > 1000  # non-empty PDF
        print(f"PDF export: {len(r.data):,} bytes")

def test_gxp_validation():
    with app.test_client() as c:
        # Should reject out-of-range value
        r = c.post('/predict', json={
            "toxicity":1.5,"bioavailability":0.7,
            "solubility":0.6,"binding":0.8,"molecular_weight":0.5
        })
        assert r.status_code == 422
        d = r.get_json()
        assert d["validation"]["valid"] == False
        print(f"GxP validation correctly rejected: {d['validation']['errors']}")

def test_transparency_report():
    with app.test_client() as c:
        r = c.get('/transparency-report')
        d = r.get_json()
        assert "model_identity" in d
        assert "regulatory_alignment" in d
        assert "bias_and_fairness" in d
        print(f"Transparency report: {d['model_identity']['name']}")


def test_admin_routes_require_auth():
    with app.test_client() as c:
        r = c.get('/admin/system-health')
        assert r.status_code == 401
        print('Admin route correctly rejected missing auth token.')


def test_admin_routes_require_admin_role():
    token = _make_token('researcher')
    with app.test_client() as c:
        r = c.get('/admin/system-health', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 403
        print('Admin route correctly rejected non-admin role.')


def test_admin_system_health_succeeds_for_admin():
    token = _make_token('admin')
    with app.test_client() as c:
        r = c.get('/admin/system-health', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
        data = r.get_json()
        assert data.get('status') == 'ok'
        assert 'auth' in data
        print('Admin system health returned status ok for admin token.')

if __name__ == "__main__":
    test_health()
    test_predict()
    test_predict_batch()
    test_predict_extended()
    test_financial_engine()
    test_sensitivity()
    
    # New NovaCura Endpoints
    test_ensemble()
    test_counterfactual()
    test_portfolio()
    test_pdf_export()
    test_gxp_validation()
    test_transparency_report()
    test_admin_routes_require_auth()
    test_admin_routes_require_admin_role()
    test_admin_system_health_succeeds_for_admin()
    
    print("\nAll tests passed ✓")
