"""
UPGRADE 7: LLM Natural Language Analyst
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ask questions in plain English. Claude reads all compound context and explains in accessible language.

Features:
  - Claude Sonnet 4 integration for scientific explanations
  - Context-aware responses using full compound data
  - Server-sent events for streaming responses
  - Suggested questions based on compound profile
  - Error handling with fallback messages

Setup:
  export ANTHROPIC_API_KEY=sk-ant-your-key-here
  pip install anthropic
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# ── Try importing Anthropic SDK ───────────────────────────────────────────────
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False
    print("Warning: Anthropic SDK not installed. Install with: pip install anthropic")


ANALYST_SYSTEM_INSTRUCTION = '''You are NovaCura AI Analyst, a pharmaceutical strategy and translational science assistant.
Your job is to answer using only provided context. If data is missing, say exactly what is missing.
Never fabricate trial outcomes, references, or numeric values.
Prioritize risk-aware, board-actionable recommendations.

Output format:
A) Executive answer (2-3 sentences)
B) Evidence from provided data
C) Scientific interpretation
D) Risks and uncertainties
E) Next best action (1 week, 1 month, 1 quarter)

Rules:
- Cite exact values from context (probability, SHAP drivers, ADMET flags, phase PoS).
- If confidence interval is wide or key fields are absent, reduce certainty and state why.
- Distinguish prediction probability from clinical truth.
- Keep under 280 words unless user asks for detail.
- Missing-data gate: if success_probability, shap, or admet is missing, include a section titled "Missing critical inputs".
- Numeric grounding: every recommendation must reference at least two quantitative fields.
- Uncertainty policy: if confidence interval width > 0.25, include "High prediction uncertainty" and lower action confidence.
- No-fabrication policy: if asked for external evidence not in context, answer "Not in provided context."'''


def _ci_bounds(ci: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    if not isinstance(ci, dict):
        return None, None
    low = ci.get("low")
    high = ci.get("high")
    if low is None or high is None:
        interval = ci.get("interval")
        if isinstance(interval, (list, tuple)) and len(interval) == 2:
            low, high = interval[0], interval[1]
    if low is None or high is None:
        lower_bound = ci.get("lower")
        upper_bound = ci.get("upper")
        if lower_bound is not None and upper_bound is not None:
            low, high = lower_bound, upper_bound
    if low is None or high is None:
        return None, None
    try:
        return float(low), float(high)
    except (TypeError, ValueError):
        return None, None


def retrieve_compound_context(model: Any = None, features: Optional[List[float]] = None,
                          compound_name: Optional[str] = None,
                          prediction_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve full context for a compound from various sources.
    """
    context: Dict[str, Any] = {
        "compound_name": compound_name or "Unknown",
        "prediction_id": prediction_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # If features provided directly
    if features and len(features) == 5:
        import models
        context.update({
            "features": {
                "toxicity": features[0],
                "bioavailability": features[1], 
                "solubility": features[2],
                "binding": features[3],
                "molecular_weight": features[4]
            }
        })
        
        # Compute predictions if model available
        if model:
            prob = models.predict_single(model, features)
            ci = models.predict_with_confidence(model, features)
            shap = models.get_shap_breakdown(model, features)
            phases = models.get_phase_probabilities(prob)
            verdict = models.classify_verdict(prob)
            admet = models.compute_admet(features)
            
            context.update({
                "success_probability": prob,
                "verdict": verdict,
                "confidence_interval": ci,
                "shap": shap,
                "phase_probabilities": phases,
                "admet": admet,
                "warnings": []
            })
            
            # Add warnings based on properties
            warnings = context.get("warnings")
            if isinstance(warnings, list):
                if features[0] > 0.7:  # High toxicity
                    warnings.append("High toxicity risk detected")
                if features[1] < 0.4:  # Low bioavailability
                    warnings.append("Low bioavailability risk")
    
    # Try to retrieve from database if prediction_id provided
    elif prediction_id:
        try:
            from database import get_history
            history = get_history(limit=100)
            for record in history:
                if record.get("id") == prediction_id:
                    context.update({
                        "compound_name": record.get("compound_name", compound_name),
                        "features": {
                            "toxicity": record["toxicity"],
                            "bioavailability": record["bioavailability"],
                            "solubility": record["solubility"],
                            "binding": record["binding"],
                            "molecular_weight": record["molecular_weight"]
                        },
                        "success_probability": record["probability"],
                        "verdict": {"verdict": record.get("verdict", "UNKNOWN")},
                        "warnings": record.get("warnings", []),
                        "notes": record.get("notes", ""),
                        "timestamp": record["timestamp"]
                    })
                    break
        except Exception:
            pass  # Database not available
    
    return context


def build_analyst_prompt(question: str, context: Dict[str, Any]) -> str:
    """
    Build a comprehensive prompt for Claude with full compound context.
    """
    prob = context.get("success_probability")
    verdict = context.get("verdict", {})
    ci = context.get("confidence_interval", {})
    phases = context.get("phase_probabilities", {})
    admet = context.get("admet", {})
    shap = context.get("shap", {})
    warnings = context.get("warnings", [])
    counterfactual = context.get("counterfactual", {})
    data_quality_flags = context.get("data_quality_flags", [])
    regulatory_flags = context.get("regulatory_flags", [])
    portfolio_context = context.get("portfolio_context", None)

    top_shap = []
    for c in shap.get("contributions", [])[:5] if isinstance(shap, dict) else []:
        try:
            top_shap.append(
                {
                    "feature": c.get("feature", "unknown"),
                    "shap": float(c.get("shap", 0.0)),
                    "direction": c.get("direction", "unknown"),
                }
            )
        except (TypeError, ValueError):
            continue

    low, high = _ci_bounds(ci)
    ci_width = round(high - low, 4) if low is not None and high is not None else None

    scaffold = {
        "compound_name": context.get("compound_name", "Unknown"),
        "prediction_id": context.get("prediction_id"),
        "success_probability": prob,
        "verdict": verdict,
        "confidence_interval": ci,
        "confidence_interval_width": ci_width,
        "phase_probabilities": phases,
        "admet": admet,
        "shap_top_drivers": top_shap,
        "warnings": warnings,
        "counterfactual_recommendation": counterfactual,
        "data_quality_flags": data_quality_flags,
        "regulatory_flags": regulatory_flags,
        "portfolio_context": portfolio_context,
    }

    prompt = (
        f"Question: {question}\n\n"
        "Structured context:\n\n"
        f"Compound: {scaffold['compound_name']}\n"
        f"Success probability: {scaffold['success_probability']}\n"
        f"Verdict: {json.dumps(scaffold['verdict'], ensure_ascii=True)}\n"
        f"Confidence interval: {json.dumps(scaffold['confidence_interval'], ensure_ascii=True)}\n"
        f"Phase probabilities: {json.dumps(scaffold['phase_probabilities'], ensure_ascii=True)}\n"
        f"ADMET: {json.dumps(scaffold['admet'], ensure_ascii=True)}\n"
        f"SHAP top drivers: {json.dumps(scaffold['shap_top_drivers'], ensure_ascii=True)}\n"
        f"Warnings: {json.dumps(scaffold['warnings'], ensure_ascii=True)}\n"
        f"Counterfactual recommendation: {json.dumps(scaffold['counterfactual_recommendation'], ensure_ascii=True)}\n"
        f"Data quality flags: {json.dumps(scaffold['data_quality_flags'], ensure_ascii=True)}\n"
        f"Regulatory context: {json.dumps(scaffold['regulatory_flags'], ensure_ascii=True)}\n"
        f"Portfolio context (optional): {json.dumps(scaffold['portfolio_context'], ensure_ascii=True)}\n\n"
        "Answer strictly using this context."
    )
    
    return prompt


def ask_analyst(question: str, context: Dict[str, Any],
                stream: bool = False) -> Dict[str, Any]:
    """
    Send question + context to Claude and get a plain-English answer.
    """
    if not ANTHROPIC_AVAILABLE:
        return {
            "answer": "Anthropic SDK not installed. Run: pip install anthropic",
            "error": "anthropic_not_installed",
        }
    if anthropic is None:
        return {
            "answer": "Anthropic SDK not installed. Run: pip install anthropic",
            "error": "anthropic_not_installed",
        }
    
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "answer": "ANTHROPIC_API_KEY not set. Add it to your .env file.",
            "error": "api_key_missing",
        }
    
    prompt = build_analyst_prompt(question, context)
    assert anthropic is not None
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        if stream:
            # Return a generator for streaming responses
            def response_stream():
                with client.messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                    system=ANALYST_SYSTEM_INSTRUCTION,
                ) as s:
                    for text in s.text_stream:
                        yield text
            return {"stream": response_stream(), "streaming": True}
        else:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
                system=ANALYST_SYSTEM_INSTRUCTION,
            )
            answer = ""
            for block in message.content:
                block_type = getattr(block, "type", "")
                if block_type == "text":
                    answer = getattr(block, "text", "")
                    if answer:
                        break

            if not answer:
                answer = "No text response returned by model."

            return {
                "answer":   answer,
                "question": question,
                "compound": context.get("compound_name", "Unknown"),
                "model":    "claude-sonnet-4-20250514",
                "tokens":   message.usage.output_tokens,
                "streaming": False,
            }
    
    except Exception as e:
        if anthropic and isinstance(e, anthropic.AuthenticationError):
            return {"answer": "Invalid API key.", "error": "auth_error"}
        if anthropic and isinstance(e, anthropic.RateLimitError):
            return {"answer": "Rate limit reached. Please wait a moment.", "error": "rate_limit"}
        return {"answer": f"LLM error: {str(e)}", "error": str(e)}


def get_suggested_questions(context: Dict) -> List[str]:
    """Generate contextual suggested questions based on compound profile."""
    prob = context.get("success_probability", 0.5)
    verdict = context.get("verdict", {}).get("verdict", "CAUTION")
    admet = context.get("admet", {})
    shap = context.get("shap", {})
    top = shap.get("top_driver", "binding")
    
    questions = [f"Why did this compound receive a {verdict} verdict?"]
    
    if prob < 0.5:
        questions.append("What are the biggest obstacles to this compound's success?")
        questions.append("What structural changes would most improve the success probability?")
    else:
        questions.append("What are this compound's strongest properties?")
        questions.append("What risks should we monitor in clinical development?")
    
    if admet and admet.get("herg_risk"):
        questions.append("How serious is the hERG cardiac risk and how can we mitigate it?")
    
    if admet and not admet.get("lipinski_pass"):
        questions.append("What do the Lipinski violations mean for oral bioavailability?")
    
    questions.append(f"Why is {top.replace('_',' ')} the most important feature for this compound?")
    questions.append("How does this compound compare to typical drugs in this class?")
    questions.append("What is the recommended next step for this compound?")
    
    return questions[:6]


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ROUTES (add to api.py)
# ─────────────────────────────────────────────────────────────────────────────

LLM_ROUTES = '''
# ── ADD TO api.py ─────────────────────────────────────────────────────────────

from llm_analyst import (
    retrieve_compound_context, ask_analyst, get_suggested_questions
)
from flask import Response, stream_with_context

@app.route("/analyst/ask", methods=["POST"])
def analyst_ask():
    """
    POST body:
      {
        "question": "Why did compound A fail?",
        "compound_name": "Compound A",        # look up from history
        "prediction_id": "abc123",            # or by ID
        "features": [0.8, 0.3, 0.3, 0.4, 0.5],  # or raw features
        "stream": false
      }
    """
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "question field required"}), 400
    
    context = retrieve_compound_context(
        compound_name = data.get("compound_name"),
        prediction_id = data.get("prediction_id"),
        model = model,
        features = data.get("features"),
    )
    
    if data.get("stream"):
        result = ask_analyst(question, context, stream=True)
        if result.get("streaming"):
            def generate():
                for chunk in result["stream"]:
                    yield f"data: {json.dumps({'chunk': chunk})}\\n\\n"
                yield "data: [DONE]\\n\\n"
            return Response(stream_with_context(generate()),
                            mimetype="text/event-stream")
    
    result = ask_analyst(question, context)
    return jsonify(result)

@app.route("/analyst/suggestions", methods=["POST"])
def analyst_suggestions():
    """
    POST body: {"features": [...]} or {"compound_name": "..."}
    Returns contextual suggested questions.
    """
    data = request.get_json()
    
    if data.get("features"):
        context = retrieve_compound_context(features=data["features"], model=model)
    elif data.get("compound_name"):
        # Look up from database
        from database import get_history
        history = get_history(limit=100)
        for record in history:
            if record.get("compound_name") == data["compound_name"]:
                context = retrieve_compound_context(
                    compound_name=data["compound_name"],
                    prediction_id=record.get("id")
                )
                break
        else:
            context = retrieve_compound_context(compound_name=data["compound_name"])
    else:
        return jsonify({"error": "Provide features or compound_name"}), 400
    
    suggestions = get_suggested_questions(context)
    return jsonify({
        "compound": context.get("compound_name", "Unknown"),
        "suggestions": suggestions,
        "context_available": bool(context.get("success_probability"))
    })
'''


# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT COMPONENT
# ─────────────────────────────────────────────────────────────────────────────

STREAMLIT_LLM_COMPONENT = '''
# ── ADD TO app.py (after all other sections) ─────────────────────────────────

from llm_analyst import retrieve_compound_context, ask_analyst, get_suggested_questions

st.divider()
st.markdown("### Ask AI Analyst")
st.markdown("*Ask any question about this compound in plain English.*")

# Build context from current sliders
if "analyst_context" not in st.session_state:
    st.session_state.analyst_context = {}

current_context = retrieve_compound_context(
    model=model,
    features=feat_a,
)
current_context["compound_name"] = name_a

# Suggested questions
suggestions = get_suggested_questions(current_context)
selected_q = st.selectbox("Suggested questions", [""] + suggestions)
user_q = st.text_input("Or type your own question", value=selected_q)

col1, col2 = st.columns([3, 1])
with col1:
    ask_button = st.button("Ask analyst ↗", type="primary")
with col2:
    stream_checkbox = st.checkbox("Stream response")

if ask_button and user_q:
    with st.spinner("Analysing compound..."):
        result = ask_analyst(user_q, current_context, stream=stream_checkbox)
    
    if result.get("answer"):
        st.markdown("**Answer:**")
        st.info(result["answer"])
        if result.get("tokens"):
            st.caption(f"Generated by {result['model']} · {result['tokens']} tokens")
    elif result.get("error"):
        st.error(f"Error: {result['error']}")
        
        # Show setup help
        if result["error"] == "anthropic_not_installed":
            st.code("pip install anthropic")
        elif result["error"] == "api_key_missing":
            st.code("Add ANTHROPIC_API_KEY to your .env file")
'''


# ─────────────────────────────────────────────────────────────────────────────
# CLI INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NovaCura LLM Analyst")
    parser.add_argument("--test", action="store_true", help="Test LLM integration")
    parser.add_argument("--question", type=str, help="Ask a question")
    parser.add_argument("--compound", type=str, help="Compound name")
    parser.add_argument("--features", type=str, help="Features as comma-separated values")
    
    args = parser.parse_args()
    
    if args.test:
        print("LLM Analyst Test")
        print("=" * 40)
        print(f"Anthropic available: {ANTHROPIC_AVAILABLE}")
        
        if ANTHROPIC_AVAILABLE:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            print(f"API key configured: {'Yes' if api_key else 'No'}")
            
            # Test with sample context
            test_context = {
                "compound_name": "Test Compound",
                "success_probability": 0.75,
                "verdict": {"verdict": "PASS"},
                "features": {
                    "toxicity": 0.3, "bioavailability": 0.7,
                    "solubility": 0.6, "binding": 0.8,
                    "molecular_weight": 0.5
                },
                "warnings": ["High toxicity risk"]
            }
            
            test_question = "Why did this compound pass?"
            result = ask_analyst(test_question, test_context)
            
            if result.get("answer"):
                print(f"✅ Test successful")
                print(f"Question: {test_question}")
                print(f"Answer: {result['answer'][:200]}...")
            else:
                print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
        else:
            print("❌ Anthropic SDK not available")
            print("Install with: pip install anthropic")
    
    elif args.question and (args.compound or args.features):
        context = {}
        if args.features:
            try:
                features = [float(x.strip()) for x in args.features.split(",")]
                if len(features) == 5:
                    import models
                    context = retrieve_compound_context(features=features, model=models.load_model())
                else:
                    print("Error: Need exactly 5 features")
                    exit(1)
            except ValueError:
                print("Error: Invalid feature values")
                exit(1)
        else:
            context = retrieve_compound_context(compound_name=args.compound)
        
        result = ask_analyst(args.question, context)
        
        print(f"Question: {args.question}")
        print(f"Compound: {context.get('compound_name', 'Unknown')}")
        print(f"Answer: {result.get('answer', result.get('error', 'No answer'))}")
        
        if result.get("error"):
            print(f"Error: {result['error']}")
    
    else:
        parser.print_help()
