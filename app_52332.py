import streamlit as st
import requests
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import base64
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

# Configuration
API_BASE_URL = "http://127.0.0.1:52332"
VIDEO_PATH = Path(__file__).resolve().parent / "video4.mp4"


@st.cache_data(show_spinner=False)
def _load_video_base64(path: str) -> str:
    """Cache encoded video so it is not re-read on every rerun."""
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")


def inject_background_video(video_path: Path) -> None:
    """Render a fixed full-screen horizontal background video layer."""
    if not video_path.exists():
        st.warning(f"Background video not found: {video_path}")
        return

    encoded_video = _load_video_base64(str(video_path))
    st.markdown(
        f"""
        <style>
            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"],
            [data-testid="stMainBlockContainer"] {{
                background: transparent !important;
            }}
            #bg-video-wrap {{
                position: fixed;
                inset: 0;
                z-index: 0;
                overflow: hidden;
                pointer-events: none;
            }}
            #bg-video-wrap video {{
                position: absolute;
                top: 50%;
                left: 50%;
                min-width: 100vw;
                min-height: 100vh;
                width: 100vw;
                height: 100vh;
                transform: translate(-50%, -50%);
                object-fit: cover;
                object-position: center center;
                filter: saturate(1.05) contrast(1.02);
            }}
            #bg-shade {{
                position: fixed;
                inset: 0;
                z-index: 1;
                background: linear-gradient(120deg, rgba(3, 8, 18, 0.78), rgba(3, 8, 18, 0.40) 45%, rgba(3, 8, 18, 0.76));
                pointer-events: none;
            }}
            [data-testid="stAppViewContainer"] > .main,
            [data-testid="stMainBlockContainer"],
            [data-testid="stSidebar"],
            [data-testid="stSidebar"] > div:first-child,
            [data-testid="stHeader"] {{
                position: relative;
                z-index: 2;
            }}
            [data-testid="stHeader"] {{
                background: rgba(0, 0, 0, 0);
            }}
            [data-testid="stSidebar"] > div:first-child {{
                background: rgba(8, 18, 32, 0.58);
                backdrop-filter: blur(6px);
            }}
            .glass-card {{
                border: 1px solid rgba(194, 223, 255, 0.25);
                border-radius: 16px;
                padding: 14px 16px;
                background: rgba(7, 18, 35, 0.58);
                backdrop-filter: blur(6px);
                margin-bottom: 14px;
            }}
            .hero-title {{
                font-size: 2rem;
                margin-bottom: 0.25rem;
                color: #f0f7ff;
            }}
            .hero-subtitle {{
                color: #c7dcf5;
                margin-bottom: 0.75rem;
            }}
            @media (max-width: 768px) {{
                .hero-title {{
                    font-size: 1.45rem;
                }}
            }}
        </style>

        <div id="bg-video-wrap">
            <video autoplay muted loop playsinline>
                <source src="data:video/mp4;base64,{encoded_video}" type="video/mp4">
            </video>
        </div>
        <div id="bg-shade"></div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="hero-title">NovaCura Drug Discovery Intelligence Platform</div>
            <div class="hero-subtitle">Connected endpoint: {API_BASE_URL}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


MODEL_VERSION = "synthetic_v2"
SYNTHETIC_DATASET_PROFILES = [
    ("balanced_screening", 260),
    ("lead_optimized", 360),
    ("high_risk", 260),
    ("noisy_screening", 220),
]


def _generate_synthetic_profile(profile_name: str, n_samples: int, seed_offset: int) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    rng = np.random.default_rng(42 + seed_offset)

    if profile_name == "lead_optimized":
        toxicity = rng.beta(1.6, 4.8, n_samples)
        bioavailability = rng.beta(4.6, 1.7, n_samples)
        solubility = rng.beta(3.8, 1.8, n_samples)
        binding = rng.beta(4.3, 1.6, n_samples)
        molecular_weight = rng.beta(2.1, 2.6, n_samples)
        bias = 0.18
        noise = 0.05
        threshold = 0.48
    elif profile_name == "high_risk":
        toxicity = rng.beta(4.9, 1.7, n_samples)
        bioavailability = rng.beta(1.9, 4.1, n_samples)
        solubility = rng.beta(1.8, 4.2, n_samples)
        binding = rng.beta(2.0, 3.8, n_samples)
        molecular_weight = rng.beta(3.6, 2.0, n_samples)
        bias = -0.24
        noise = 0.07
        threshold = 0.54
    elif profile_name == "noisy_screening":
        toxicity = rng.beta(2.3, 2.3, n_samples)
        bioavailability = rng.beta(2.6, 2.4, n_samples)
        solubility = rng.beta(2.5, 2.5, n_samples)
        binding = rng.beta(2.4, 2.6, n_samples)
        molecular_weight = rng.beta(2.8, 2.2, n_samples)
        bias = 0.02
        noise = 0.14
        threshold = 0.50
    else:
        toxicity = rng.beta(2.2, 3.4, n_samples)
        bioavailability = rng.beta(2.7, 2.0, n_samples)
        solubility = rng.beta(2.4, 2.2, n_samples)
        binding = rng.beta(2.8, 1.9, n_samples)
        molecular_weight = rng.beta(2.5, 2.3, n_samples)
        bias = 0.04
        noise = 0.08
        threshold = 0.50

    score = (
        (bioavailability * 0.34)
        + (binding * 0.31)
        + (solubility * 0.22)
        + ((1 - molecular_weight) * 0.12)
        - (toxicity * 0.43)
        + (bioavailability * binding * 0.08)
        - (toxicity * solubility * 0.05)
        + bias
    )
    score += rng.normal(0, noise, n_samples)
    success = (score > threshold).astype(int)

    X = np.column_stack((toxicity, bioavailability, solubility, binding, molecular_weight))
    summary = {
        "Dataset": profile_name.replace("_", " ").title(),
        "Samples": int(n_samples),
        "Success Rate": float(success.mean()),
        "Avg Toxicity": float(np.mean(toxicity)),
        "Avg Bioavailability": float(np.mean(bioavailability)),
        "Avg Solubility": float(np.mean(solubility)),
        "Avg Binding": float(np.mean(binding)),
        "Avg Molecular Weight": float(np.mean(molecular_weight)),
    }
    return X, success, summary


def _build_synthetic_training_data() -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    features = []
    labels = []
    summaries = []

    for seed_offset, (profile_name, n_samples) in enumerate(SYNTHETIC_DATASET_PROFILES):
        X_part, y_part, summary = _generate_synthetic_profile(profile_name, n_samples, seed_offset)
        features.append(X_part)
        labels.append(y_part)
        summaries.append(summary)

    X = np.vstack(features)
    y = np.concatenate(labels)
    order = np.random.default_rng(42).permutation(len(X))

    return X[order], y[order], pd.DataFrame(summaries)


@st.cache_resource(show_spinner=False)
def get_local_rf_model() -> tuple[RandomForestClassifier, pd.DataFrame, dict[str, float], pd.DataFrame]:
    X, y, dataset_summary = _build_synthetic_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    test_prob = model.predict_proba(X_test)[:, 1]
    test_pred = (test_prob >= 0.5).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_test, test_pred)),
        "auc": float(roc_auc_score(y_test, test_prob)) if len(np.unique(y_test)) > 1 else 0.0,
        "precision": float(precision_score(y_test, test_pred, zero_division=0)),
        "recall": float(recall_score(y_test, test_pred, zero_division=0)),
        "f1": float(f1_score(y_test, test_pred, zero_division=0)),
    }

    importance = pd.DataFrame(
        {
            "Feature": ["Toxicity", "Bioavailability", "Solubility", "Binding Affinity", "Molecular Weight"],
            "Importance": model.feature_importances_,
        }
    ).sort_values("Importance", ascending=False)

    model.model_version = MODEL_VERSION
    model.synthetic_training_summary_ = {
        "model_version": MODEL_VERSION,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "total_samples": int(len(X)),
        **metrics,
    }

    return model, importance, metrics, dataset_summary


def predict_local_probability(tox: float, bio: float, sol: float, bind: float, mw: float) -> float:
    model, _, _, _ = get_local_rf_model()
    input_data = np.array([[tox, bio, sol, bind, mw]])
    return float(model.predict_proba(input_data)[0][1])


def render_local_model_insights(tox: float, bio: float, sol: float, bind: float, mw: float) -> None:
    _, importance, metrics, dataset_summary = get_local_rf_model()
    probability = predict_local_probability(tox, bio, sol, bind, mw)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🌳 Local Random Forest Model")
    st.caption("This embedded model is trained on multiple synthetic cohorts so it stays available when the backend is offline.")
    st.subheader(f"📊 Predicted Success Probability: {probability * 100:.2f}%")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Validation accuracy", f"{metrics['accuracy']:.1%}")
    metric_cols[1].metric("Validation AUC", f"{metrics['auc']:.1%}")
    metric_cols[2].metric("Validation F1", f"{metrics['f1']:.1%}")
    metric_cols[3].metric("Dataset count", str(len(dataset_summary)))

    if tox > 0.7:
        st.warning("⚠️ High toxicity risk detected")
    if bio < 0.4:
        st.warning("⚠️ Low bioavailability (absorption) risk")

    st.write("### 📈 Feature Importance (Model Insight)")
    st.bar_chart(importance.set_index("Feature"))

    with st.expander("Synthetic training datasets"):
        st.dataframe(dataset_summary, use_container_width=True)

    st.write("### 🧠 Model Explanation")
    st.write(
        "The Random Forest model uses multiple decision trees to evaluate how different drug properties interact. "
        "It is trained on several synthetic dataset profiles with different risk and success patterns, which makes the local fallback more robust than a single tiny sample set."
    )
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="NovaCura v2 - Port 52332",
        page_icon="🧬",
        layout="wide"
    )

    inject_background_video(VIDEO_PATH)
    render_hero()
    
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
    
    tab_predict, tab_smiles, tab_ta, tab_active = st.tabs([
        "Core Prediction",
        "SMILES Pipeline",
        "Therapeutic Areas",
        "Active Learning",
    ])

    with tab_predict:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("🔬 Feature Inputs")
            tox_a = st.slider("Toxicity", 0.0, 1.0, 0.3, key="tox_52332")
            bio_a = st.slider("Bioavailability", 0.0, 1.0, 0.7, key="bio_52332")
            sol_a = st.slider("Solubility", 0.0, 1.0, 0.6, key="sol_52332")
            bind_a = st.slider("Binding Affinity", 0.0, 1.0, 0.8, key="bind_52332")
            mw_a = st.slider("Molecular Weight", 0.0, 1.0, 0.5, key="mw_52332")

            if st.button("Predict Success", type="primary", key="predict_52332"):
                local_probability = predict_local_probability(tox_a, bio_a, sol_a, bind_a, mw_a)
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
                        st.warning("Backend prediction unavailable. Showing the local Random Forest result instead.")
                        st.subheader(f"📊 Predicted Success Probability: {local_probability * 100:.2f}%")
                        if tox_a > 0.7:
                            st.warning("⚠️ High toxicity risk detected")
                        if bio_a < 0.4:
                            st.warning("⚠️ Low bioavailability (absorption) risk")
                except Exception as e:
                    st.warning(f"Backend API error: {e}. Showing the local Random Forest result instead.")
                    st.subheader(f"📊 Predicted Success Probability: {local_probability * 100:.2f}%")
                    if tox_a > 0.7:
                        st.warning("⚠️ High toxicity risk detected")
                    if bio_a < 0.4:
                        st.warning("⚠️ Low bioavailability (absorption) risk")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("📊 Probability Gauge")
            if 'tox_52332' in st.session_state:
                prob = calculate_probability(
                    st.session_state.tox_52332,
                    st.session_state.bio_52332,
                    st.session_state.sol_52332,
                    st.session_state.bind_52332,
                    st.session_state.mw_52332
                )

                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=prob * 100,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Success Probability"},
                    delta={'reference': 50},
                    gauge={
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
            st.markdown("</div>", unsafe_allow_html=True)

            render_local_model_insights(tox_a, bio_a, sol_a, bind_a, mw_a)

    with tab_smiles:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("🧪 SMILES Prediction")
        col1, col2 = st.columns([3, 1])

        with col1:
            smiles_input = st.text_input(
                "Enter SMILES string",
                placeholder="e.g. CC(=O)Oc1ccccc1C(=O)O",
                help="Auto-computes all features from molecular structure",
                key="smiles_52332"
            )

        with col2:
            if st.button("Predict from SMILES", key="predict_smiles_52332") and smiles_input:
                try:
                    response = requests.post(f"{API_BASE_URL}/predict-smiles", json={
                        "smiles": smiles_input,
                        "compound_name": "SMILES Test"
                    }, timeout=10)

                    if response.status_code == 200:
                        result = response.json()
                        st.success("SMILES prediction complete")
                        st.json(result)
                    else:
                        st.error(f"SMILES prediction failed: {response.status_code}")
                except Exception as e:
                    st.error(f"API Error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_ta:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("🏥 Therapeutic Area Analysis")
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
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_active:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("🎯 Active Learning Queue")
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
        st.markdown("</div>", unsafe_allow_html=True)

def calculate_probability(tox, bio, sol, bind, mw):
    """Probability derived from the embedded local Random Forest demo model."""
    return predict_local_probability(tox, bio, sol, bind, mw)

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
