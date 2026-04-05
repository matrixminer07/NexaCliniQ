from __future__ import annotations

import logging
from typing import List

from backend.celery_app import celery_app
from backend.data.pubchem_client import PubChem


logger = logging.getLogger(__name__)


@celery_app.task
def sync_pubchem_data(smiles_list: List[str]):
    pubchem = PubChem()
    synced = []
    for smiles in smiles_list:
        try:
            payload = pubchem.get_compound_by_smiles(smiles)
            synced.append({"smiles": smiles, "payload": payload})
        except Exception as exc:
            logger.error("pubchem_sync_failed", extra={"smiles": smiles, "error": str(exc)})
    return {"total": len(smiles_list), "synced": len(synced)}
