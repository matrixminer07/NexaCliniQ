# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportGeneralTypeIssues=false
"""
AttentiveFP molecular property predictor.

This module is a drop-in replacement for the previous joblib-oriented GNN helper.
It preserves legacy function names used across the API layer:
- load_gnn_model
- predict_gnn
- train_gnn

Optional dependencies:
  pip install torch torch-geometric rdkit-pypi
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

GNN_MODEL_PATH = "gnn_model.pt"


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    try:
        from torch_geometric.loader import DataLoader
    except Exception:
        from torch_geometric.data import DataLoader

    from torch_geometric.data import Batch, Data
    from torch_geometric.nn import AttentiveFP

    TORCH_GEOMETRIC_AVAILABLE = True
except Exception:
    torch = None
    nn = None
    F = None
    DataLoader = None
    Batch = None
    Data = None
    AttentiveFP = None
    TORCH_GEOMETRIC_AVAILABLE = False

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    RDKIT_AVAILABLE = True
except Exception:
    Chem = None
    AllChem = None
    RDKIT_AVAILABLE = False


ATOM_FEATURES = {
    "atomic_num": list(range(1, 119)),
    "degree": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "formal_charge": [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5],
    "hybridization": [],
    "num_hs": [0, 1, 2, 3, 4],
}

if RDKIT_AVAILABLE:
    ATOM_FEATURES["hybridization"] = [
        Chem.rdchem.HybridizationType.SP,
        Chem.rdchem.HybridizationType.SP2,
        Chem.rdchem.HybridizationType.SP3,
        Chem.rdchem.HybridizationType.SP3D,
        Chem.rdchem.HybridizationType.SP3D2,
    ]


def _one_hot(value, choices):
    enc = [0] * (len(choices) + 1)
    if value in choices:
        enc[choices.index(value)] = 1
    else:
        enc[-1] = 1
    return enc


def atom_features(atom) -> List[float]:
    feats = []
    feats += _one_hot(atom.GetAtomicNum(), ATOM_FEATURES["atomic_num"])
    feats += _one_hot(atom.GetDegree(), ATOM_FEATURES["degree"])
    feats += _one_hot(atom.GetFormalCharge(), ATOM_FEATURES["formal_charge"])
    feats += _one_hot(atom.GetHybridization(), ATOM_FEATURES["hybridization"])
    feats += _one_hot(atom.GetTotalNumHs(), ATOM_FEATURES["num_hs"])
    feats += [
        int(atom.GetIsAromatic()),
        int(atom.IsInRing()),
        atom.GetMass() / 100.0,
    ]
    return feats


def bond_features(bond) -> List[float]:
    bond_type = bond.GetBondType()
    return [
        int(bond_type == Chem.rdchem.BondType.SINGLE),
        int(bond_type == Chem.rdchem.BondType.DOUBLE),
        int(bond_type == Chem.rdchem.BondType.TRIPLE),
        int(bond_type == Chem.rdchem.BondType.AROMATIC),
        int(bond.GetIsConjugated()),
        int(bond.IsInRing()),
    ]


def _infer_dims() -> tuple[int, int]:
    if not RDKIT_AVAILABLE:
        return 0, 6
    mol = Chem.MolFromSmiles("C")
    if mol is None:
        return 0, 6
    atom_dim = len(atom_features(mol.GetAtomWithIdx(0)))
    return atom_dim, 6


ATOM_DIM, BOND_DIM = _infer_dims()


def smiles_to_graph(smiles: str):
    if not (TORCH_GEOMETRIC_AVAILABLE and RDKIT_AVAILABLE):
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    mol = Chem.AddHs(mol)
    x = torch.tensor([atom_features(a) for a in mol.GetAtoms()], dtype=torch.float)

    edges_src: List[int] = []
    edges_dst: List[int] = []
    edge_attr: List[List[float]] = []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        bf = bond_features(bond)
        edges_src.extend([i, j])
        edges_dst.extend([j, i])
        edge_attr.extend([bf, bf])

    if not edges_src:
        return None

    edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
    edge_attr_tensor = torch.tensor(edge_attr, dtype=torch.float)
    return Data(x=x, edge_index=edge_index, edge_attr=edge_attr_tensor)  # type: ignore[operator]


def get_morgan_fp(smiles: str, radius: int = 2, nbits: int = 2048) -> Optional[np.ndarray]:
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=nbits)
    return np.asarray(fp, dtype=np.float32)


class MolecularGNN(nn.Module if TORCH_GEOMETRIC_AVAILABLE else object):
    def __init__(
        self,
        in_channels: int = ATOM_DIM,
        hidden_channels: int = 200,
        out_channels: int = 200,
        edge_dim: int = BOND_DIM,
        num_layers: int = 2,
        num_timesteps: int = 2,
        dropout: float = 0.2,
        task_names: Optional[List[str]] = None,
    ):
        if not TORCH_GEOMETRIC_AVAILABLE:
            raise ImportError("torch-geometric and torch are required for MolecularGNN")

        super().__init__()
        self.task_names = task_names or ["activity"]

        self.gnn = AttentiveFP(  # type: ignore[operator]
            in_channels=in_channels,
            hidden_channels=hidden_channels,
            out_channels=out_channels,
            edge_dim=edge_dim,
            num_layers=num_layers,
            num_timesteps=num_timesteps,
            dropout=dropout,
        )

        fp_dim = 2048
        fusion_dim = out_channels + fp_dim

        self.fusion = nn.Sequential(
            nn.Linear(fusion_dim, 512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        self.heads = nn.ModuleDict({name: nn.Linear(256, 1) for name in self.task_names})

    def forward(self, data, fingerprint: Optional[object] = None) -> Dict[str, object]:
        gnn_out = self.gnn(data.x, data.edge_index, data.edge_attr, data.batch)

        if fingerprint is None:
            fingerprint = torch.zeros(gnn_out.size(0), 2048, device=gnn_out.device)

        fused = torch.cat([gnn_out, fingerprint], dim=-1)
        h = self.fusion(fused)
        return {name: self.heads[name](h).squeeze(-1) for name in self.task_names}

    def predict_with_uncertainty(
        self,
        data,
        fingerprint: Optional[object] = None,
        n_samples: int = 20,
    ) -> Dict[str, Dict[str, List[float]]]:
        self.train()
        preds = {name: [] for name in self.task_names}

        with torch.no_grad():
            for _ in range(max(1, n_samples)):
                out = self.forward(data, fingerprint)
                for name in self.task_names:
                    preds[name].append(out[name].detach().cpu().numpy())

        self.eval()
        results: Dict[str, Dict[str, List[float]]] = {}
        for name in self.task_names:
            arr = np.stack(preds[name], axis=0)
            results[name] = {
                "mean": arr.mean(axis=0).tolist(),
                "std": arr.std(axis=0).tolist(),
                "lower_ci": np.percentile(arr, 10, axis=0).tolist(),
                "upper_ci": np.percentile(arr, 90, axis=0).tolist(),
            }
        return results


class GNNInferenceService:
    def __init__(self, model: MolecularGNN, device: str = "cpu"):
        self.device = device
        self.model = model.to(device)
        self.model.eval()

    @classmethod
    def load(
        cls,
        checkpoint_path: str,
        task_names: Optional[List[str]] = None,
        device: str = "cpu",
    ):
        if not TORCH_GEOMETRIC_AVAILABLE:
            raise ImportError("torch-geometric and torch are not installed")

        state = torch.load(checkpoint_path, map_location=device)
        ckpt_task_names = state.get("task_names") or task_names or ["activity"]
        model_cfg = state.get("model_config", {})

        model = MolecularGNN(task_names=ckpt_task_names, **model_cfg)
        model.load_state_dict(state["model_state_dict"])
        return cls(model, device=device)

    def _prepare_batch(self, smiles_list: List[str]):
        graphs = []
        fps = []
        valid_smiles = []

        for smiles in smiles_list:
            graph = smiles_to_graph(smiles)
            fp = get_morgan_fp(smiles)
            if graph is None or fp is None:
                continue
            graphs.append(graph)
            fps.append(fp)
            valid_smiles.append(smiles)

        if not graphs:
            return None, None, []

        batch = Batch.from_data_list(graphs).to(self.device)
        fp_tensor = torch.tensor(np.stack(fps), dtype=torch.float, device=self.device)
        return batch, fp_tensor, valid_smiles

    def predict(self, smiles: str, uncertainty: bool = True) -> dict:
        batch, fp_tensor, valid = self._prepare_batch([smiles])
        if not valid:
            return {"error": f"Invalid SMILES: {smiles}"}

        if uncertainty:
            predictions = self.model.predict_with_uncertainty(batch, fp_tensor)
        else:
            with torch.no_grad():
                out = self.model(batch, fp_tensor)
            predictions = {name: {"mean": out[name].detach().cpu().numpy().tolist()} for name in self.model.task_names}

        return {"smiles": smiles, "predictions": predictions}


_inference_service: Optional[GNNInferenceService] = None


def load_gnn_model() -> Optional[GNNInferenceService]:
    global _inference_service

    if _inference_service is not None:
        return _inference_service

    if not TORCH_GEOMETRIC_AVAILABLE or not RDKIT_AVAILABLE:
        return None

    if not os.path.exists(GNN_MODEL_PATH):
        return None

    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        _inference_service = GNNInferenceService.load(GNN_MODEL_PATH, task_names=["activity"], device=device)
        return _inference_service
    except Exception as exc:
        logger.warning("Failed loading GNN checkpoint: %s", exc)
        return None


def _verdict_from_prob(prob: float) -> str:
    if prob >= 0.7:
        return "PASS"
    if prob >= 0.4:
        return "CAUTION"
    return "FAIL"


def predict_gnn(smiles: str) -> dict:
    if not TORCH_GEOMETRIC_AVAILABLE or not RDKIT_AVAILABLE:
        return {
            "error": "PyTorch Geometric or RDKit not installed",
            "fallback": True,
            "model_used": "random_forest",
        }

    service = load_gnn_model()
    if service is None:
        return {
            "error": "GNN model not trained yet. Run train_gnn() first.",
            "fallback": True,
            "model_used": "random_forest",
        }

    result = service.predict(smiles, uncertainty=True)
    if "error" in result:
        return result

    activity = result["predictions"]["activity"]
    mean_prob = float(activity["mean"][0])
    std_prob = float(activity.get("std", [0.0])[0])
    p10 = float(activity.get("lower_ci", [mean_prob])[0])
    p90 = float(activity.get("upper_ci", [mean_prob])[0])

    return {
        "smiles": smiles,
        "gnn_probability": round(mean_prob, 4),
        "success_probability": round(mean_prob, 4),
        "confidence_interval": {
            "p10": round(p10, 4),
            "p50": round(mean_prob, 4),
            "p90": round(p90, 4),
            "std": round(std_prob, 4),
        },
        "verdict": _verdict_from_prob(mean_prob),
        "model_used": "graph_neural_network",
        "fallback": False,
    }


def train_gnn(
    smiles_list: List[str],
    labels,
    epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    hidden_dim: int = 200,
) -> dict:
    if not TORCH_GEOMETRIC_AVAILABLE:
        return {"error": "PyTorch Geometric not installed. Run: pip install torch torch-geometric"}
    if not RDKIT_AVAILABLE:
        return {"error": "RDKit not installed. Run: pip install rdkit-pypi"}

    if isinstance(labels, dict):
        task_names = list(labels.keys())
        label_matrix = labels
    else:
        task_names = ["activity"]
        label_matrix = {"activity": labels}

    dataset = []
    for i, smiles in enumerate(smiles_list):
        graph = smiles_to_graph(smiles)
        fp = get_morgan_fp(smiles)
        if graph is None or fp is None:
            continue

        values = []
        valid_row = True
        for task in task_names:
            task_values = label_matrix.get(task)
            if task_values is None or i >= len(task_values):
                valid_row = False
                break
            try:
                values.append(float(task_values[i]))
            except Exception:
                valid_row = False
                break

        if not valid_row:
            continue

        graph.fp = torch.tensor(fp, dtype=torch.float)
        graph.y = torch.tensor(values, dtype=torch.float)
        dataset.append(graph)

    if len(dataset) < 10:
        return {"error": f"Only {len(dataset)} valid compounds found. Need at least 10."}

    split_idx = max(1, int(0.8 * len(dataset)))
    train_set = dataset[:split_idx]
    val_set = dataset[split_idx:] if split_idx < len(dataset) else dataset[:1]

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)  # type: ignore[operator]
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False)  # type: ignore[operator]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = MolecularGNN(task_names=task_names, hidden_channels=hidden_dim, out_channels=hidden_dim).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=8)

    best_state = None
    best_val_loss = float("inf")

    for epoch in range(epochs):
        model.train()
        train_loss_total = 0.0

        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            out = model(batch, batch.fp)
            loss = 0.0
            for idx, task in enumerate(task_names):
                loss = loss + F.mse_loss(out[task], batch.y[:, idx])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss_total += float(loss.item())

        model.eval()
        val_loss_total = 0.0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                out = model(batch, batch.fp)
                val_loss = 0.0
                for idx, task in enumerate(task_names):
                    val_loss = val_loss + F.mse_loss(out[task], batch.y[:, idx])
                val_loss_total += float(val_loss.item())

        avg_val_loss = val_loss_total / max(1, len(val_loader))
        scheduler.step(avg_val_loss)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        if epoch % 10 == 0 or epoch == epochs - 1:
            avg_train_loss = train_loss_total / max(1, len(train_loader))
            logger.info("Epoch %d | train_loss=%.4f val_loss=%.4f", epoch, avg_train_loss, avg_val_loss)

    if best_state is not None:
        model.load_state_dict(best_state)

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "task_names": task_names,
        "model_config": {
            "in_channels": ATOM_DIM,
            "hidden_channels": hidden_dim,
            "out_channels": hidden_dim,
            "edge_dim": BOND_DIM,
            "num_layers": 2,
            "num_timesteps": 2,
            "dropout": 0.2,
        },
        "best_val_auc": None,
        "best_val_loss": float(best_val_loss),
        "n_compounds": len(dataset),
        "trained_at": datetime.utcnow().isoformat(),
    }

    torch.save(checkpoint, GNN_MODEL_PATH)

    global _inference_service
    _inference_service = None

    return {
        "status": "trained",
        "best_val_auc": None,
        "best_val_loss": round(float(best_val_loss), 6),
        "n_compounds": len(dataset),
        "trained_at": checkpoint["trained_at"],
    }
