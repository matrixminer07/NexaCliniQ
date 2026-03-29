"""
UPGRADE 8: Graph Neural Network (GNN) Model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Replaces tabular Random Forest with a PyTorch Geometric GNN that reads
molecular graphs directly from SMILES strings.

Atoms = nodes, bonds = edges. The GNN learns chemical patterns directly
from molecular topology — same class of AI used by Isomorphic Labs
(DeepMind's drug discovery spin-out) and Recursion Pharmaceuticals.

Architecture: Message Passing Neural Network (MPNN)
  Input: Atom features (atomic number, degree, formal charge, aromaticity, ...)
  Layers: 3× GINConv (Graph Isomorphism Network)
  Readout: Global mean + max pooling
  Output: Binary classification (active/inactive)

Install:
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  pip install torch_geometric
  pip install rdkit-pypi
"""

import numpy as np
import json
import os
from datetime import datetime

GNN_MODEL_PATH = "gnn_model.pt"

# ── Try importing PyTorch Geometric ──────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.data import Data, DataLoader
    from torch_geometric.nn import GINConv, global_mean_pool, global_max_pool
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from rdkit import Chem
    from rdkit.Chem import rdmolops
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# ATOM AND BOND FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

ATOM_TYPES = ['C','N','O','S','F','Cl','Br','I','P','Si','B','Se','other']
HYBRIDISATION = ['SP','SP2','SP3','SP3D','SP3D2','other']

def atom_features(atom) -> list:
    """
    18-dimensional atom feature vector.
    """
    atom_type_one_hot = [int(atom.GetSymbol() == t) for t in ATOM_TYPES]
    return atom_type_one_hot + [
        atom.GetDegree() / 10.0,
        atom.GetFormalCharge() / 4.0,
        float(atom.GetIsAromatic()),
        float(atom.IsInRing()),
        atom.GetTotalNumHs() / 4.0,
    ]   # 13 + 5 = 18 features


def bond_features(bond) -> list:
    """4-dimensional bond feature vector."""
    bt = bond.GetBondTypeAsDouble()
    return [
        float(bt == 1.0),   # single
        float(bt == 2.0),   # double
        float(bt == 3.0),   # triple
        float(bt == 1.5),   # aromatic
    ]


def smiles_to_graph(smiles: str):
    """Convert SMILES to a PyTorch Geometric Data object."""
    if not RDKIT_AVAILABLE or not TORCH_AVAILABLE:
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    # Node features (atoms)
    node_feats = [atom_features(a) for a in mol.GetAtoms()]
    if not node_feats:
        return None
    x = torch.tensor(node_feats, dtype=torch.float)

    # Edge index + edge features (bonds)
    edge_index, edge_attr = [], []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        bf = bond_features(bond)
        edge_index += [[i, j], [j, i]]   # undirected
        edge_attr += [bf, bf]

    if edge_index:
        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        edge_attr = torch.tensor(edge_attr, dtype=torch.float)
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 4), dtype=torch.float)

    return Data(x=x, edge_index=edge_index, edge_attr=edge_attr)


# ─────────────────────────────────────────────────────────────────────────────
# GNN MODEL ARCHITECTURE
# ─────────────────────────────────────────────────────────────────────────────

class DrugGNN(torch.nn.Module if TORCH_AVAILABLE else object):
    """
    Message Passing Neural Network for drug activity prediction.
    Architecture: 3-layer GIN + global pooling + 2-layer MLP classifier
    """
    def __init__(self,
                 node_features: int = 18,
                 hidden_dim: int = 128,
                 n_layers: int = 3,
                 dropout: float = 0.3):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch not available. Install with: pip install torch torchvision")
        
        super().__init__()
        self.hidden_dim = hidden_dim

        # GIN layers (Graph Isomorphism Network — maximally expressive)
        self.convs = torch.nn.ModuleList()
        self.bns = torch.nn.ModuleList()

        in_dim = node_features
        for _ in range(n_layers):
            mlp = torch.nn.Sequential(
                torch.nn.Linear(in_dim, hidden_dim * 2),
                torch.nn.ReLU(),
                torch.nn.BatchNorm1d(hidden_dim * 2),
                torch.nn.Linear(hidden_dim * 2, hidden_dim),
            )
            self.convs.append(GINConv(mlp, train_eps=True))
            self.bns.append(torch.nn.BatchNorm1d(hidden_dim))
            in_dim = hidden_dim

        # Classifier MLP (mean + max pooling → 2× hidden_dim)
        self.classifier = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim * 2, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_dim, hidden_dim // 2),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_dim // 2, 1),
        )

        self.dropout = torch.nn.Dropout(dropout)

    def forward(self, x, edge_index, batch):
        # Message passing
        for conv, bn in zip(self.convs, self.bns):
            x = conv(x, edge_index)
            x = bn(x)
            x = torch.nn.functional.relu(x)
            x = self.dropout(x)

        # Global pooling: concat mean + max for richer graph representation
        x_mean = global_mean_pool(x, batch)
        x_max = global_max_pool(x, batch)
        x = torch.cat([x_mean, x_max], dim=1)

        # Classification
        return torch.nn.functional.sigmoid(self.classifier(x)).squeeze(-1)


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING
# ─────────────────────────────────────────────────────────────────────────────

def train_gnn(smiles_list: list, labels: list,
              epochs: int = 50,
              batch_size: int = 32,
              learning_rate: float = 1e-3,
              hidden_dim: int = 128) -> dict:
    """
    Train GNN on a list of SMILES strings.

    Args:
        smiles_list: list of SMILES strings
        labels: list of 0/1 labels (0=inactive, 1=active)
        epochs: training epochs
        batch_size: mini-batch size
        learning_rate: Adam learning rate
        hidden_dim: hidden layer size

    Returns:
        dict with model, metrics, training history
    """
    if not TORCH_AVAILABLE:
        return {"error": "PyTorch not installed. Run: pip install torch torch_geometric"}
    if not RDKIT_AVAILABLE:
        return {"error": "RDKit not installed. Run: pip install rdkit-pypi"}

    print("Building molecular graphs from SMILES...")
    graphs, valid_labels = [], []
    for smi, lbl in zip(smiles_list, labels):
        g = smiles_to_graph(smi)
        if g is not None:
            g.y = torch.tensor([float(lbl)], dtype=torch.float)
            graphs.append(g)
            valid_labels.append(lbl)

    if len(graphs) < 10:
        return {"error": f"Only {len(graphs)} valid graphs — need at least 10"}

    print(f"  Valid graphs: {len(graphs)} ({sum(valid_labels)} active, "
          f"{len(valid_labels)-sum(valid_labels)} inactive)")

    # Train/val split (80/20)
    split = int(0.8 * len(graphs))
    train_g = graphs[:split]
    val_g = graphs[split:]

    train_loader = DataLoader(train_g, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_g, batch_size=batch_size, shuffle=False)

    # Model, optimizer, loss
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DrugGNN(node_features=18, hidden_dim=hidden_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    # Class weights for imbalanced data
    pos_rate = sum(valid_labels) / len(valid_labels)
    pos_weight = torch.tensor([(1 - pos_rate) / max(pos_rate, 0.01)]).to(device)
    criterion = nn.BCELoss(weight=None)

    history = {"train_loss": [], "val_loss": [], "val_auc": []}
    best_val_auc = 0
    best_state = None

    print(f"Training GNN on {device} for {epochs} epochs...")
    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        total_loss = 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            pred = model(batch.x, batch.edge_index, batch.batch)
            loss = criterion(pred, batch.y.to(device))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()

        # Validate
        model.eval()
        val_preds, val_true = [], []
        val_loss = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                pred = model(batch.x, batch.edge_index, batch.batch)
                val_loss += criterion(pred, batch.y.to(device)).item()
                val_preds.extend(pred.cpu().numpy())
                val_true.extend(batch.y.cpu().numpy())

        try:
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score(val_true, val_preds) if len(set(val_true)) > 1 else 0.5
        except Exception:
            auc = 0.5

        avg_train = total_loss / len(train_loader)
        avg_val = val_loss / max(len(val_loader), 1)
        scheduler.step(avg_val)

        history["train_loss"].append(round(avg_train, 4))
        history["val_loss"].append(round(avg_val, 4))
        history["val_auc"].append(round(auc, 4))

        if auc > best_val_auc:
            best_val_auc = auc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if epoch % 10 == 0 or epoch == epochs:
            print(f"  Epoch {epoch:3d}: train_loss={avg_train:.4f} "
                  f"val_loss={avg_val:.4f} val_AUC={auc:.4f}")

    # Restore best model
    if best_state:
        model.load_state_dict(best_state)

    # Save
    torch.save({
        "model_state_dict": model.state_dict(),
        "model_config": {
            "node_features": 18,
            "hidden_dim": hidden_dim,
            "n_layers": 3,
        },
        "best_val_auc": best_val_auc,
        "trained_at": datetime.utcnow().isoformat(),
        "n_compounds": len(graphs),
    }, GNN_MODEL_PATH)

    print(f"\nGNN saved → {GNN_MODEL_PATH}")
    print(f"Best validation AUC: {best_val_auc:.4f}")

    return {
        "model": model,
        "best_val_auc": round(best_val_auc, 4),
        "n_compounds": len(graphs),
        "history": history,
        "trained_at": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

_gnn_model = None

def load_gnn_model():
    global _gnn_model
    if _gnn_model is not None:
        return _gnn_model
    if not os.path.exists(GNN_MODEL_PATH):
        return None
    try:
        checkpoint = torch.load(GNN_MODEL_PATH, map_location="cpu")
        cfg = checkpoint["model_config"]
        model = DrugGNN(**cfg)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        _gnn_model = model
        print(f"GNN loaded: AUC={checkpoint.get('best_val_auc','?')} "
              f"trained on {checkpoint.get('n_compounds','?')} compounds")
        return model
    except Exception as e:
        print(f"Failed to load GNN: {e}")
        return None


def predict_gnn(smiles: str) -> dict:
    """
    Run GNN prediction from a SMILES string.
    Falls back to Random Forest if GNN unavailable.
    """
    if not TORCH_AVAILABLE or not RDKIT_AVAILABLE:
        return {
            "error": "PyTorch or RDKit not available",
            "fallback": True,
            "model_used": "random_forest",
        }

    model = load_gnn_model()
    if model is None:
        return {
            "error": "GNN model not trained yet. Run train_gnn() first.",
            "fallback": True,
            "model_used": "random_forest",
        }

    graph = smiles_to_graph(smiles)
    if graph is None:
        return {"error": f"Could not parse SMILES: {smiles}"}

    with torch.no_grad():
        graph = graph.to("cpu")
        batch = torch.zeros(graph.num_nodes, dtype=torch.long)
        prob = float(model(graph.x, graph.edge_index, batch).item())

    return {
        "smiles": smiles,
        "gnn_probability": round(prob, 4),
        "model_used": "gnn",
        "model_type": "Graph Isomorphism Network (3-layer GINConv)",
        "n_atoms": graph.num_nodes,
        "n_bonds": graph.num_edges // 2,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ROUTES (add to api.py)
# ─────────────────────────────────────────────────────────────────────────────

GNN_ROUTES = '''
# ── ADD TO api.py ─────────────────────────────────────────────────────────────

from gnn_model import predict_gnn, train_gnn, load_gnn_model, GNN_MODEL_PATH
import os

@app.route("/predict-gnn", methods=["POST"])
def predict_with_gnn():
    """
    POST body: {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}
    Runs GNN model. Falls back to RF if GNN unavailable.
    """
    data = request.get_json()
    smiles = data.get("smiles", "").strip()
    if not smiles:
        return jsonify({"error": "smiles field required"}), 400

    result = predict_gnn(smiles)

    # If GNN available, also run RF for comparison
    if not result.get("fallback"):
        from smiles_pipeline import smiles_to_descriptors
        desc = smiles_to_descriptors(smiles)
        if desc["validity"]["valid"] and desc["model_features"]:
            features = [desc["model_features"][k] for k in
                        ["toxicity","bioavailability","solubility","binding","molecular_weight"]]
            rf_prob = models.predict_single(model, features)
            result["rf_probability"] = round(rf_prob, 4)
            result["ensemble_gnn_rf"] = round(
                result["gnn_probability"] * 0.6 + rf_prob * 0.4, 4
            )

    return jsonify(result)

@app.route("/gnn/status", methods=["GET"])
def gnn_status():
    import torch
    if os.path.exists(GNN_MODEL_PATH):
        checkpoint = torch.load(GNN_MODEL_PATH, map_location="cpu")
        return jsonify({
            "status": "trained",
            "best_val_auc": checkpoint.get("best_val_auc"),
            "n_compounds": checkpoint.get("n_compounds"),
            "trained_at": checkpoint.get("trained_at"),
        })
    return jsonify({"status": "not_trained", 
                    "message": "POST to /gnn/train with SMILES + labels to train"})

@app.route("/gnn/train", methods=["POST"])
def train_gnn_endpoint():
    """
    POST body: {"smiles_list": [...], "labels": [...], "epochs": 50}
    Or: {"use_chembl_dataset": true} to use existing chembl_dataset.csv
    """
    data = request.get_json()
    
    if data.get("use_chembl_dataset"):
        import pandas as pd
        if not os.path.exists("chembl_dataset.csv"):
            return jsonify({"error": "chembl_dataset.csv not found. Run ChEMBL import first."}), 404
        df = pd.read_csv("chembl_dataset.csv")
        smiles_list = df["smiles"].fillna("").tolist()
        labels = df["label"].tolist()
    else:
        smiles_list = data.get("smiles_list", [])
        labels = data.get("labels", [])
    
    if len(smiles_list) < 10:
        return jsonify({"error": "Need at least 10 compounds to train GNN"}), 400
    
    result = train_gnn(
        smiles_list, labels,
        epochs = data.get("epochs", 50),
        hidden_dim = data.get("hidden_dim", 128),
    )
    
    if result.get("error"):
        return jsonify(result), 500
    return jsonify({
        "status": "trained",
        "best_val_auc": result["best_val_auc"],
        "n_compounds": result["n_compounds"],
        "trained_at": result["trained_at"],
    })
'''


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST (no RDKit/PyTorch required — just tests the code path)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("GNN Model Status Check")
    print("=" * 40)
    print(f"  PyTorch available: {TORCH_AVAILABLE}")
    print(f"  RDKit available:   {RDKIT_AVAILABLE}")

    if TORCH_AVAILABLE:
        model = DrugGNN(node_features=18, hidden_dim=64, n_layers=3)
        n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"  GNN parameters:    {n_params:,}")
        print(f"  Architecture:      3× GINConv → Global Pool → MLP")

    if TORCH_AVAILABLE and RDKIT_AVAILABLE:
        test_smi = "CC(=O)Oc1ccccc1C(=O)O"   # Aspirin
        g = smiles_to_graph(test_smi)
        if g:
            print(f"  Test graph (Aspirin): {g.num_nodes} atoms, {g.num_edges//2} bonds")
        print("\nTo train: python gnn_model.py")
        print("Or use train_gnn(smiles_list, labels) in Python")
    else:
        print("\nInstall dependencies:")
        if not TORCH_AVAILABLE:
            print("  pip install torch torch_geometric")
        if not RDKIT_AVAILABLE:
            print("  pip install rdkit-pypi")
