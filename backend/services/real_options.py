import numpy as np
from scipy.stats import norm

def black_scholes_call(S, K, T, r, sigma):
    """Standard BSM call option formula."""
    if T <= 0 or sigma <= 0:
        return max(S - K, 0)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)

def value_pharma_real_options(compound: dict) -> dict:
    """
    Value three real options embedded in a drug development program:
    1. Option to expand (scale up on Phase 2 success)
    2. Option to abandon (sell/out-license on failure)
    3. Option to delay (wait for better data before Phase 3 commit)

    compound: {
        "name": str,
        "base_npv_m": float,          # DCF NPV if approved
        "development_cost_m": float,   # remaining investment needed
        "time_to_decision_yr": float,  # years until next go/no-go
        "volatility": float,           # 0.3-0.6 typical for pharma
        "salvage_value_m": float       # out-license value on failure
    }
    """
    r       = 0.10
    S       = compound["base_npv_m"]
    K       = compound["development_cost_m"]
    T       = compound["time_to_decision_yr"]
    sigma   = compound.get("volatility", 0.40)
    salvage = compound.get("salvage_value_m", 0)

    expand_value  = black_scholes_call(S, K, T, r, sigma)
    abandon_value = salvage * np.exp(-r * T)
    delay_value   = black_scholes_call(S * 0.92, K, T + 1, r, sigma)  # cost of waiting

    strategic_premium = expand_value + abandon_value - max(S - K, 0)

    return {
        "compound": compound["name"],
        "dcf_base_npv_m":        round(max(S - K, 0), 1),
        "expand_option_value_m": round(expand_value, 1),
        "abandon_option_value_m": round(abandon_value, 1),
        "delay_option_value_m":   round(delay_value, 1),
        "strategic_premium_m":    round(strategic_premium, 1),
        "total_strategic_value_m": round(max(S-K,0) + strategic_premium, 1),
        "premium_pct": round(strategic_premium / max(K, 1) * 100, 1),
        "recommendation": (
            "Expand" if expand_value > delay_value and expand_value > salvage
            else "Delay" if delay_value > expand_value
            else "Abandon/out-license"
        )
    }
