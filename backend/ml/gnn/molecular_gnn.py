from __future__ import annotations

from dataclasses import dataclass
from typing import List

import torch
import torch.nn as nn
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, global_mean_pool


ATOM_TYPES = [
    "C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "B", "Si", "Se", "other"
]
HYBRIDIZATION_TYPES = [
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
]
BOND_TYPES = [
    Chem.rdchem.BondType.SINGLE,
    Chem.rdchem.BondType.DOUBLE,
    Chem.rdchem.BondType.TRIPLE,
    Chem.rdchem.BondType.AROMATIC,
]


def _one_hot(value, choices: List) -> List[float]:
    return [1.0 if value == c else 0.0 for c in choices]


def _atom_features(atom: Chem.Atom) -> List[float]:
    symbol = atom.GetSymbol() if atom.GetSymbol() in ATOM_TYPES[:-1] else "other"
    atom_type = _one_hot(symbol, ATOM_TYPES)
    hybridization = _one_hot(atom.GetHybridization(), HYBRIDIZATION_TYPES)
    return atom_type + hybridization + [
        float(atom.GetFormalCharge()),
        float(atom.GetIsAromatic()),
        float(atom.GetDegree()),
        float(atom.GetTotalNumHs()),
    ]


def _bond_features(bond: Chem.Bond) -> List[float]:
    return _one_hot(bond.GetBondType(), BOND_TYPES) + [
        float(bond.GetIsConjugated()),
        float(bond.IsInRing()),
    ]


def _global_features(mol: Chem.Mol) -> torch.Tensor:
    return torch.tensor(
        [
            float(Descriptors.MolWt(mol)),
            float(rdMolDescriptors.CalcNumRings(mol)),
            float(rdMolDescriptors.CalcNumHBD(mol)),
            float(rdMolDescriptors.CalcNumHBA(mol)),
        ],
        dtype=torch.float,
    )


class MolecularGNN(nn.Module):
    """Graph Attention Network for molecular property prediction."""

    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        hidden_dim: int = 128,
        num_heads: int = 4,
        dropout: float = 0.2,
        output_dim: int = 1,
        global_dim: int = 4,
    ):
        super().__init__()
        self.gat1 = GATConv(num_node_features, hidden_dim, heads=num_heads, dropout=dropout, edge_dim=num_edge_features)
        self.gat2 = GATConv(hidden_dim * num_heads, hidden_dim, heads=num_heads, dropout=dropout, edge_dim=num_edge_features)
        self.gat3 = GATConv(hidden_dim * num_heads, hidden_dim, heads=1, concat=False, dropout=dropout, edge_dim=num_edge_features)

        self.norm1 = nn.LayerNorm(hidden_dim * num_heads)
        self.norm2 = nn.LayerNorm(hidden_dim * num_heads)
        self.norm3 = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)

        self.fc1 = nn.Linear(hidden_dim + global_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        self.activation = nn.ReLU()

    def encode(self, data: Data) -> torch.Tensor:
        x, edge_index, edge_attr = data.x, data.edge_index, data.edge_attr
        batch = data.batch
        x = self.dropout(self.activation(self.norm1(self.gat1(x, edge_index, edge_attr))))
        x = self.dropout(self.activation(self.norm2(self.gat2(x, edge_index, edge_attr))))
        x = self.dropout(self.activation(self.norm3(self.gat3(x, edge_index, edge_attr))))
        pooled = global_mean_pool(x, batch)
        return torch.cat([pooled, data.global_features], dim=1)

    def forward(self, data: Data) -> torch.Tensor:
        embedding = self.encode(data)
        hidden = self.dropout(self.activation(self.fc1(embedding)))
        return self.fc2(hidden)


def smiles_to_graph(smiles: str) -> Data:
    """Convert SMILES to a torch_geometric Data object."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    node_features = [_atom_features(atom) for atom in mol.GetAtoms()]
    edge_index = []
    edge_features = []
    for bond in mol.GetBonds():
        i = bond.GetBeginAtomIdx()
        j = bond.GetEndAtomIdx()
        bf = _bond_features(bond)
        edge_index.extend([[i, j], [j, i]])
        edge_features.extend([bf, bf])

    if not edge_index:
        edge_index = [[0, 0]]
        edge_features = [[0.0] * (len(BOND_TYPES) + 2)]

    data = Data(
        x=torch.tensor(node_features, dtype=torch.float),
        edge_index=torch.tensor(edge_index, dtype=torch.long).t().contiguous(),
        edge_attr=torch.tensor(edge_features, dtype=torch.float),
    )
    data.global_features = _global_features(mol).unsqueeze(0)
    return data


@dataclass
class MoleculeGraphSpec:
    node_dim: int
    edge_dim: int


def infer_graph_dims() -> MoleculeGraphSpec:
    probe = smiles_to_graph("CCO")
    return MoleculeGraphSpec(node_dim=probe.x.shape[1], edge_dim=probe.edge_attr.shape[1])
