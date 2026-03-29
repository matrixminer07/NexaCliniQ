"""
UPGRADE 2: SMILES → Descriptor Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Accepts a raw SMILES string and auto-computes all model features using RDKit.
Users no longer need to manually enter molecular properties.

What this does:
  1. Parse SMILES string to RDKit molecule
  2. Compute all 5 model features (MW, LogP, TPSA → toxicity/bio/sol/binding/mw)
  3. Compute extended ADMET descriptors (hERG, BBB, Lipinski, Veber rules)
  4. Validate molecule (sanitise, check drug-likeness)
  5. Expose as /predict-smiles endpoint on the Flask API

Install:  pip install rdkit-pypi  (or conda install -c conda-forge rdkit)
"""

import numpy as np
from typing import Optional

# ── Try importing RDKit ───────────────────────────────────────────────────────
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors, Crippen, Lipinski, QED
    from rdkit.Chem import AllChem, Draw
    from rdkit.Chem.rdMolDescriptors import CalcTPSA
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    print("Warning: RDKit not installed. Install with: pip install rdkit-pypi")
    print("Falling back to SMILES-based approximations.")


# ─────────────────────────────────────────────────────────────────────────────
# CORE DESCRIPTOR COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

def smiles_to_descriptors(smiles: str) -> dict:
    """
    Convert a SMILES string to full descriptor set.
    Returns both raw physicochemical values and normalised 0-1 model features.

    Args:
        smiles: SMILES string (e.g. "CC(=O)Oc1ccccc1C(=O)O" for aspirin)

    Returns:
        dict with:
          - model_features: {toxicity, bioavailability, solubility, binding, molecular_weight}
          - raw_descriptors: {mw, logp, tpsa, hbd, hba, rotbonds, rings, qed, ...}
          - drug_likeness: {lipinski_pass, veber_pass, ghose_pass, ro3_pass}
          - admet: {herg_risk, bbb_penetration, pgp_substrate, ...}
          - validity: {valid, error_message}
    """
    if RDKIT_AVAILABLE:
        return _rdkit_descriptors(smiles)
    else:
        return _approximate_descriptors(smiles)


def _rdkit_descriptors(smiles: str) -> dict:
    """Full RDKit-powered descriptor computation."""

    # ── Validate and parse ────────────────────────────────────────────────────
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {
            "validity": {"valid": False, "error_message": f"Invalid SMILES: {smiles}"},
            "model_features": None,
        }

    # Sanitise
    try:
        Chem.SanitizeMol(mol)
    except Exception as e:
        return {"validity": {"valid": False, "error_message": str(e)}, "model_features": None}

    # ── Raw physicochemical descriptors ──────────────────────────────────────
    mw       = Descriptors.MolWt(mol)
    logp     = Crippen.MolLogP(mol)
    tpsa     = CalcTPSA(mol)
    hbd      = Lipinski.NumHDonors(mol)
    hba      = Lipinski.NumHAcceptors(mol)
    rotbonds = rdMolDescriptors.CalcNumRotatableBonds(mol)
    arom_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
    rings    = rdMolDescriptors.CalcNumRings(mol)
    fsp3     = rdMolDescriptors.CalcFractionCSP3(mol)
    mw_exact = Descriptors.ExactMolWt(mol)

    # QED: drug-likeness score 0-1 (Quantitative Estimate of Drug-likeness)
    try:
        qed_score = QED.qed(mol)
    except Exception:
        qed_score = 0.5

    # Formal charge
    charge = sum(atom.GetFormalCharge() for atom in mol.GetAtoms())

    # Heavy atom count
    n_atoms = mol.GetNumHeavyAtoms()

    # ── Normalised model features (0-1 scale) ─────────────────────────────────

    # Molecular weight: 150-900 Da range
    mol_wt_norm = float(np.clip((mw - 150) / 750, 0, 1))

    # Binding affinity proxy: estimated from aromatic rings + HBA (pharmacophore richness)
    # Higher aromatic + moderate HBA = stronger binding potential
    binding_raw = (
        min(arom_rings / 4, 1) * 0.40 +
        min(hba / 8, 1)        * 0.30 +
        min(fsp3, 1)           * 0.15 +
        (1 - min(charge**2 / 4, 1)) * 0.15
    )
    binding_norm = float(np.clip(binding_raw, 0, 1))

    # Bioavailability: penalise rule-of-5 violations, high TPSA, many rot bonds
    bio_raw = (
        (1 - min(max(mw - 500, 0) / 400, 1))   * 0.35 +
        (1 - min(max(logp - 5, 0) / 3, 1))     * 0.25 +
        (1 - min(tpsa / 200, 1))                * 0.25 +
        (1 - min(rotbonds / 15, 1))             * 0.15
    )
    bioavail_norm = float(np.clip(bio_raw, 0, 1))

    # Solubility: high LogP and high MW reduce aqueous solubility
    sol_raw = (
        (1 - min(max(logp, 0) / 6, 1)) * 0.55 +
        (1 - mol_wt_norm)              * 0.30 +
        min(fsp3, 1)                   * 0.15
    )
    solubility_norm = float(np.clip(sol_raw, 0, 1))

    # Toxicity: high LogP + high MW + reactive groups = elevated risk
    tox_raw = (
        min(max(logp, 0) / 6, 1)  * 0.40 +
        mol_wt_norm                * 0.25 +
        min(max(hbd - 3, 0) / 5, 1) * 0.20 +
        min(max(charge**2 - 1, 0) / 3, 1) * 0.15
    )
    toxicity_norm = float(np.clip(tox_raw, 0, 1))

    model_features = {
        "toxicity":          round(toxicity_norm, 4),
        "bioavailability":   round(bioavail_norm, 4),
        "solubility":        round(solubility_norm, 4),
        "binding":           round(binding_norm, 4),
        "molecular_weight":  round(mol_wt_norm, 4),
    }

    # ── Drug-likeness rules ───────────────────────────────────────────────────
    lipinski  = mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10
    veber     = rotbonds <= 10 and tpsa <= 140
    ghose     = 160 <= mw <= 480 and -0.4 <= logp <= 5.6 and 20 <= n_atoms <= 70
    ro3       = mw <= 300 and logp <= 3 and hbd <= 3 and hba <= 3

    # ── ADMET flags ───────────────────────────────────────────────────────────
    # hERG: high MW + high LogP = cardiac channel inhibition risk
    herg_risk = mw > 400 and logp > 3.5 and arom_rings >= 2

    # BBB: MW < 450 + LogP 1-3 + TPSA < 90 = CNS penetration likely
    bbb_penetration = mw < 450 and 1.0 <= logp <= 3.5 and tpsa < 90 and hbd <= 3

    # P-gp substrate: high MW + multiple aromatic rings
    pgp_substrate = mw > 400 and arom_rings >= 2 and rotbonds >= 5

    # CYP3A4 inhibitor: aromatic + nitrogen-containing
    mol_formula = rdMolDescriptors.CalcMolFormula(mol)
    has_nitrogen = "N" in mol_formula
    cyp_risk = arom_rings >= 2 and has_nitrogen and logp > 2

    admet = {
        "herg_risk":         herg_risk,
        "bbb_penetration":   bbb_penetration,
        "pgp_substrate":     pgp_substrate,
        "cyp3a4_risk":       cyp_risk,
        "lipinski_pass":     lipinski,
        "veber_pass":        veber,
        "reactive_groups":   _check_reactive_groups(mol),
    }

    # ── Warnings ─────────────────────────────────────────────────────────────
    warnings = []
    if not lipinski:
        violations = []
        if mw > 500:    violations.append(f"MW {mw:.0f} > 500")
        if logp > 5:    violations.append(f"LogP {logp:.1f} > 5")
        if hbd > 5:     violations.append(f"HBD {hbd} > 5")
        if hba > 10:    violations.append(f"HBA {hba} > 10")
        warnings.append(f"Lipinski violation: {', '.join(violations)}")
    if herg_risk:
        warnings.append("hERG cardiac channel inhibition risk")
    if not veber:
        warnings.append("Veber rule violation: poor oral bioavailability expected")
    if cyp_risk:
        warnings.append("CYP3A4 inhibition risk — potential drug-drug interactions")
    if admet["reactive_groups"]:
        warnings.append(f"Reactive groups detected: {', '.join(admet['reactive_groups'])}")
    if tpsa > 140:
        warnings.append(f"High TPSA ({tpsa:.0f} Å²) — poor oral absorption expected")

    return {
        "validity": {"valid": True, "error_message": None},
        "smiles":   smiles,
        "model_features": model_features,
        "raw_descriptors": {
            "mw":           round(mw, 2),
            "mw_exact":     round(mw_exact, 4),
            "logp":         round(logp, 3),
            "tpsa":         round(tpsa, 1),
            "hbd":          int(hbd),
            "hba":          int(hba),
            "rotbonds":     int(rotbonds),
            "rings":        int(rings),
            "arom_rings":   int(arom_rings),
            "n_heavy_atoms":int(n_atoms),
            "fsp3":         round(fsp3, 3),
            "qed":          round(qed_score, 3),
            "formal_charge":int(charge),
            "formula":      mol_formula,
        },
        "drug_likeness": {
            "lipinski_pass": lipinski,
            "veber_pass":    veber,
            "ghose_pass":    ghose,
            "ro3_pass":      ro3,
            "qed_score":     round(qed_score, 3),
            "overall":       "Excellent" if lipinski and veber and qed_score > 0.7
                            else "Good"  if lipinski and veber
                            else "Poor",
        },
        "admet": admet,
        "warnings": warnings,
    }


def _check_reactive_groups(mol) -> list:
    """Screen for PAINS and reactive functional groups."""
    REACTIVE_SMARTS = {
        "aldehyde":         "[CH]=O",
        "michael_acceptor": "C=CC(=O)",
        "epoxide":          "C1OC1",
        "acyl_halide":      "C(=O)[F,Cl,Br,I]",
        "isocyanate":       "N=C=O",
        "anhydride":        "C(=O)OC(=O)",
        "amine_oxide":      "[N+][O-]",
    }
    found = []
    for name, smarts in REACTIVE_SMARTS.items():
        try:
            pattern = Chem.MolFromSmarts(smarts)
            if pattern and mol.HasSubstructMatch(pattern):
                found.append(name)
        except Exception:
            pass
    return found


def _approximate_descriptors(smiles: str) -> dict:
    """
    Fallback descriptor estimation without RDKit.
    Uses SMILES string heuristics — less accurate but functional.
    """
    if not smiles or len(smiles) < 3:
        return {"validity": {"valid": False, "error_message": "Empty SMILES"}, "model_features": None}

    s = smiles.upper()

    # Rough MW estimate: count heavy atoms
    heavy_atoms = sum(1 for c in smiles if c.isalpha() and c.upper() not in ['H'])
    mw_est = heavy_atoms * 14.0

    # Count aromatic rings (lowercase = aromatic in SMILES)
    arom_est = smiles.count('c') / 6

    # Count nitrogen/oxygen (pharmacophore elements)
    n_N = smiles.upper().count('N')
    n_O = smiles.upper().count('O')

    # Heuristic features
    mw_norm   = float(np.clip((mw_est - 150) / 750, 0, 1))
    binding   = float(np.clip(arom_est * 0.2 + n_N * 0.05 + n_O * 0.03, 0, 1))
    bio       = float(np.clip(1 - mw_norm * 0.6, 0, 1))
    sol       = float(np.clip(0.5 + (n_O + n_N) * 0.05 - mw_norm * 0.4, 0, 1))
    tox       = float(np.clip(mw_norm * 0.4, 0, 1))

    return {
        "validity": {"valid": True, "error_message": None, "note": "RDKit not available — approximate values"},
        "smiles": smiles,
        "model_features": {
            "toxicity":        round(tox, 4),
            "bioavailability": round(bio, 4),
            "solubility":      round(sol, 4),
            "binding":         round(binding, 4),
            "molecular_weight": round(mw_norm, 4),
        },
        "raw_descriptors": {"mw_estimate": round(mw_est, 0), "note": "RDKit not installed"},
        "drug_likeness":    {"overall": "Unknown — install RDKit for full analysis"},
        "admet":            {},
        "warnings":         ["RDKit not installed — descriptors are approximate"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# BATCH SMILES PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def batch_smiles_to_features(smiles_list: list) -> list:
    """Process a list of SMILES strings and return feature dicts."""
    return [smiles_to_descriptors(s) for s in smiles_list]


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ENDPOINTS (add to api.py)
# ─────────────────────────────────────────────────────────────────────────────

SMILES_ROUTES = '''
# ── ADD THESE ROUTES TO api.py ───────────────────────────────────────────────

from smiles_pipeline import smiles_to_descriptors, batch_smiles_to_features
import models

@app.route("/predict-smiles", methods=["POST"])
def predict_smiles():
    """
    POST body: {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "compound_name": "Aspirin"}
    Auto-computes all 5 features from SMILES, then runs prediction.
    """
    data   = request.get_json()
    smiles = data.get("smiles", "").strip()
    if not smiles:
        return jsonify({"error": "smiles field required"}), 400

    desc = smiles_to_descriptors(smiles)
    if not desc["validity"]["valid"]:
        return jsonify({"error": desc["validity"]["error_message"]}), 422
    if desc["model_features"] is None:
        return jsonify({"error": "Could not compute features from SMILES"}), 422

    features = [desc["model_features"][k] for k in
                ["toxicity","bioavailability","solubility","binding","molecular_weight"]]

    prob    = models.predict_single(model, features)
    ci      = models.predict_with_confidence(model, features)
    shap_bd = models.get_shap_breakdown(model, features)
    phases  = models.get_phase_probabilities(prob)
    verdict = models.classify_verdict(prob)

    all_warnings = desc["warnings"][:]
    if desc["model_features"]["toxicity"] > 0.7:
        all_warnings.append("High toxicity risk detected")
    if desc["model_features"]["bioavailability"] < 0.4:
        all_warnings.append("Low bioavailability risk")

    return jsonify({
        "compound_name":      data.get("compound_name", "Unknown"),
        "smiles":             smiles,
        "success_probability": round(prob, 4),
        "verdict":            verdict,
        "confidence_interval": ci,
        "shap_breakdown":     shap_bd,
        "phase_probabilities": phases,
        "model_features":     desc["model_features"],
        "raw_descriptors":    desc.get("raw_descriptors", {}),
        "drug_likeness":      desc.get("drug_likeness", {}),
        "admet":              desc.get("admet", {}),
        "warnings":           all_warnings,
    })

@app.route("/descriptors", methods=["POST"])
def compute_descriptors():
    """
    POST body: {"smiles": "..."} or {"smiles_list": [...]}
    Returns full descriptor set without running prediction.
    """
    data = request.get_json()
    if "smiles_list" in data:
        results = batch_smiles_to_features(data["smiles_list"])
        return jsonify({"count": len(results), "results": results})
    smiles = data.get("smiles","")
    return jsonify(smiles_to_descriptors(smiles))
'''


# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT COMPONENT (add to app.py)
# ─────────────────────────────────────────────────────────────────────────────

STREAMLIT_SMILES_COMPONENT = '''
# ── ADD TO app.py sidebar ────────────────────────────────────────────────────

from smiles_pipeline import smiles_to_descriptors

st.sidebar.divider()
st.sidebar.markdown("### SMILES input")
smiles_input = st.sidebar.text_input(
    "Paste SMILES string",
    placeholder="e.g. CC(=O)Oc1ccccc1C(=O)O",
    help="Auto-computes all features from molecular structure"
)

if smiles_input:
    desc = smiles_to_descriptors(smiles_input)
    if desc["validity"]["valid"] and desc["model_features"]:
        st.sidebar.success("Molecule parsed — features auto-filled")
        mf = desc["model_features"]
        # Auto-populate sliders by updating session state
        st.session_state["tox_a"]  = mf["toxicity"]
        st.session_state["bio_a"]  = mf["bioavailability"]
        st.session_state["sol_a"]  = mf["solubility"]
        st.session_state["bind_a"] = mf["binding"]
        st.session_state["mw_a"]   = mf["molecular_weight"]

        if desc.get("raw_descriptors"):
            rd = desc["raw_descriptors"]
            st.sidebar.caption(
                f"MW: {rd.get('mw','N/A')} Da · "
                f"LogP: {rd.get('logp','N/A')} · "
                f"QED: {rd.get('qed','N/A')}"
            )
        for w in desc.get("warnings", []):
            st.sidebar.warning(w)
    else:
        st.sidebar.error(desc["validity"].get("error_message","Invalid SMILES"))
'''


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_molecules = {
        "Aspirin":    "CC(=O)Oc1ccccc1C(=O)O",
        "Ibuprofen":  "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        "Caffeine":   "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
        "Taxol":      "CC1=C2C(C(=O)C3(C(CC4C(C3C(C(=O)C(C(C2(C)C)(CC1OC(=O)c5ccccc5)O)OC(=O)C)O4)(CO)OC(=O)C)OC(=O)c6ccccc6)=O",
        "Invalid":    "NOTASMILES",
    }

    print("SMILES Pipeline Test")
    print("=" * 50)
    for name, smi in test_molecules.items():
        result = smiles_to_descriptors(smi)
        if result["validity"]["valid"] and result["model_features"]:
            mf = result["model_features"]
            dl = result.get("drug_likeness", {})
            print(f"\n{name}:")
            print(f"  Features: tox={mf['toxicity']:.3f} bio={mf['bioavailability']:.3f} "
                  f"sol={mf['solubility']:.3f} bind={mf['binding']:.3f} mw={mf['molecular_weight']:.3f}")
            if result.get("raw_descriptors"):
                rd = result["raw_descriptors"]
                print(f"  Raw:      MW={rd.get('mw','N/A')} LogP={rd.get('logp','N/A')} "
                      f"TPSA={rd.get('tpsa','N/A')} QED={rd.get('qed','N/A')}")
            print(f"  Drug-likeness: {dl.get('overall','N/A')}")
            if result["warnings"]:
                print(f"  Warnings: {result['warnings']}")
        else:
            print(f"\n{name}: INVALID — {result['validity']['error_message']}")
