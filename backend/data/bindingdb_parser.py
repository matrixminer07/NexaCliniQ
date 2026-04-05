from __future__ import annotations

import pandas as pd


class BindingDBParser:
    """Parse and normalize BindingDB downloads."""

    def parse_tsv(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, sep="\t", low_memory=False)
        if "Ligand SMILES" not in df.columns:
            raise ValueError("Expected 'Ligand SMILES' column not found")
        df = df[df["Ligand SMILES"].notna()].copy()
        df = self._standardize_smiles(df)
        return self._convert_units(df)

    def _standardize_smiles(self, df: pd.DataFrame) -> pd.DataFrame:
        from rdkit import Chem

        def canon(smi: str):
            try:
                mol = Chem.MolFromSmiles(str(smi))
                return Chem.MolToSmiles(mol) if mol else None
            except Exception:
                return None

        df["canonical_smiles"] = df["Ligand SMILES"].apply(canon)
        return df[df["canonical_smiles"].notna()].copy()

    def _convert_units(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ["Ki (nM)", "IC50 (nM)", "Kd (nM)"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def import_to_database(self, df: pd.DataFrame, engine):
        df.to_sql("binding_data", engine, if_exists="append", index=False)
