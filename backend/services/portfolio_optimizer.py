import numpy as np
from itertools import combinations

def optimize_portfolio(compounds: list, budget_m: float = 500.0) -> dict:
    """
    Given a list of compounds with costs and predicted success probabilities,
    find the allocation that maximises expected NPV within budget.

    compounds: list of dicts, each with:
        {
          "id": str,
          "name": str,
          "success_probability": float,   # from /predict
          "development_cost_m": float,    # estimated $M to IND
          "peak_revenue_m": float,        # estimated peak annual revenue if approved
          "time_to_market_yr": float      # years to approval
        }
    """
    DISCOUNT_RATE = 0.10
    PATENT_YEARS  = 12   # revenue years post-approval

    def compound_npv(c):
        prob  = c["success_probability"]
        years = c["time_to_market_yr"]
        # Discounted revenue stream over patent life
        revenue_npv = sum(
            c["peak_revenue_m"] / (1 + DISCOUNT_RATE)**(years + yr)
            for yr in range(PATENT_YEARS)
        )
        return prob * revenue_npv - c["development_cost_m"]

    # Score each compound individually
    scored = []
    for c in compounds:
        npv = compound_npv(c)
        scored.append({**c, "individual_npv": round(npv, 1),
                       "npv_per_dollar": round(npv / max(c["development_cost_m"], 1), 3)})

    # Knapsack: find best combination within budget
    best_combo  = []
    best_npv    = -float("inf")
    n           = len(scored)

    for r in range(1, min(n+1, 7)):  # cap at 6-compound combos for speed
        for combo in combinations(range(n), r):
            total_cost = sum(scored[i]["development_cost_m"] for i in combo)
            if total_cost > budget_m:
                continue
            total_npv = sum(scored[i]["individual_npv"] for i in combo)
            if total_npv > best_npv:
                best_npv   = total_npv
                best_combo = combo

    optimal = [scored[i] for i in best_combo]
    portfolio_pos = 1 - np.prod([1 - c["success_probability"] for c in optimal])

    return {
        "optimal_portfolio": optimal,
        "total_cost_m":      round(sum(c["development_cost_m"] for c in optimal), 1),
        "budget_remaining_m": round(budget_m - sum(c["development_cost_m"] for c in optimal), 1),
        "expected_portfolio_npv_m": round(best_npv, 1),
        "portfolio_success_probability": round(portfolio_pos, 3),
        "all_compounds_scored": sorted(scored, key=lambda x: x["individual_npv"], reverse=True),
        "recommendation": (
            f"Optimal {len(optimal)}-compound portfolio: "
            + ", ".join(c['name'] for c in optimal)
            + f". Expected NPV: ${best_npv:.0f}M at portfolio PoS of {portfolio_pos*100:.1f}%."
        )
    }
