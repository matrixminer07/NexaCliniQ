import numpy as np
from typing import Generator

DISCOUNT_RATE = 0.10
BUDGET_KEYS = ("ai", "clinical", "ma", "ops", "reg")
TARGET_BUDGET_M = 500.0

# Revenue multipliers per strategy per year [Y1..Y5]
REVENUE_PROFILES = {
    "ai":          [20, 80, 220, 520, 980],
    "traditional": [30, 70, 140, 260, 420],
    "hybrid":      [25, 75, 180, 390, 680]
}

COST_PER_DRUG = {
    "ai": 820, "traditional": 1800, "hybrid": 1200
}

STRATEGIES = tuple(REVENUE_PROFILES.keys())
_REVENUE_MATRIX = np.array([REVENUE_PROFILES[s] for s in STRATEGIES], dtype=float)
# t = 0..5 where t=0 is initial investment
_DISCOUNT_FACTORS = np.array([1.0 / ((1.0 + DISCOUNT_RATE) ** t) for t in range(6)], dtype=float)


def _normalize_budget(budget: dict) -> dict:
    if not isinstance(budget, dict):
        raise ValueError("Budget payload must be an object with ai/clinical/ma/ops/reg values")

    normalized = {}
    for key in BUDGET_KEYS:
        value = budget.get(key, 0)
        try:
            normalized[key] = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"Budget field '{key}' must be numeric")
        if normalized[key] < 0:
            raise ValueError(f"Budget field '{key}' cannot be negative")
    return normalized

def compute_npv(budget: dict) -> dict:
    """
    budget: {ai, clinical, ma, ops, reg} — values in $M
    Returns NPV, IRR, payback year, break-even, revenue projections
    for all three strategies simultaneously.
    """
    clean_budget = _normalize_budget(budget)
    total = float(sum(clean_budget[k] for k in BUDGET_KEYS))

    # Build cash flow matrix for all strategies at once: [initial_cost, y1..y5]
    initial = np.full((len(STRATEGIES), 1), -total, dtype=float)
    cash_flow_matrix = np.hstack((initial, _REVENUE_MATRIX))
    npv_values = cash_flow_matrix @ _DISCOUNT_FACTORS

    results = {}
    for idx, strategy in enumerate(STRATEGIES):
        revenues = REVENUE_PROFILES[strategy]
        cash_flows = cash_flow_matrix[idx].tolist()
        npv = float(npv_values[idx])
        irr = _estimate_irr(cash_flows)
        payback = _payback_year(cash_flows)
        results[strategy] = {
            "npv": round(npv, 1),
            "irr": round(irr * 100, 1),
            "payback_year": round(payback, 1),
            "revenues": revenues,
            "cost_per_drug": COST_PER_DRUG[strategy],
            "capital_efficiency": round(npv / total, 2) if total > 0 else 0.0,
        }

    results["total_allocated"] = round(total, 1)
    results["budget_status"] = (
        "on_budget" if abs(total - TARGET_BUDGET_M) < 5
        else "over" if total > TARGET_BUDGET_M else "under"
    )
    results["budget_breakdown"] = clean_budget
    return results

def run_monte_carlo(
    params: dict, 
    n_scenarios: int = 5000, 
    batches: int = 10
) -> Generator:
    """
    Yields batches of scenario NPV results for streaming.
    Varies: success rate, pricing, trial costs, timeline.
    """
    batch_size = n_scenarios // batches
    all_npvs = []
    base_revenue = np.array(REVENUE_PROFILES["ai"])
    
    for i in range(batches):
        # Sample uncertainty around base assumptions
        revenue_mult = np.random.normal(1.0, 0.25, (batch_size, 5))
        cost_mult    = np.random.normal(1.0, 0.15, batch_size)
        pos_mult     = np.random.normal(1.0, 0.30, batch_size)
        
        batch_npvs = []
        for j in range(batch_size):
            revenues = base_revenue * revenue_mult[j] * pos_mult[j]
            cost = 500 * cost_mult[j]
            cash_flows = [-cost] + revenues.tolist()
            npv = sum(cf / (1 + DISCOUNT_RATE)**t 
                      for t, cf in enumerate(cash_flows))
            batch_npvs.append(npv)
        
        all_npvs.extend(batch_npvs)
        yield {
            "batch": i + 1,
            "scenarios_complete": len(all_npvs),
            "histogram": np.histogram(
                all_npvs, bins=20, range=(-200, 3000)
            )[0].tolist(),
            "bin_edges": np.histogram(
                all_npvs, bins=20, range=(-200, 3000)
            )[1].tolist(),
            "p10": round(float(np.percentile(all_npvs, 10)), 1),
            "p50": round(float(np.percentile(all_npvs, 50)), 1),
            "p90": round(float(np.percentile(all_npvs, 90)), 1),
            "sharpe": round(
                float(np.mean(all_npvs)) / 
                max(float(np.std(all_npvs)), 1), 2
            )
        }

def _estimate_irr(cash_flows: list,
                  guess: float = 0.1,
                  iterations: int = 60) -> float:
    rate = guess
    arr = np.asarray(cash_flows, dtype=float)
    periods = np.arange(len(arr), dtype=float)
    for _ in range(iterations):
        denom = (1.0 + rate) ** periods
        npv = float(np.sum(arr / denom))
        d_npv = float(np.sum(-periods * arr / ((1.0 + rate) ** (periods + 1.0))))
        if abs(d_npv) < 1e-10:
            break

        next_rate = rate - npv / d_npv
        if abs(next_rate - rate) < 1e-7:
            rate = next_rate
            break
        rate = next_rate
    return max(min(rate, 2.0), -0.99)

def _payback_year(cash_flows: list) -> float:
    cumulative = 0.0
    for t, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0:
            prev_cumulative = cumulative - cf
            if t == 0 or cf == 0:
                return float(t)
            # Linear interpolation for fractional payback within the year.
            frac = (0.0 - prev_cumulative) / cf
            return float(max(0.0, (t - 1) + frac))
    return float(len(cash_flows))
