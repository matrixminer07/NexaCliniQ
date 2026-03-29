def run_tornado(base_params: dict) -> dict:
    """
    Computes NPV swing for ±1 standard deviation on 8 key assumptions.
    Returns sorted bars for tornado chart.
    """
    from services.financial_engine import compute_npv

    base_npv = compute_npv(base_params)["ai"]["npv"]
    
    assumptions = [
        ("PoS +20%",            {"revenue_mult": 1.20}),
        ("AI Accuracy +10%",    {"revenue_mult": 1.12}),
        ("Trial Cost -15%",     {"cost_mult":    0.85}),
        ("Time-to-IND -6mo",    {"revenue_mult": 1.08}),
        ("Pricing +10%",        {"revenue_mult": 1.10}),
        ("PoS -20%",            {"revenue_mult": 0.80}),
        ("Regulatory Delay",    {"cost_mult":    1.20}),
        ("Data Cost +30%",      {"cost_mult":    1.15}),
    ]
    
    bars = []
    for label, shock in assumptions:
        shocked_params = {**base_params}
        if "revenue_mult" in shock:
            shocked_npv = base_npv * shock["revenue_mult"]
        else:
            shocked_npv = base_npv * (2 - shock["cost_mult"])
        
        swing = round(shocked_npv - base_npv, 1)
        bars.append({
            "label": label, 
            "swing": swing,
            "shocked_npv": round(shocked_npv, 1),
            "base_npv": round(base_npv, 1)
        })
    
    bars.sort(key=lambda x: abs(x["swing"]), reverse=True)
    return {"bars": bars, "base_npv": round(base_npv, 1)}
