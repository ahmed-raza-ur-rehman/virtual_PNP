"""Loss functions."""
from __future__ import annotations

import numpy as np


def mse_loss(pred: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean((pred - target) ** 2))


def mse_grad(pred: np.ndarray, target: np.ndarray) -> np.ndarray:
    return 2 * (pred - target) / pred.size


def mae_loss(pred: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean(np.abs(pred - target)))


def mae_grad(pred: np.ndarray, target: np.ndarray) -> np.ndarray:
    return np.sign(pred - target) / pred.size


def cross_entropy_loss(pred: np.ndarray, target: np.ndarray) -> float:
    eps = 1e-12
    pred = np.clip(pred, eps, 1 - eps)
    # target as class indices or one-hot
    if target.ndim == 1:
        N = pred.shape[0]
        return float(-np.mean(np.log(pred[np.arange(N), target.astype(int)])))
    return float(-np.mean(np.sum(target * np.log(pred), axis=-1)))


def cross_entropy_grad(pred: np.ndarray, target: np.ndarray) -> np.ndarray:
    eps = 1e-12
    pred = np.clip(pred, eps, 1 - eps)
    if target.ndim == 1:
        N = pred.shape[0]
        grad = pred.copy()
        grad[np.arange(N), target.astype(int)] -= 1
        return grad / N
    return (pred - target) / pred.shape[0]


def binary_cross_entropy(pred: np.ndarray, target: np.ndarray) -> float:
    eps = 1e-12
    pred = np.clip(pred, eps, 1 - eps)
    return float(-np.mean(target * np.log(pred) + (1 - target) * np.log(1 - pred)))


def binary_cross_entropy_grad(pred: np.ndarray, target: np.ndarray) -> np.ndarray:
    eps = 1e-12
    pred = np.clip(pred, eps, 1 - eps)
    return (-(target / pred) + (1 - target) / (1 - pred)) / pred.size


def huber_loss(pred: np.ndarray, target: np.ndarray, delta: float = 1.0) -> float:
    diff = np.abs(pred - target)
    quad = np.minimum(diff, delta)
    lin = diff - quad
    return float(np.mean(0.5 * quad ** 2 + delta * lin))


def huber_grad(pred: np.ndarray, target: np.ndarray, delta: float = 1.0) -> np.ndarray:
    diff = pred - target
    grad = np.where(np.abs(diff) <= delta, diff, delta * np.sign(diff))
    return grad / pred.size


def focal_loss(pred: np.ndarray, target: np.ndarray, gamma: float = 2.0, alpha: float = 0.25) -> float:
    eps = 1e-12
    pred = np.clip(pred, eps, 1 - eps)
    if target.ndim == 1:
        N = pred.shape[0]
        pt = pred[np.arange(N), target.astype(int)]
    else:
        pt = np.sum(pred * target, axis=-1)
    return float(-np.mean(alpha * (1 - pt) ** gamma * np.log(pt)))


def triplet_loss(anchor: np.ndarray, positive: np.ndarray, negative: np.ndarray, margin: float = 1.0) -> float:
    d_pos = np.sum((anchor - positive) ** 2, axis=-1)
    d_neg = np.sum((anchor - negative) ** 2, axis=-1)
    return float(np.mean(np.maximum(d_pos - d_neg + margin, 0)))


def contrastive_loss(y: np.ndarray, d: np.ndarray, margin: float = 1.0) -> float:
    # y=1 similar, y=0 dissimilar
    pos = y * d ** 2
    neg = (1 - y) * np.maximum(margin - d, 0) ** 2
    return float(np.mean(pos + neg))


def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    eps = 1e-12
    p = np.clip(p, eps, 1)
    q = np.clip(q, eps, 1)
    return float(np.sum(p * np.log(p / q)))


def get_loss(name: str):
    losses = {
        "mse": (mse_loss, mse_grad),
        "mae": (mae_loss, mae_grad),
        "cross_entropy": (cross_entropy_loss, cross_entropy_grad),
        "bce": (binary_cross_entropy, binary_cross_entropy_grad),
        "huber": (huber_loss, huber_grad),
    }
    return losses.get(name, (mse_loss, mse_grad))
