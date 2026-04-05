from __future__ import annotations

from io import StringIO
from typing import Iterable

import pandas as pd
import requests


class ADMETDatasets:
    """Dataset utilities for TDC, ADMETlab-like CSVs, and ChEMBL assay exports."""

    @staticmethod
    def load_tdc_csv(url: str) -> pd.DataFrame:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return pd.read_csv(StringIO(response.text))

    @staticmethod
    def load_admetlab_csv(path_or_url: str) -> pd.DataFrame:
        if path_or_url.startswith("http"):
            response = requests.get(path_or_url, timeout=60)
            response.raise_for_status()
            return pd.read_csv(StringIO(response.text))
        return pd.read_csv(path_or_url)

    @staticmethod
    def filter_chembl_admet(df: pd.DataFrame, assays: Iterable[str]) -> pd.DataFrame:
        if "assay_type" not in df.columns:
            return df
        assays_norm = {a.lower() for a in assays}
        return df[df["assay_type"].astype(str).str.lower().isin(assays_norm)].copy()
