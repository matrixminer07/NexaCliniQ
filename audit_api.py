"""Comprehensive API audit for NovaCura backend.

Starts app.py in a subprocess, probes all primary endpoints, validates status and
expected top-level JSON keys, reports PASS/FAIL with response time, and exits 1
if any check fails.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests

from backend.db_pg import execute as pg_execute


@dataclass
class CheckResult:
    name: str
    ok: bool
    status_code: int
    elapsed_ms: float
    detail: str


def unwrap_payload(body: Any) -> Any:
    if isinstance(body, dict) and "data" in body and body.get("data") is not None:
        return body["data"]
    return body


def request_json(
    base: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | list[Any] | None = None,
    timeout: int = 15,
) -> tuple[int, Any, float]:
    url = f"{base}{path}"
    started = time.perf_counter()
    response = requests.request(method=method, url=url, json=payload, timeout=timeout)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    return response.status_code, body, elapsed_ms


def expect_keys(payload: Any, keys: list[str]) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "response is not an object"
    missing = [k for k in keys if k not in payload]
    return (len(missing) == 0, f"missing keys: {missing}" if missing else "ok")


def run_check(
    name: str,
    base: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | list[Any] | None = None,
    expected_status: set[int] | None = None,
    required_keys: list[str] | None = None,
) -> CheckResult:
    expected = expected_status or {200}
    try:
        code, body, elapsed = request_json(base, path, method=method, payload=payload)
        ok = code in expected
        detail = "status ok"
        unwrapped = unwrap_payload(body)
        if ok and required_keys:
            ok, key_detail = expect_keys(unwrapped, required_keys)
            detail = key_detail
        return CheckResult(name=name, ok=ok, status_code=code, elapsed_ms=elapsed, detail=detail)
    except requests.RequestException as exc:
        return CheckResult(name=name, ok=False, status_code=0, elapsed_ms=0.0, detail=str(exc))


def wait_for_health(base: str, timeout_s: int = 40) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            code, body, _ = request_json(base, "/health")
            data = unwrap_payload(body)
            if code == 200 and isinstance(data, dict) and data.get("status") == "healthy":
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError("API did not become healthy within timeout")


def seed_active_learning_row(workspace: str) -> str:
    qid = f"audit-{int(time.time())}"
    pg_execute(
        (
            "INSERT INTO active_learning_queue (id, compound_name, features, uncertainty_score, predicted_prob, priority, status) "
            "VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET features=EXCLUDED.features, predicted_prob=EXCLUDED.predicted_prob, status='pending'"
        ),
        [qid, "AuditCandidate", json.dumps({"toxicity": 0.3}), 0.8, 0.42, "high", "pending"],
    )
    return qid


def run_full_audit(base: str, workspace: str) -> list[CheckResult]:
    features = {
        "compound_name": "AuditCompound",
        "toxicity": 0.30,
        "bioavailability": 0.70,
        "solubility": 0.60,
        "binding": 0.80,
        "molecular_weight": 0.50,
    }
    features_list = {"compound_name": "AuditList", "features": [0.3, 0.7, 0.6, 0.8, 0.5]}

    results: list[CheckResult] = []
    results.append(run_check("GET /health", base, "/health", required_keys=["status"], expected_status={200}))
    results.append(run_check("GET /model/info", base, "/model/info", required_keys=["model_version", "training_date", "n_samples", "feature_names", "auc"], expected_status={200}))

    pred = run_check("POST /predict", base, "/predict", method="POST", payload=features, required_keys=["success_probability", "verdict", "shap_breakdown", "admet", "phase_probabilities"])
    results.append(pred)
    results.append(run_check("POST /predict (list-form)", base, "/predict", method="POST", payload=features_list, expected_status={200}))

    results.append(run_check("POST /predict-batch", base, "/predict-batch", method="POST", payload=[features, {**features, "compound_name": "AuditB", "binding": 0.6}], required_keys=["count", "results", "summary"]))
    results.append(run_check("POST /predict-ensemble", base, "/predict-ensemble", method="POST", payload=features, required_keys=["ensemble_probability", "model_breakdown", "confidence_band"]))
    results.append(run_check("POST /predict-smiles", base, "/predict-smiles", method="POST", payload={"smiles": "CCO", "compound_name": "AuditSMILES"}, required_keys=["success_probability", "model_features", "warnings"]))
    results.append(run_check("POST /predict-ta", base, "/predict-ta", method="POST", payload={**features, "therapeutic_area": "oncology", "compare_all": True}, required_keys=["all_ta_results", "best_indication", "worst_indication"]))
    results.append(run_check("POST /counterfactual", base, "/counterfactual", method="POST", payload={**features, "target_probability": 0.75}, expected_status={200}, required_keys=[]))
    results.append(run_check("POST /shap", base, "/shap", method="POST", payload=features, required_keys=["contributions", "top_driver"]))
    results.append(run_check("POST /admet", base, "/admet", method="POST", payload=features, required_keys=["mw_daltons", "drug_likeness", "lipinski_pass"]))
    results.append(run_check("GET /history", base, "/history", expected_status={200}))
    results.append(run_check("GET /stats", base, "/stats", required_keys=["total_predictions", "pass_rate", "verdict_breakdown"]))

    create_scenario = run_check("POST /scenarios", base, "/scenarios", method="POST", payload={"name": "Audit Scenario", "inputs": features, "outputs": {"x": 1}, "tags": ["audit"]}, expected_status={201})
    results.append(create_scenario)
    results.append(run_check("GET /scenarios", base, "/scenarios", expected_status={200}))

    # Pull created id to exercise delete and compound update routes.
    scenario_id = None
    try:
        code, body, _ = request_json(base, "/scenarios")
        if code == 200 and isinstance(body, list) and body:
            scenario_id = body[0].get("id")
    except requests.RequestException:
        scenario_id = None

    if scenario_id:
        results.append(run_check("DELETE /scenarios/<id>", base, f"/scenarios/{scenario_id}", method="DELETE", expected_status={200}))
    else:
        results.append(CheckResult("DELETE /scenarios/<id>", False, 0, 0.0, "no scenario id available"))

    compounds_payload = {
        "budget_m": 500,
        "compounds": [
            {"id": "cmp-a", "toxicity": 0.2, "bioavailability": 0.8, "solubility": 0.7, "binding": 0.85, "molecular_weight": 0.4},
            {"id": "cmp-b", "features": [0.4, 0.7, 0.6, 0.75, 0.5]},
        ],
    }
    results.append(run_check("POST /optimize-portfolio", base, "/optimize-portfolio", method="POST", payload=compounds_payload, expected_status={200}))
    results.append(run_check("POST /financial/npv", base, "/financial/npv", method="POST", payload={"ai": 180, "clinical": 150, "ma": 90}, expected_status={200}))
    results.append(run_check("POST /financial/sensitivity", base, "/financial/sensitivity", method="POST", payload={"base_case": 1000}, expected_status={200}))

    # PDF endpoint returns binary; validate status only.
    try:
        started = time.perf_counter()
        pdf_resp = requests.post(f"{base}/export/pdf", json={"summary": "audit"}, timeout=20)
        elapsed = (time.perf_counter() - started) * 1000.0
        results.append(CheckResult("POST /export/pdf", pdf_resp.status_code == 200, pdf_resp.status_code, elapsed, "status ok"))
    except requests.RequestException as exc:
        results.append(CheckResult("POST /export/pdf", False, 0, 0.0, str(exc)))

    results.append(run_check("GET /transparency-report", base, "/transparency-report", expected_status={200}))
    results.append(run_check("GET /model/cv-report", base, "/model/cv-report", expected_status={200}))
    results.append(run_check("GET /therapeutic-areas", base, "/therapeutic-areas", required_keys=["oncology", "cns", "rare", "cardiology", "infectious", "metabolic"]))
    results.append(run_check("GET /theraputic-areas", base, "/theraputic-areas", expected_status={200}))

    results.append(run_check("POST /analyst/ask", base, "/analyst/ask", method="POST", payload={**features, "question": "Summarize strengths"}, expected_status={200}, required_keys=["answer"]))
    results.append(run_check("POST /analyst/suggestions", base, "/analyst/suggestions", method="POST", payload=features, required_keys=["suggestions"]))

    results.append(run_check("GET /active-learning/queue", base, "/active-learning/queue", expected_status={200}))
    results.append(run_check("GET /active-learning/stats", base, "/active-learning/stats", expected_status={200}))
    qid = seed_active_learning_row(workspace)
    results.append(run_check("POST /active-learning/label/<id>", base, f"/active-learning/label/{qid}", method="POST", payload={"true_label": 1, "labelled_by": "audit"}, expected_status={200}))

    # Resolve latest compound id for detail/tag/note endpoints.
    compound_id = None
    try:
        code, body, _ = request_json(base, "/history")
        history_payload = unwrap_payload(body)
        if code == 200 and isinstance(history_payload, list) and history_payload:
            compound_id = history_payload[0].get("id")
    except requests.RequestException:
        compound_id = None

    if compound_id:
        results.append(run_check("GET /compound/<id>", base, f"/compound/{compound_id}", expected_status={200}))
        results.append(run_check("POST /compounds/<id>/tags", base, f"/compounds/{compound_id}/tags", method="POST", payload={"tags": ["priority", "audit"]}, expected_status={200}))
        results.append(run_check("POST /compounds/<id>/notes", base, f"/compounds/{compound_id}/notes", method="POST", payload={"note": "Audit note"}, expected_status={200}))
    else:
        results.append(CheckResult("GET /compound/<id>", False, 0, 0.0, "no compound id available"))
        results.append(CheckResult("POST /compounds/<id>/tags", False, 0, 0.0, "no compound id available"))
        results.append(CheckResult("POST /compounds/<id>/notes", False, 0, 0.0, "no compound id available"))

    # OPTIONS preflight spot checks.
    for path in ["/predict", "/analyst/ask", "/history"]:
        results.append(run_check(f"OPTIONS {path}", base, path, method="OPTIONS", expected_status={200, 204}))

    return results


def start_backend(workspace: str) -> subprocess.Popen[str]:
    cmd = [sys.executable, os.path.join(workspace, "app.py")]
    proc = subprocess.Popen(
        cmd,
        cwd=workspace,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    time.sleep(1.0)
    if proc.poll() is not None:
        raise RuntimeError("Failed to start backend subprocess (port in use or startup error)")
    return proc


def stop_backend(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[arg-type]
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def print_results(results: list[CheckResult]) -> int:
    failures = 0
    for item in results:
        status_text = "PASS" if item.ok else "FAIL"
        print(f"[{status_text}] {item.name:34s} | status={item.status_code:>3} | {item.elapsed_ms:7.1f} ms | {item.detail}")
        if not item.ok:
            failures += 1
    print(f"\nTotal checks: {len(results)} | Failures: {failures}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit NovaCura API endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Backend base URL")
    parser.add_argument("--workspace", default=os.path.dirname(os.path.abspath(__file__)), help="Workspace path containing app.py")
    parser.add_argument("--quick", action="store_true", help="Quick health-only mode")
    parser.add_argument("--no-spawn", action="store_true", help="Do not spawn app.py subprocess")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    proc: subprocess.Popen[str] | None = None

    try:
        if not args.no_spawn:
            proc = start_backend(args.workspace)
        wait_for_health(base)

        if args.quick:
            quick = [run_check("GET /health", base, "/health", required_keys=["status"], expected_status={200})]
            return print_results(quick)

        results = run_full_audit(base, args.workspace)
        return print_results(results)
    finally:
        if proc is not None:
            stop_backend(proc)


if __name__ == "__main__":
    sys.exit(main())
