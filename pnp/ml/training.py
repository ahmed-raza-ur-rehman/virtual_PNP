"""Training utilities for orientation/defect models."""
from __future__ import annotations

import numpy as np


def train_val_split(X, y, val_ratio=0.2, seed=42):
    rng = np.random.default_rng(seed)
    idx = np.arange(len(X))
    rng.shuffle(idx)
    n_val = int(len(X) * val_ratio)
    val_idx = idx[:n_val]
    tr_idx = idx[n_val:]
    return X[tr_idx], X[val_idx], y[tr_idx], y[val_idx]


def accuracy(y_true, y_pred):
    return float(np.mean(np.asarray(y_true) == np.asarray(y_pred)))


def cross_entropy_loss(logits, labels):
    # logits: (N,C), labels: (N,)
    logits = logits - logits.max(axis=1, keepdims=True)
    logsum = np.log(np.exp(logits).sum(axis=1))
    nll = -logits[np.arange(len(labels)), labels] + logsum
    return float(nll.mean())
