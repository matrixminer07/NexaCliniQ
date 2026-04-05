from __future__ import annotations

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, MACCSkeys, rdMolDescriptors


class MolecularFeatureExtractor:
    """Molecular descriptor and fingerprint extraction."""

    def extract_2d_features(self, smiles: str):
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        values = [
            Descriptors.MolWt(mol),
            Descriptors.MolLogP(mol),
            Descriptors.TPSA(mol),
            Descriptors.NumHDonors(mol),
            Descriptors.NumHAcceptors(mol),
            Descriptors.NumRotatableBonds(mol),
            rdMolDescriptors.CalcNumAromaticRings(mol),
        ]

        # Extend to broad descriptor coverage from RDKit descriptor registry.
        descriptor_funcs = [f for _, f in Descriptors.descList]
        for fn in descriptor_funcs:
            try:
                values.append(float(fn(mol)))
            except Exception:
                values.append(0.0)
            if len(values) >= 220:
                break
        return np.array(values, dtype=np.float32)

    def extract_fingerprints(self, smiles: str, fp_type: str = "morgan"):
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        if fp_type == "morgan":
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
        elif fp_type == "maccs":
            fp = MACCSkeys.GenMACCSKeys(mol)
        else:
            fp = Chem.RDKFingerprint(mol, fpSize=2048)
        return np.array(list(fp), dtype=np.int8)
