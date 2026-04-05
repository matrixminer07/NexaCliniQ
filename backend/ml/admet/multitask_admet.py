from __future__ import annotations

from typing import Dict, Iterable, Optional

import torch
import torch.nn as nn

from backend.ml.gnn.molecular_gnn import MolecularGNN, infer_graph_dims


ADMET_TASKS = [
    "caco2",
    "hia",
    "bbb",
    "ppb",
    "cyp3a4",
    "cyp2d6",
    "cyp2c9",
    "half_life",
    "clearance",
    "herg",
    "hepatotoxicity",
    "ames",
]


class MultiTaskADMET(nn.Module):
    """Shared GNN encoder with task-specific prediction heads."""

    def __init__(self, hidden_dim: int = 128):
        super().__init__()
        dims = infer_graph_dims()
        self.shared_encoder = MolecularGNN(
            num_node_features=dims.node_dim,
            num_edge_features=dims.edge_dim,
            hidden_dim=hidden_dim,
            output_dim=hidden_dim,
        )
        self.task_heads = nn.ModuleDict({
            task: nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_dim // 2, 1),
            )
            for task in ADMET_TASKS
        })

    def forward(self, data, tasks: Optional[Iterable[str]] = None) -> Dict[str, torch.Tensor]:
        embedding = self.shared_encoder(data)
        selected = list(tasks) if tasks is not None else ADMET_TASKS
        return {task: self.task_heads[task](embedding).squeeze(-1) for task in selected}
