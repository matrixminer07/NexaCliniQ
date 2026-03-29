import streamlit as st
import requests
import json
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Configuration
API_BASE_URL = "http://127.0.0.1:52332"

def main():
    st.set_page_config(
        page_title="NovaCura v2 - Port 52332",
        page_icon="🧬",
        layout="wide"
    )
    
    st.title("🧬 NovaCura Drug Discovery Intelligence Platform")
    st.markdown(f"*API Endpoint: `{API_BASE_URL}*")
    st.markdown("---")
    
    # Sidebar with API status
    with st.sidebar:
        st.header("🔗 API Status")
        
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=3)
            if response.status_code == 200:
                health = response.json()
                st.success("✅ API Connected")
                st.json(health)
            else:
                st.error(f"❌ API Error: {response.status_code}")
        except Exception as e:
            st.error(f"❌ API Unreachable: {e}")
        
        st.divider()
        st.header("🧪 Test Features")
        
        if st.button("Test All Endpoints"):
            test_all_endpoints()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🔬 Core Prediction")
        
        # Input sliders
        tox_a = st.slider("Toxicity", 0.0, 1.0, 0.3, key="tox_52332")
        bio_a = st.slider("Bioavailability", 0.0, 1.0, 0.7, key="bio_52332")
        sol_a = st.slider("Solubility", 0.0, 1.0, 0.6, key="sol_52332")
        bind_a = st.slider("Binding Affinity", 0.0, 1.0, 0.8, key="bind_52332")
        mw_a = st.slider("Molecular Weight", 0.0, 1.0, 0.5, key="mw_52332")
        
        if st.button("Predict Success", type="primary", key="predict_52332"):
            features = [tox_a, bio_a, sol_a, bind_a, mw_a]
            
            try:
                response = requests.post(f"{API_BASE_URL}/predict", json={
                    "toxicity": tox_a,
                    "bioavailability": bio_a,
                    "solubility": sol_a,
                    "binding": bind_a,
                    "molecular_weight": mw_a,
                    "compound_name": "Test Compound"
                }, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    display_prediction_result(result)
                else:
                    st.error(f"Prediction failed: {response.status_code}")
            except Exception as e:
                st.error(f"API Error: {e}")
    
    with col2:
        st.header("📊 Probability Gauge")
        
        # Create gauge
        if 'tox_52332' in st.session_state:
            prob = calculate_probability(
                st.session_state.tox_52332,
                st.session_state.bio_52332,
                st.session_state.sol_52332,
                st.session_state.bind_52332,
                st.session_state.mw_52332
            )
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = prob * 100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Success Probability"},
                delta = {'reference': 50},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 30], 'color': "red"},
                        {'range': [30, 70], 'color': "yellow"},
                        {'range': [70, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 85
                    }
                }
            ))
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # SMILES Input Section
    st.header("🧪 SMILES Pipeline")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        smiles_input = st.text_input(
            "Enter SMILES string",
            placeholder="e.g. CC(=O)Oc1ccccc1C(=O)O",
            help="Auto-computes all features from molecular structure",
            key="smiles_52332"
        )
    
    with col2:
        if st.button("Predict from SMILES", key="predict_smiles_52332"):
            if smiles_input:
                try:
                    response = requests.post(f"{API_BASE_URL}/predict-smiles", json={
                        "smiles": smiles_input,
                        "compound_name": "SMILES Test"
                    }, timeout=10)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ SMILES prediction complete!")
                        st.json(result)
                    else:
                        st.error(f"SMILES prediction failed: {response.status_code}")
                except Exception as e:
                    st.error(f"API Error: {e}")
    
    st.markdown("---")
    
    # Therapeutic Areas Section
    st.header("🏥 Therapeutic Area Analysis")
    
    if st.button("Compare All Therapeutic Areas", key="compare_ta_52332"):
        features = [
            st.session_state.get('tox_52332', 0.3),
            st.session_state.get('bio_52332', 0.7),
            st.session_state.get('sol_52332', 0.6),
            st.session_state.get('bind_52332', 0.8),
            st.session_state.get('mw_52332', 0.5)
        ]
        
        try:
            response = requests.post(f"{API_BASE_URL}/predict-ta", json={
                "features": features,
                "compare_all": True
            }, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                display_therapeutic_areas(result)
            else:
                st.error(f"TA comparison failed: {response.status_code}")
        except Exception as e:
            st.error(f"API Error: {e}")
    
    st.markdown("---")
    
    # Active Learning Queue
    st.header("🎯 Active Learning Queue")
    
    if st.button("Show Active Learning Queue", key="show_queue_52332"):
        try:
            response = requests.get(f"{API_BASE_URL}/active-learning/queue", timeout=10)
            if response.status_code == 200:
                result = response.json()
                display_active_learning_queue(result)
            else:
                st.error(f"Queue fetch failed: {response.status_code}")
        except Exception as e:
            st.error(f"API Error: {e}")

def calculate_probability(tox, bio, sol, bind, mw):
    """Simple probability calculation for demo"""
    return max(0, min(1, (bio * 0.3 + bind * 0.3 + sol * 0.2 - tox * 0.4)))

def display_prediction_result(result):
    """Display prediction results"""
    prob = result.get('success_probability', 0)
    verdict = result.get('verdict', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Success Probability", f"{prob:.1%}")
        st.metric("Verdict", verdict.get('verdict', 'UNKNOWN'))
    
    with col2:
        if 'confidence_interval' in result:
            ci = result['confidence_interval']
            st.metric("P10", f"{ci.get('p10', 0):.3f}")
            st.metric("P90", f"{ci.get('p90', 0):.3f}")
    
    with col3:
        if 'phase_probabilities' in result:
            phases = result['phase_probabilities']
            st.metric("Phase 1", f"{phases.get('phase1', 0):.1f}%")
            st.metric("Overall PoS", f"{phases.get('overall_pos', 0):.1f}%")
    
    if 'warnings' in result and result['warnings']:
        st.warning("⚠️ Warnings:")
        for warning in result['warnings']:
            st.write(f"• {warning}")

def display_therapeutic_areas(result):
    """Display therapeutic area comparison"""
    if 'therapeutic_areas' in result:
        areas = result['therapeutic_areas']
        
        for ta_key, ta_data in areas.items():
            with st.expander(f"🏥 {ta_data.get('label', ta_key)}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Probability", f"{ta_data.get('probability', 0):.1%}")
                    st.metric("Phase 1", f"{ta_data.get('phase_probabilities', {}).get('phase1', 0):.1f}%")
                
                with col2:
                    st.metric("Phase 2", f"{ta_data.get('phase_probabilities', {}).get('phase2', 0):.1f}%")
                    st.metric("Phase 3", f"{ta_data.get('phase_probabilities', {}).get('phase3', 0):.1f}%")

def display_active_learning_queue(result):
    """Display active learning queue"""
    if 'queue' in result:
        queue = result['queue']
        
        if queue:
            st.write(f"📋 Queue has {len(queue)} compounds")
            
            for item in queue[:10]:  # Show first 10
                with st.expander(f"🔬 {item.get('compound_name', 'Unknown')}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Probability", f"{item.get('probability', 0):.1%}")
                        st.metric("Uncertainty", f"{item.get('uncertainty', 0):.3f}")
                    
                    with col2:
                        st.metric("Priority Score", f"{item.get('priority_score', 0):.1f}")
                        st.write(f"**Status:** {item.get('status', 'Unknown')}")
                    
                    with col3:
                        if 'features' in item:
                            features = item['features']
                            st.write("**Features:**")
                            for key, value in features.items():
                                st.write(f"• {key}: {value:.3f}")
        else:
            st.info("📋 Queue is empty")

def test_all_endpoints():
    """Test all available endpoints"""
    endpoints = [
        ("/health", "GET"),
        ("/stats", "GET"),
        ("/therapeutic-areas", "GET"),
        ("/active-learning/stats", "GET"),
        ("/data/chembl-status", "GET"),
        ("/gnn/status", "GET")
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{API_BASE_URL}{endpoint}", timeout=5)
            
            st.write(f"{'✅' if response.status_code == 200 else '❌'} {method} {endpoint}: {response.status_code}")
        except Exception as e:
            st.write(f"❌ {method} {endpoint}: {e}")

if __name__ == "__main__":
    main()
