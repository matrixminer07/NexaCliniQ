from __future__ import annotations

import asyncio
import hashlib
from typing import Dict, List, Optional

import torch
from torch_geometric.loader import DataLoader

from backend.ml.gnn.molecular_gnn import MolecularGNN, infer_graph_dims, smiles_to_graph


class GNNPredictor:
    """Production inference class with in-memory caching and batching."""

    def __init__(self, model_path: str, device: str = "cpu"):
        dims = infer_graph_dims()
        self.device = device
        self.model = MolecularGNN(dims.node_dim, dims.edge_dim).to(device)
        self.model.load_state_dict(torch.load(model_path, map_location=device))
        self.model.eval()
        self.cache: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()

    def _key(self, smiles: str) -> str:
        return hashlib.sha256(smiles.encode("utf-8")).hexdigest()

    async def predict_properties(self, smiles_list: List[str]) -> Dict:
        async with self.lock:
            todo = [s for s in smiles_list if self._key(s) not in self.cache]

            batch_data = []
            valid_smiles = []
            for s in todo:
                try:
                    batch_data.append(smiles_to_graph(s))
                    valid_smiles.append(s)
                except Exception:
                    self.cache[self._key(s)] = {"smiles": s, "error": "invalid_smiles"}

            if batch_data:
                loader = DataLoader(batch_data, batch_size=min(64, len(batch_data)), shuffle=False)
                preds = []
                with torch.no_grad():
                    for batch in loader:
                        out = self.model(batch.to(self.device)).squeeze(-1).detach().cpu().tolist()
                        preds.extend(out if isinstance(out, list) else [out])
                for s, p in zip(valid_smiles, preds):
                    self.cache[self._key(s)] = {"smiles": s, "predictions": {"property": float(p)}}

            return {"results": [self.cache[self._key(s)] for s in smiles_list]}

    def explain_prediction(self, smiles: str) -> Dict:
        # Placeholder explanation until integrated with GNNExplainer/SHAP.
        if smiles_to_graph(smiles).x.shape[0] == 0:
            return {"error": "invalid_smiles"}
        return {
            "smiles": smiles,
            "method": "gnnexplainer_placeholder",
            "atom_importance": [],
            "message": "Enable torch_geometric.explain for full attributions.",
        }
