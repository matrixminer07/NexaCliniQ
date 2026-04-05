from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.model_selection import train_test_split
from torch_geometric.loader import DataLoader

from backend.ml.gnn.molecular_gnn import MolecularGNN, infer_graph_dims, smiles_to_graph

try:
    import optuna
except Exception:
    optuna = None

try:
    import wandb
except Exception:
    wandb = None


@dataclass
class TrainConfig:
    lr: float = 1e-3
    hidden_dim: int = 128
    heads: int = 4
    dropout: float = 0.2
    batch_size: int = 32
    epochs: int = 50
    patience: int = 8
    output_path: str = "backend/ta_models/gnn_property.pt"


def build_dataset(smiles: List[str], y: List[float]):
    dataset = []
    for s, target in zip(smiles, y):
        try:
            d = smiles_to_graph(s)
            d.y = torch.tensor([target], dtype=torch.float)
            dataset.append(d)
        except Exception:
            continue
    return dataset


def run_epoch(model, loader, optimizer=None, device="cpu") -> float:
    train_mode = optimizer is not None
    model.train(train_mode)
    losses = []
    for batch in loader:
        batch = batch.to(device)
        pred = model(batch).squeeze(-1)
        loss = F.mse_loss(pred, batch.y.view(-1))
        if train_mode:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        losses.append(loss.item())
    return float(np.mean(losses)) if losses else 1e9


def train_once(dataset, config: TrainConfig, device: str = "cpu") -> Tuple[MolecularGNN, float]:
    train_data, valid_data = train_test_split(dataset, test_size=0.2, random_state=42)
    train_loader = DataLoader(train_data, batch_size=config.batch_size, shuffle=True)
    valid_loader = DataLoader(valid_data, batch_size=config.batch_size, shuffle=False)

    dims = infer_graph_dims()
    model = MolecularGNN(
        num_node_features=dims.node_dim,
        num_edge_features=dims.edge_dim,
        hidden_dim=config.hidden_dim,
        num_heads=config.heads,
        dropout=config.dropout,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.lr)

    best_loss = float("inf")
    wait = 0
    for epoch in range(config.epochs):
        train_loss = run_epoch(model, train_loader, optimizer, device)
        valid_loss = run_epoch(model, valid_loader, None, device)
        if wandb:
            wandb.log({"epoch": epoch, "train_loss": train_loss, "valid_loss": valid_loss})
        if valid_loss < best_loss:
            best_loss = valid_loss
            wait = 0
            torch.save(model.state_dict(), config.output_path)
        else:
            wait += 1
        if wait >= config.patience:
            break
    model.load_state_dict(torch.load(config.output_path, map_location=device))
    return model, best_loss


def tune_with_optuna(dataset, base_config: TrainConfig, trials: int = 10) -> TrainConfig:
    if not optuna:
        return base_config

    def objective(trial):
        cfg = TrainConfig(
            lr=trial.suggest_float("lr", 1e-4, 5e-3, log=True),
            hidden_dim=trial.suggest_categorical("hidden_dim", [64, 96, 128, 192]),
            heads=trial.suggest_categorical("heads", [2, 4, 8]),
            dropout=trial.suggest_float("dropout", 0.1, 0.4),
            batch_size=trial.suggest_categorical("batch_size", [16, 32, 64]),
            epochs=base_config.epochs,
            patience=base_config.patience,
            output_path=base_config.output_path,
        )
        _, loss = train_once(dataset, cfg)
        return loss

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=trials)
    p = study.best_params
    return TrainConfig(
        lr=p["lr"],
        hidden_dim=p["hidden_dim"],
        heads=p["heads"],
        dropout=p["dropout"],
        batch_size=p["batch_size"],
        epochs=base_config.epochs,
        patience=base_config.patience,
        output_path=base_config.output_path,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=0)
    args = parser.parse_args()

    os.makedirs("backend/ta_models", exist_ok=True)
    smiles = ["CCO", "CCN", "CCCl", "c1ccccc1", "CC(=O)O", "CCOC(=O)N"]
    targets = [0.12, 0.28, 0.51, 0.42, 0.18, 0.31]
    dataset = build_dataset(smiles, targets)

    cfg = TrainConfig()
    if args.trials > 0:
        cfg = tune_with_optuna(dataset, cfg, trials=args.trials)

    if wandb:
        wandb.init(project="pharmanexus-gnn", config=cfg.__dict__)
    _, best = train_once(dataset, cfg)
    print({"status": "ok", "best_valid_mse": best, "saved_to": cfg.output_path})


if __name__ == "__main__":
    main()
