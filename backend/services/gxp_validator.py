PHYSIOLOGICAL_BOUNDS = {
    "toxicity":          (0.0,  1.0,  "Normalised 0-1 scale"),
    "bioavailability":   (0.0,  1.0,  "Normalised 0-1 scale"),
    "solubility":        (0.0,  1.0,  "Normalised 0-1 scale"),
    "binding":           (0.0,  1.0,  "Normalised 0-1 scale"),
    "molecular_weight":  (0.0,  1.0,  "Normalised 0-1 scale (150-900 Da range)")
}

def validate_inputs(data: dict) -> dict:
    errors, warnings_list, passed = [], [], []
    for field, (lo, hi, desc) in PHYSIOLOGICAL_BOUNDS.items():
        if field not in data:
            errors.append({"field": field, "issue": "Missing required field"})
            continue
        val = data[field]
        if not isinstance(val, (int, float)):
            errors.append({"field": field, "issue": f"Must be numeric, got {type(val).__name__}"})
            continue
        if not (lo <= val <= hi):
            errors.append({"field": field, "issue": f"Out of range [{lo},{hi}], got {val}"})
            continue
        # Soft warnings for physiologically implausible combinations
        passed.append(field)

    # Cross-field plausibility
    if "toxicity" in data and "bioavailability" in data:
        if data["toxicity"] > 0.9 and data["bioavailability"] > 0.9:
            warnings_list.append(
                "Extreme toxicity and bioavailability simultaneously is physiologically unusual - verify inputs"
            )

    return {
        "valid":          len(errors) == 0,
        "errors":         errors,
        "warnings":       warnings_list,
        "fields_checked": len(PHYSIOLOGICAL_BOUNDS),
        "fields_passed":  len(passed),
        "gxp_compliant":  len(errors) == 0
    }
