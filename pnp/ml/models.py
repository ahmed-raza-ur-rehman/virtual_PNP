"""Neural network model containers."""
from __future__ import annotations

import numpy as np

from .layers import Layer


class Sequential:
    def __init__(self, *layers: Layer):
        self.layers = list(layers)
        self.training = True

    def add(self, layer: Layer):
        self.layers.append(layer)

    def forward(self, x: np.ndarray) -> np.ndarray:
        for layer in self.layers:
            layer.training = self.training
            x = layer.forward(x)
        return x

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return self.forward(x)

    def backward(self, grad: np.ndarray) -> np.ndarray:
        for layer in reversed(self.layers):
            grad = layer.backward(grad)
        return grad

    def params(self) -> list[np.ndarray]:
        out = []
        for layer in self.layers:
            out.extend(layer.params())
        return out

    def grads(self) -> list[np.ndarray]:
        out = []
        for layer in self.layers:
            out.extend(layer.grads())
        return out

    def train(self):
        self.training = True
        for layer in self.layers:
            layer.training = True

    def eval(self):
        self.training = False
        for layer in self.layers:
            layer.training = False

    def save(self, path: str):
        import pickle
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> Sequential:
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)

    def summary(self) -> str:
        lines = ["Model Summary"]
        total = 0
        for i, layer in enumerate(self.layers):
            params = sum(p.size for p in layer.params())
            total += params
            lines.append(f"  {i}: {type(layer).__name__} params={params}")
        lines.append(f"Total params: {total}")
        return "\n".join(lines)


class ModelCheckpoint:
    def __init__(self, path: str, monitor: str = "val_loss", mode: str = "min"):
        self.path = path
        self.monitor = monitor
        self.mode = mode
        self.best = None

    def update(self, metrics: dict[str, float], model: Sequential):
        val = metrics.get(self.monitor, 0.0)
        if self.best is None or (self.mode == "min" and val < self.best) or (self.mode == "max" and val > self.best):
            self.best = val
            model.save(self.path)
            return True
        return False


class EarlyStopping:
    def __init__(self, patience: int = 5, monitor: str = "val_loss", mode: str = "min"):
        self.patience = patience
        self.monitor = monitor
        self.mode = mode
        self.best = None
        self.counter = 0
        self.stop = False

    def update(self, metrics: dict[str, float]):
        val = metrics.get(self.monitor, 0.0)
        if self.best is None:
            self.best = val
            return False
        improved = (val < self.best) if self.mode == "min" else (val > self.best)
        if improved:
            self.best = val
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.stop = True
        return self.stop
