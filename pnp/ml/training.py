"""Training loop and trainer."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .losses import get_loss
from .metrics import accuracy
from .models import EarlyStopping, ModelCheckpoint
from .optimizers import SGD


@dataclass
class TrainingHistory:
    train_loss: list[float] = field(default_factory=list)
    val_loss: list[float] = field(default_factory=list)
    train_acc: list[float] = field(default_factory=list)
    val_acc: list[float] = field(default_factory=list)
    lr: list[float] = field(default_factory=list)


class Trainer:
    def __init__(self, model, optimizer=None, loss: str = "cross_entropy", device: str = "cpu"):
        self.model = model
        self.optimizer = optimizer
        self.loss_name = loss
        self.loss_fn, self.loss_grad = get_loss(loss)
        self.device = device
        self.history = TrainingHistory()
        self.early_stopping = None
        self.checkpoint = None

    def set_early_stopping(self, patience: int = 5, monitor: str = "val_loss"):
        self.early_stopping = EarlyStopping(patience=patience, monitor=monitor)

    def set_checkpoint(self, path: str, monitor: str = "val_loss"):
        self.checkpoint = ModelCheckpoint(path=path, monitor=monitor)

    def train_step(self, x: np.ndarray, y: np.ndarray) -> float:
        # forward
        pred = self.model(x)
        loss = self.loss_fn(pred, y)
        # backward
        grad = self.loss_grad(pred, y)
        self.model.backward(grad)
        # update
        if self.optimizer is not None:
            # set grads
            params = self.model.params()
            grads = self.model.grads()
            self.optimizer.params = params
            self.optimizer.grads = grads
            self.optimizer.step()
            self.optimizer.zero_grad()
        return float(loss)

    def evaluate(self, x: np.ndarray, y: np.ndarray) -> dict[str, float]:
        pred = self.model(x)
        loss = self.loss_fn(pred, y)
        acc = accuracy(pred, y)
        return {"loss": float(loss), "accuracy": float(acc)}

    def fit(self, x_train: np.ndarray, y_train: np.ndarray, x_val: np.ndarray | None = None,
            y_val: np.ndarray | None = None, epochs: int = 10, batch_size: int = 32,
            shuffle: bool = True, verbose: bool = True) -> TrainingHistory:
        n = len(x_train)
        for epoch in range(epochs):
            # shuffle
            if shuffle:
                idx = np.random.permutation(n)
                x_train = x_train[idx]
                y_train = y_train[idx]
            # train
            epoch_losses = []
            for i in range(0, n, batch_size):
                xb = x_train[i:i+batch_size]
                yb = y_train[i:i+batch_size]
                loss = self.train_step(xb, yb)
                epoch_losses.append(loss)
            train_loss = float(np.mean(epoch_losses))
            train_pred = self.model(x_train)
            train_acc = accuracy(train_pred, y_train)
            self.history.train_loss.append(train_loss)
            self.history.train_acc.append(float(train_acc))
            # val
            if x_val is not None:
                val_metrics = self.evaluate(x_val, y_val)
                self.history.val_loss.append(val_metrics["loss"])
                self.history.val_acc.append(val_metrics["accuracy"])
                metrics = {"val_loss": val_metrics["loss"], "val_acc": val_metrics["accuracy"]}
                if self.checkpoint:
                    self.checkpoint.update(metrics, self.model)
                if self.early_stopping and self.early_stopping.update(metrics):
                        if verbose:
                            print(f"Early stopping at epoch {epoch}")
                        break
            else:
                self.history.val_loss.append(0.0)
                self.history.val_acc.append(0.0)
            if verbose:
                msg = f"Epoch {epoch+1}/{epochs} - loss: {train_loss:.4f} - acc: {train_acc:.4f}"
                if x_val is not None:
                    msg += f" - val_loss: {self.history.val_loss[-1]:.4f} - val_acc: {self.history.val_acc[-1]:.4f}"
                print(msg)
        return self.history

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model(x)

    def save(self, path: str):
        self.model.save(path)

    def load(self, path: str):
        from .models import Sequential
        self.model = Sequential.load(path)


class CrossValidator:
    def __init__(self, n_folds: int = 5):
        self.n_folds = n_folds

    def split(self, X: np.ndarray, y: np.ndarray):
        n = len(X)
        fold_size = n // self.n_folds
        indices = np.arange(n)
        np.random.shuffle(indices)
        for i in range(self.n_folds):
            val_idx = indices[i*fold_size:(i+1)*fold_size]
            train_idx = np.concatenate([indices[:i*fold_size], indices[(i+1)*fold_size:]])
            yield train_idx, val_idx

    def cross_validate(self, model_factory: Callable, X: np.ndarray, y: np.ndarray, epochs: int = 10, batch_size: int = 32) -> dict[str, float]:
        scores = []
        for train_idx, val_idx in self.split(X, y):
            model = model_factory()
            trainer = Trainer(model, optimizer=SGD(model.params(), lr=0.01), loss="cross_entropy")
            trainer.fit(X[train_idx], y[train_idx], X[val_idx], y[val_idx], epochs=epochs, batch_size=batch_size, verbose=False)
            metrics = trainer.evaluate(X[val_idx], y[val_idx])
            scores.append(metrics["accuracy"])
        return {"mean": float(np.mean(scores)), "std": float(np.std(scores)), "scores": scores}


class LearningRateFinder:
    def __init__(self, model, optimizer_factory, loss: str = "cross_entropy"):
        self.model = model
        self.optimizer_factory = optimizer_factory
        self.loss_name = loss

    def find(self, x: np.ndarray, y: np.ndarray, start_lr: float = 1e-7, end_lr: float = 10, num_iters: int = 100):
        lrs = np.geomspace(start_lr, end_lr, num_iters)
        losses = []
        for lr in lrs:
            opt = self.optimizer_factory(self.model.params(), lr=lr)
            trainer = Trainer(self.model, optimizer=opt, loss=self.loss_name)
            # single batch
            xb = x[:32]; yb = y[:32]
            loss = trainer.train_step(xb, yb)
            losses.append(loss)
        # find steepest descent
        best_idx = int(np.argmin(losses))
        return {"best_lr": float(lrs[best_idx]), "lrs": lrs.tolist(), "losses": losses}


def train_val_split(X, y, val_ratio=0.2, seed=0):
    import numpy as np
    X = np.asarray(X); y = np.asarray(y)
    n = len(X)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = int(n * val_ratio)
    val_idx = idx[:n_val]
    train_idx = idx[n_val:]
    return X[train_idx], X[val_idx], y[train_idx], y[val_idx]
