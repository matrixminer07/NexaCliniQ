import requests
import json

# Test the NovaCura API on port 52332
def test_api():
    base_url = "http://127.0.0.1:52332"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        health_data = response.json()
        print("✅ Health Check:")
        print(json.dumps(health_data, indent=2))
        
        # Test prediction endpoint
        test_data = {
            "toxicity": 0.3,
            "bioavailability": 0.7,
            "solubility": 0.6,
            "binding": 0.8,
            "molecular_weight": 0.5,
            "compound_name": "Test Compound"
        }
        
        response = requests.post(f"{base_url}/predict", json=test_data, timeout=5)
        pred_data = response.json()
        print("\n✅ Prediction Test:")
        print(json.dumps(pred_data, indent=2))
        
        # Test SMILES endpoint if available
        smiles_data = {
            "smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "compound_name": "Aspirin"
        }
        
        response = requests.post(f"{base_url}/predict-smiles", json=smiles_data, timeout=5)
        if response.status_code == 200:
            smiles_result = response.json()
            print("\n✅ SMILES Prediction Test:")
            print(json.dumps(smiles_result, indent=2))
        else:
            print(f"\n⚠️ SMILES endpoint: {response.status_code}")
        
        # Test therapeutic areas
        ta_data = {
            "features": [0.3, 0.7, 0.6, 0.8, 0.5],
            "compare_all": True
        }
        
        response = requests.post(f"{base_url}/predict-ta", json=ta_data, timeout=5)
        if response.status_code == 200:
            ta_result = response.json()
            print("\n✅ Therapeutic Areas Test:")
            print(json.dumps(ta_result, indent=2))
        else:
            print(f"\n⚠️ Therapeutic areas endpoint: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_api()
