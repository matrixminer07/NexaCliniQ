from __future__ import annotations

import time
from typing import Dict, List

import requests


class PubChem:
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def get_compound_by_smiles(self, smiles: str) -> Dict:
        url = f"{self.BASE_URL}/compound/smiles/{smiles}/JSON"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_bioassay_data(self, cid: int) -> List[Dict]:
        url = f"{self.BASE_URL}/compound/cid/{cid}/assaysummary/JSON"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json().get("Table", {}).get("Row", [])

    def bulk_download_properties(self, cids: List[int], properties: List[str], rate_limit_s: float = 0.2):
        out = []
        props_str = ",".join(properties)
        for cid in cids:
            url = f"{self.BASE_URL}/compound/cid/{cid}/property/{props_str}/JSON"
            response = requests.get(url, timeout=30)
            if response.ok:
                out.append(response.json())
            time.sleep(rate_limit_s)
        return out
