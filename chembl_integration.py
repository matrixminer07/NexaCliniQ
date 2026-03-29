"""
UPGRADE 1: ChEMBL API Integration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Replaces 600 synthetic training samples with real published bioactivity records.
Uses ChEMBL REST API (no API key required — publicly accessible).

What this does:
  1. Fetch bioactivity data for any target (ChEMBL ID or gene name)
  2. Parse IC50 / Ki / Kd / EC50 values into normalised features
  3. Label compounds as success (active) or failure (inactive)
  4. Retrain Random Forest on real data
  5. Cache results locally so repeated runs don't re-fetch

Usage:
  python chembl_integration.py --target CHEMBL205          # single target
  python chembl_integration.py --gene EGFR                 # by gene name
  python chembl_integration.py --targets CHEMBL205,CHEMBL203,CHEMBL240  # multi-target
"""

import requests
import numpy as np
import pandas as pd
import joblib
import json
import os
import time
import argparse
from datetime import datetime
from typing import Optional

CHEMBL_BASE   = "https://www.ebi.ac.uk/chembl/api/data"
CACHE_DIR     = "chembl_cache"
MODEL_PATH    = "model.joblib"
DATASET_PATH  = "chembl_dataset.csv"
os.makedirs(CACHE_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: FETCH BIOACTIVITY DATA FROM CHEMBL
# ─────────────────────────────────────────────────────────────────────────────

def fetch_target_id(gene_name: str) -> Optional[str]:
    """Resolve a gene name (e.g. 'EGFR') to a ChEMBL target ID."""
    url = f"{CHEMBL_BASE}/target/search.json"
    r   = requests.get(url, params={"q": gene_name, "limit": 5}, timeout=15)
    r.raise_for_status()
    targets = r.json().get("targets", [])
    if not targets:
        raise ValueError(f"No ChEMBL target found for gene: {gene_name}")
    # Prefer single protein targets
    for t in targets:
        if t.get("target_type") == "SINGLE PROTEIN":
            print(f"  Resolved {gene_name} → {t['target_chembl_id']} ({t['pref_name']})")
            return t["target_chembl_id"]
    return targets[0]["target_chembl_id"]


def fetch_bioactivities(target_id: str,
                        activity_types: list = None,
                        max_records: int = 2000) -> list:
    """
    Fetch bioactivity records for a target from ChEMBL.
    Returns list of raw activity dicts.
    """
    cache_file = os.path.join(CACHE_DIR, f"{target_id}.json")
    if os.path.exists(cache_file):
        print(f"  Using cached data for {target_id}")
        with open(cache_file) as f:
            return json.load(f)

    if activity_types is None:
        activity_types = ["IC50", "Ki", "Kd", "EC50"]

    all_records = []
    for act_type in activity_types:
        offset = 0
        while len(all_records) < max_records:
            url    = f"{CHEMBL_BASE}/activity.json"
            params = {
                "target_chembl_id": target_id,
                "standard_type":    act_type,
                "standard_units":   "nM",
                "limit":            200,
                "offset":           offset,
            }
            try:
                r = requests.get(url, params=params, timeout=20)
                r.raise_for_status()
                data     = r.json()
                records  = data.get("activities", [])
                if not records:
                    break
                all_records.extend(records)
                offset  += len(records)
                if offset >= data.get("page_meta", {}).get("total_count", 0):
                    break
                time.sleep(0.3)   # respect ChEMBL rate limits
            except requests.RequestException as e:
                print(f"  Warning: fetch failed for {act_type} at offset {offset}: {e}")
                break

    print(f"  Fetched {len(all_records)} raw records for {target_id}")
    with open(cache_file, "w") as f:
        json.dump(all_records, f)
    return all_records


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: PARSE AND NORMALISE FEATURES
# ─────────────────────────────────────────────────────────────────────────────

def parse_activity_records(records: list,
                            active_threshold_nm: float = 1000.0) -> pd.DataFrame:
    """
    Convert raw ChEMBL bioactivity records into a feature DataFrame.

    Features derived:
      - binding:          normalised potency (1 - log10(nM)/9, clipped 0-1)
      - toxicity:         proxy from high MW + high lipophilicity patterns
      - bioavailability:  proxy from MW and polar surface area estimates
      - solubility:       proxy from molecular complexity flags
      - molecular_weight: normalised MW (150-900 Da range → 0-1)
      - label:            1 if active (IC50 < threshold), else 0

    Note: Without RDKit, features are computed from ChEMBL metadata.
    For full ADMET accuracy, pair with Upgrade 2 (SMILES pipeline).
    """
    rows = []
    for rec in records:
        try:
            val   = float(rec.get("standard_value") or 0)
            mw    = float(rec.get("molecule_properties", {}).get("mw_freebase") or 400)
            alogp = float(rec.get("molecule_properties", {}).get("alogp") or 2.0)
            tpsa  = float(rec.get("molecule_properties", {}).get("psa") or 80.0)
            hbd   = float(rec.get("molecule_properties", {}).get("hbd") or 1)
            hba   = float(rec.get("molecule_properties", {}).get("hba") or 3)
            rtb   = float(rec.get("molecule_properties", {}).get("rtb") or 3)
            smiles = rec.get("canonical_smiles", "")
            chembl_mol_id = rec.get("molecule_chembl_id", "")

            if val <= 0:
                continue

            # ── Normalised features ──────────────────────────────────────────

            # Binding: potency score — lower nM = higher binding
            log_val = np.log10(max(val, 0.001))           # log10(nM)
            binding = float(np.clip(1.0 - log_val / 9.0, 0, 1))

            # Molecular weight: normalised 150–900 Da
            mol_wt  = float(np.clip((mw - 150) / 750, 0, 1))

            # Bioavailability proxy: penalise high MW + high TPSA + many rot bonds
            bio_raw = 1.0 - (mw / 900 * 0.4 + tpsa / 200 * 0.4 + rtb / 15 * 0.2)
            bioavailability = float(np.clip(bio_raw, 0, 1))

            # Solubility proxy: high LogP and high MW reduce aqueous solubility
            sol_raw = 1.0 - (max(alogp, 0) / 6.0 * 0.6 + mw / 900 * 0.4)
            solubility = float(np.clip(sol_raw, 0, 1))

            # Toxicity proxy: high LogP + high MW = elevated toxicity risk
            tox_raw = (max(alogp, 0) / 6.0 * 0.5 + mw / 900 * 0.3 +
                       max(hbd - 3, 0) / 5.0 * 0.2)
            toxicity = float(np.clip(tox_raw, 0, 1))

            # Label: active if below threshold nM
            label = int(val < active_threshold_nm)

            rows.append({
                "chembl_mol_id":  chembl_mol_id,
                "smiles":         smiles,
                "activity_nM":    round(val, 2),
                "toxicity":       round(toxicity, 4),
                "bioavailability": round(bioavailability, 4),
                "solubility":     round(solubility, 4),
                "binding":        round(binding, 4),
                "molecular_weight": round(mol_wt, 4),
                "mw_daltons":     round(mw, 1),
                "alogp":          round(alogp, 2),
                "tpsa":           round(tpsa, 1),
                "label":          label,
                "source":         "ChEMBL",
                "activity_type":  rec.get("standard_type", ""),
            })
        except (TypeError, ValueError, KeyError):
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Remove duplicates: keep highest-potency record per molecule
    df = df.sort_values("activity_nM").drop_duplicates("chembl_mol_id", keep="first")
    print(f"  Parsed {len(df)} unique compounds "
          f"({df['label'].sum()} active, {(1-df['label']).sum()} inactive)")
    return df


def load_or_fetch_dataset(target_ids: list,
                           max_per_target: int = 1500) -> pd.DataFrame:
    """
    Load dataset from CSV cache, or fetch fresh from ChEMBL.
    Multiple targets are combined and deduplicated.
    """
    if os.path.exists(DATASET_PATH):
        df = pd.read_csv(DATASET_PATH)
        print(f"Loaded cached dataset: {len(df)} compounds from {DATASET_PATH}")
        return df

    all_dfs = []
    for tid in target_ids:
        print(f"\nFetching ChEMBL data for target: {tid}")
        records = fetch_bioactivities(tid, max_records=max_per_target)
        df_t    = parse_activity_records(records)
        if not df_t.empty:
            df_t["target_id"] = tid
            all_dfs.append(df_t)

    if not all_dfs:
        print("No data fetched — falling back to synthetic dataset")
        return _synthetic_fallback()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates("chembl_mol_id", keep="first")
    combined.to_csv(DATASET_PATH, index=False)
    print(f"\nDataset saved: {len(combined)} compounds → {DATASET_PATH}")
    return combined


def _synthetic_fallback(n: int = 600) -> pd.DataFrame:
    """Generate synthetic data if ChEMBL is unreachable."""
    np.random.seed(42)
    tox = np.random.rand(n); bio = np.random.rand(n)
    sol = np.random.rand(n); bind = np.random.rand(n); mw = np.random.rand(n)
    labels = ((bio*0.30 + bind*0.30 + sol*0.20 - tox*0.40) > 0.35).astype(int)
    return pd.DataFrame({
        "chembl_mol_id": [f"SYNTH_{i:04d}" for i in range(n)],
        "smiles": [""] * n,
        "toxicity": tox, "bioavailability": bio, "solubility": sol,
        "binding": bind, "molecular_weight": mw, "label": labels,
        "source": "synthetic",
    })


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: TRAIN MODEL ON REAL DATA
# ─────────────────────────────────────────────────────────────────────────────

def train_on_chembl(df: pd.DataFrame) -> dict:
    """
    Train RandomForest on ChEMBL data.
    Returns model, metadata, and performance metrics.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
    from sklearn.metrics import (roc_auc_score, precision_score,
                                  recall_score, f1_score, accuracy_score)
    from sklearn.calibration import CalibratedClassifierCV

    features = ["toxicity", "bioavailability", "solubility", "binding", "molecular_weight"]
    X = df[features].values
    y = df["label"].values

    # Class balance check
    pos_rate = y.mean()
    print(f"\nClass balance: {pos_rate*100:.1f}% active compounds")
    class_weight = "balanced" if pos_rate < 0.3 or pos_rate > 0.7 else None

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Base RF
    base_rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=3,
        max_features="sqrt",
        class_weight=class_weight,
        random_state=42,
        n_jobs=-1,
    )

    # Calibrated model (better probability estimates)
    model = CalibratedClassifierCV(base_rf, cv=5, method="isotonic")
    model.fit(X_train, y_train)

    # Evaluate
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_auc = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")

    metrics = {
        "test_accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "test_auc":       round(roc_auc_score(y_test, y_prob), 4),
        "test_precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "test_recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "test_f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
        "cv_auc_mean":    round(cv_auc.mean(), 4),
        "cv_auc_std":     round(cv_auc.std(), 4),
        "n_train":        len(X_train),
        "n_test":         len(X_test),
        "pos_rate":       round(pos_rate, 3),
        "data_source":    "ChEMBL" if (df.get("source","") == "ChEMBL").any() else "synthetic",
        "trained_at":     datetime.utcnow().isoformat(),
    }

    print("\nModel performance on ChEMBL data:")
    print(f"  Test AUC:       {metrics['test_auc']:.4f}")
    print(f"  CV AUC:         {metrics['cv_auc_mean']:.4f} ± {metrics['cv_auc_std']:.4f}")
    print(f"  Test Accuracy:  {metrics['test_accuracy']:.4f}")
    print(f"  Test F1:        {metrics['test_f1']:.4f}")

    # Save model + metadata
    joblib.dump(model, MODEL_PATH)
    with open("model_metadata.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nModel saved → {MODEL_PATH}")
    print(f"Metadata saved → model_metadata.json")
    return {"model": model, "metrics": metrics}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: FLASK ENDPOINT (add to api.py)
# ─────────────────────────────────────────────────────────────────────────────

CHEMBL_ROUTES = '''
# ── ADD THESE ROUTES TO api.py ───────────────────────────────────────────────

from chembl_integration import (
    fetch_target_id, load_or_fetch_dataset, train_on_chembl
)

@app.route("/data/import-chembl", methods=["POST"])
def import_chembl():
    """
    POST body:
      {"target_id": "CHEMBL205"}          # by ChEMBL ID
      {"gene": "EGFR"}                    # by gene name (auto-resolves)
      {"targets": ["CHEMBL205","CHEMBL203"]}  # multi-target
      {"max_records": 2000}               # optional cap
    """
    global model
    data     = request.get_json()
    max_recs = data.get("max_records", 1500)

    target_ids = []
    if "target_id" in data:
        target_ids = [data["target_id"]]
    elif "gene" in data:
        target_ids = [fetch_target_id(data["gene"])]
    elif "targets" in data:
        target_ids = data["targets"]
    else:
        return jsonify({"error": "Provide target_id, gene, or targets"}), 400

    try:
        df     = load_or_fetch_dataset(target_ids, max_per_target=max_recs)
        result = train_on_chembl(df)
        model  = result["model"]   # hot-swap the running model
        return jsonify({
            "status":   "success",
            "message":  f"Model retrained on {result['metrics']['n_train']} ChEMBL compounds",
            "metrics":  result["metrics"],
            "targets":  target_ids,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/data/chembl-status", methods=["GET"])
def chembl_status():
    meta_path = "model_metadata.json"
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return jsonify(json.load(f))
    return jsonify({"status": "No ChEMBL data loaded yet — using synthetic data"})

@app.route("/data/dataset-info", methods=["GET"])
def dataset_info():
    if os.path.exists(DATASET_PATH):
        df = pd.read_csv(DATASET_PATH)
        return jsonify({
            "total_compounds":  len(df),
            "active_compounds": int(df["label"].sum()),
            "sources":          df["source"].value_counts().to_dict(),
            "targets":          df.get("target_id", pd.Series()).value_counts().to_dict(),
            "path":             DATASET_PATH,
        })
    return jsonify({"status": "No dataset file found"})
'''


# ─────────────────────────────────────────────────────────────────────────────
# CLI RUNNER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NovaCura ChEMBL Data Integration")
    parser.add_argument("--target",  type=str, help="ChEMBL target ID (e.g. CHEMBL205)")
    parser.add_argument("--gene",    type=str, help="Gene name (e.g. EGFR)")
    parser.add_argument("--targets", type=str, help="Comma-separated ChEMBL IDs")
    parser.add_argument("--max",     type=int, default=1500, help="Max records per target")
    parser.add_argument("--retrain", action="store_true", help="Force retrain even if cached")
    args = parser.parse_args()

    if args.retrain and os.path.exists(DATASET_PATH):
        os.remove(DATASET_PATH)
        print("Cleared dataset cache — will re-fetch from ChEMBL")

    target_ids = []
    if args.target:
        target_ids = [args.target]
    elif args.gene:
        target_ids = [fetch_target_id(args.gene)]
    elif args.targets:
        target_ids = [t.strip() for t in args.targets.split(",")]
    else:
        # Default: EGFR (CHEMBL203), CDK2 (CHEMBL301), BRAF (CHEMBL5145)
        print("No target specified — using default oncology targets: EGFR, CDK2, BRAF")
        target_ids = ["CHEMBL203", "CHEMBL301", "CHEMBL5145"]

    df     = load_or_fetch_dataset(target_ids, max_per_target=args.max)
    result = train_on_chembl(df)

    print("\n" + "─"*50)
    print("ChEMBL integration complete.")
    print(f"  Compounds:  {result['metrics']['n_train'] + result['metrics']['n_test']}")
    print(f"  AUC:        {result['metrics']['test_auc']:.4f}")
    print(f"  Next step:  python smiles_pipeline.py  (Upgrade 2)")
