import csv
import io
import os
from collections import Counter
from datetime import datetime
from typing import Any

import requests

from backend.db_pg import execute, fetch_latest_deployed_model, init_db_schema, insert_model_version

try:
    from rdkit import Chem  # pyright: ignore[reportMissingImports]
    from rdkit.Chem import rdMolStandardize, inchi  # pyright: ignore[reportMissingImports]
except Exception:
    Chem = None
    rdMolStandardize = None
    inchi = None


CHEMBL_ACTIVITY_URL = "https://www.ebi.ac.uk/chembl/api/data/activity.json?format=json&limit=1000"
TOX21_CSV_URL = "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/tox21.csv.gz"
ADMET_AI_CSV_URL = "https://raw.githubusercontent.com/swansonk14/admet_ai/main/admet_ai/data/admet_benchmark.csv"
PUBCHEM_REST_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

CHEMBL_TARGETS = {
    "toxicity": "CHEMBL3301",
    "binding": os.getenv("CHEMBL_BINDING_TARGET", "CHEMBL203"),
    "bioavailability": os.getenv("CHEMBL_BIOAVAIL_TARGET", "CHEMBL25"),
    "solubility": os.getenv("CHEMBL_SOLUBILITY_TARGET", "CHEMBL1907601"),
}
PUBCHEM_AIDS = [
    aid.strip()
    for aid in os.getenv("PUBCHEM_AID_LIST", "743269,720709").split(",")
    if aid.strip()
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _standardize_smiles(smiles: str) -> tuple[str, str]:
    if not smiles:
        return "", ""
    if Chem is None:
        return smiles, ""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return "", ""
    if rdMolStandardize is not None:
        try:
            parent = rdMolStandardize.FragmentParent(mol)
            uncharger = rdMolStandardize.Uncharger()
            mol = uncharger.uncharge(parent)
        except Exception:
            pass
    clean_smiles = Chem.MolToSmiles(mol, canonical=True)
    inchikey = inchi.MolToInchiKey(mol) if inchi is not None else ""
    return clean_smiles, inchikey


def _insert_raw(source: str, smiles: str, inchikey: str, endpoint: str, value: float, units: str) -> None:
    execute(
        """
        INSERT INTO raw_bioactivity (source, compound_smiles, inchikey, endpoint, value, units)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [source, smiles, inchikey, endpoint, value, units],
    )


def _upsert_training(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO training_data (
          inchikey, smiles, toxicity, bioavailability, solubility, binding, molecular_weight, label, source
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            row.get("inchikey"),
            row.get("smiles"),
            row.get("toxicity"),
            row.get("bioavailability"),
            row.get("solubility"),
            row.get("binding"),
            row.get("molecular_weight"),
            row.get("label"),
            row.get("source"),
        ],
    )


def _endpoint_from_standard_type(standard_type: str) -> str:
    t = (standard_type or "").strip().lower()
    if t in {"ic50", "ki", "kd", "potency"}:
        return "binding"
    if t in {"solubility", "aq solubility"}:
        return "solubility"
    if "tox" in t:
        return "toxicity"
    if t in {"f", "bioavailability", "auc"}:
        return "bioavailability"
    return "binding"


def _normalize_training_row(source: str, clean: str, inchikey: str, endpoint: str, value: float) -> dict[str, Any]:
    endpoint_name = (endpoint or "binding").strip().lower()
    tox = 0.5
    bio = 0.5
    sol = 0.5
    bind = 0.5

    normalized = min(max(value, 0.0), 1.0)
    if endpoint_name == "toxicity":
        tox = normalized
    elif endpoint_name == "bioavailability":
        bio = normalized
    elif endpoint_name == "solubility":
        sol = normalized
    else:
        bind = normalized

    return {
        "inchikey": inchikey,
        "smiles": clean,
        "toxicity": tox,
        "bioavailability": bio,
        "solubility": sol,
        "binding": bind,
        "molecular_weight": min(max(len(clean) / 50.0, 0.0), 1.0),
        "label": 1 if bind >= 0.5 and tox <= 0.6 else 0,
        "source": source,
    }


def _pull_chembl() -> list[dict[str, Any]]:
    out = []
    for endpoint_name, target_id in CHEMBL_TARGETS.items():
        url = f"{CHEMBL_ACTIVITY_URL}&target_chembl_id={target_id}"
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            payload = r.json() if r.content else {}
        except Exception:
            continue

        for a in payload.get("activities", []):
            smiles = a.get("canonical_smiles") or ""
            clean, inchikey = _standardize_smiles(smiles)
            if not clean:
                continue
            std_type = a.get("standard_type") or endpoint_name
            endpoint = endpoint_name if endpoint_name in {"toxicity", "bioavailability", "solubility", "binding"} else _endpoint_from_standard_type(std_type)
            raw_val = _safe_float(a.get("standard_value"), 0.0)
            value = min(max(raw_val / 1000.0, 0.0), 1.0) if raw_val > 1.0 else min(max(raw_val, 0.0), 1.0)
            units = (a.get("standard_units") or "")
            _insert_raw("chembl", clean, inchikey, endpoint, value, units)
            out.append(_normalize_training_row("chembl", clean, inchikey, endpoint, value))
    return out


def _pull_pubchem() -> list[dict[str, Any]]:
    out = []
    for aid in PUBCHEM_AIDS:
        try:
            aid_url = f"{PUBCHEM_REST_BASE}/assay/aid/{aid}/CSV"
            r = requests.get(aid_url, timeout=30)
            r.raise_for_status()
            rows = csv.DictReader(io.StringIO(r.text))
        except Exception:
            continue

        for i, row in enumerate(rows):
            smiles = row.get("SMILES") or row.get("CanonicalSMILES") or ""
            clean, inchikey = _standardize_smiles(smiles)
            if not clean:
                continue

            endpoint = "binding"
            if str(aid).strip() in {"720709"}:
                endpoint = "toxicity"

            score = _safe_float(row.get("PUBCHEM_ACTIVITY_SCORE"), 0.0)
            value = min(max(score / 100.0, 0.0), 1.0)
            _insert_raw("pubchem", clean, inchikey, endpoint, value, "activity_score")
            out.append(_normalize_training_row("pubchem", clean, inchikey, endpoint, value))
            if i >= 2000:
                break
    return out


def _pull_tox21() -> list[dict[str, Any]]:
    out = []
    try:
        r = requests.get(TOX21_CSV_URL, timeout=30)
        r.raise_for_status()
        import gzip

        rows = csv.DictReader(io.StringIO(gzip.decompress(r.content).decode("utf-8", errors="ignore")))
        for i, row in enumerate(rows):
            smiles = row.get("smiles", "")
            clean, inchikey = _standardize_smiles(smiles)
            if not clean:
                continue
            tox = max([_safe_float(row.get(k), 0.0) for k in row.keys() if k.startswith("NR-")] + [0.0])
            _insert_raw("tox21", clean, inchikey, "toxicity", tox, "binary")
            out.append(
                {
                    "inchikey": inchikey,
                    "smiles": clean,
                    "toxicity": min(max(tox, 0.0), 1.0),
                    "bioavailability": 0.5,
                    "solubility": 0.5,
                    "binding": 0.5,
                    "molecular_weight": min(max(len(clean) / 50.0, 0.0), 1.0),
                    "label": 0 if tox > 0.5 else 1,
                    "source": "tox21",
                }
            )
            if i >= 2000:
                break
    except Exception:
        return []
    return out


def _pull_admet_ai() -> list[dict[str, Any]]:
    out = []
    try:
        r = requests.get(ADMET_AI_CSV_URL, timeout=30)
        r.raise_for_status()
        rows = csv.DictReader(io.StringIO(r.text))
        for i, row in enumerate(rows):
            smiles = row.get("smiles", "")
            clean, inchikey = _standardize_smiles(smiles)
            if not clean:
                continue
            bio = _safe_float(row.get("caco2_wang"), 0.5)
            sol = _safe_float(row.get("solubility_aqsoldb"), 0.5)
            _insert_raw("admet_ai", clean, inchikey, "admet", (bio + sol) / 2.0, "normalized")
            out.append(
                {
                    "inchikey": inchikey,
                    "smiles": clean,
                    "toxicity": 0.5,
                    "bioavailability": min(max(bio, 0.0), 1.0),
                    "solubility": min(max(sol, 0.0), 1.0),
                    "binding": 0.5,
                    "molecular_weight": min(max(len(clean) / 50.0, 0.0), 1.0),
                    "label": 1,
                    "source": "admet_ai",
                }
            )
            if i >= 2000:
                break
    except Exception:
        return []
    return out


def sync_datasets_task() -> dict[str, Any]:
    init_db_schema()

    all_rows = []
    all_rows.extend(_pull_chembl())
    all_rows.extend(_pull_pubchem())
    all_rows.extend(_pull_tox21())
    all_rows.extend(_pull_admet_ai())

    unique = {}
    for row in all_rows:
        key = row.get("inchikey") or row.get("smiles")
        if not key:
            continue
        unique[key] = row

    for row in unique.values():
        _upsert_training(row)

    counts = Counter([r.get("source", "unknown") for r in unique.values()])

    latest = fetch_latest_deployed_model()
    sync_metadata = {
        "source_breakdown": dict(counts),
        "sync_task": "sync_datasets_task",
        "sync_time": datetime.utcnow().isoformat() + "Z",
        "records_after_dedup": len(unique),
        "chembl_targets": CHEMBL_TARGETS,
        "pubchem_aids": PUBCHEM_AIDS,
    }
    insert_model_version(
        {
            "version": datetime.utcnow().strftime("data-sync-%Y%m%d%H%M%S"),
            "algorithm": latest.get("algorithm", "stacked_ensemble") if latest else "stacked_ensemble",
            "training_dataset_size": len(unique),
            "val_auc": latest.get("val_auc") if latest else None,
            "val_f1": latest.get("val_f1") if latest else None,
            "val_brier": latest.get("val_brier") if latest else None,
            "artifact_path": latest.get("artifact_path", "backend/ensemble") if latest else "backend/ensemble",
            "deployed": False,
            "sync_metadata": sync_metadata,
        }
    )

    return {
        "success": True,
        "total_clean_records": len(unique),
        "source_breakdown": dict(counts),
        "sync_metadata": sync_metadata,
    }
