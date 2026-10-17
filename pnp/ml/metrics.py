"""Evaluation metrics for ML."""
from __future__ import annotations

import numpy as np


def accuracy(pred: np.ndarray, target: np.ndarray) -> float:
    if pred.ndim > 1:
        pred = np.argmax(pred, axis=-1)
    if target.ndim > 1:
        target = np.argmax(target, axis=-1)
    return float(np.mean(pred == target))


def precision(pred: np.ndarray, target: np.ndarray, average: str = "macro") -> float:
    if pred.ndim > 1:
        pred = np.argmax(pred, axis=-1)
    if target.ndim > 1:
        target = np.argmax(target, axis=-1)
    classes = np.unique(np.concatenate([pred, target]))
    precisions = []
    for c in classes:
        tp = np.sum((pred == c) & (target == c))
        fp = np.sum((pred == c) & (target != c))
        precisions.append(tp / (tp + fp + 1e-12))
    if average == "macro":
        return float(np.mean(precisions))
    if average == "micro":
        tp = np.sum(pred == target)
        return float(tp / len(pred))
    return precisions


def recall(pred: np.ndarray, target: np.ndarray, average: str = "macro") -> float:
    if pred.ndim > 1:
        pred = np.argmax(pred, axis=-1)
    if target.ndim > 1:
        target = np.argmax(target, axis=-1)
    classes = np.unique(np.concatenate([pred, target]))
    recalls = []
    for c in classes:
        tp = np.sum((pred == c) & (target == c))
        fn = np.sum((pred != c) & (target == c))
        recalls.append(tp / (tp + fn + 1e-12))
    if average == "macro":
        return float(np.mean(recalls))
    if average == "micro":
        tp = np.sum(pred == target)
        return float(tp / len(target))
    return recalls


def f1_score(pred: np.ndarray, target: np.ndarray, average: str = "macro") -> float:
    p = precision(pred, target, average)
    r = recall(pred, target, average)
    if isinstance(p, list):
        return [2 * pi * ri / (pi + ri + 1e-12) for pi, ri in zip(p, r)]
    return float(2 * p * r / (p + r + 1e-12))


def confusion_matrix(pred: np.ndarray, target: np.ndarray, num_classes: int | None = None) -> np.ndarray:
    if pred.ndim > 1:
        pred = np.argmax(pred, axis=-1)
    if target.ndim > 1:
        target = np.argmax(target, axis=-1)
    if num_classes is None:
        num_classes = int(max(pred.max(), target.max())) + 1
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for p, t in zip(pred, target):
        cm[t, p] += 1
    return cm


def iou(pred: np.ndarray, target: np.ndarray) -> float:
    inter = np.logical_and(pred, target).sum()
    union = np.logical_or(pred, target).sum()
    if union == 0:
        return 1.0
    return float(inter / union)


def dice_coefficient(pred: np.ndarray, target: np.ndarray) -> float:
    inter = np.logical_and(pred, target).sum()
    return float(2 * inter / (pred.sum() + target.sum() + 1e-12))


def psnr(pred: np.ndarray, target: np.ndarray) -> float:
    mse = np.mean((pred.astype(float) - target.astype(float)) ** 2)
    if mse == 0:
        return float("inf")
    return float(20 * np.log10(255.0 / np.sqrt(mse)))


def ssim(pred: np.ndarray, target: np.ndarray) -> float:
    # simplified
    mu_x = pred.mean(); mu_y = target.mean()
    sigma_x = pred.std(); sigma_y = target.std()
    sigma_xy = np.mean((pred - mu_x) * (target - mu_y))
    c1, c2 = (0.01*255)**2, (0.03*255)**2
    return float(((2*mu_x*mu_y + c1)*(2*sigma_xy + c2)) / ((mu_x**2 + mu_y**2 + c1)*(sigma_x**2 + sigma_y**2 + c2)))


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    # simplified trapezoidal
    order = np.argsort(scores)[::-1]
    labels = labels[order]
    tp = 0; fp = 0
    tps = [0]; fps = [0]
    n_pos = labels.sum(); n_neg = len(labels) - n_pos
    for l in labels:
        if l == 1:
            tp += 1
        else:
            fp += 1
        tps.append(tp); fps.append(fp)
    tps = np.array(tps) / max(n_pos, 1)
    fps = np.array(fps) / max(n_neg, 1)
    return float(np.trapz(tps, fps))


def mean_average_precision(predictions: list, ground_truths: list, iou_threshold: float = 0.5) -> float:
    return 0.5  # placeholder
