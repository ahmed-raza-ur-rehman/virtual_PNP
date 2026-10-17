"""End-to-end training pipeline."""
from __future__ import annotations

import numpy as np

from pnp.ml.training import accuracy, train_val_split
from pnp.models.orientation_cnn import SimpleCNN


def train(epochs: int = 5, lr: float = 0.01):
    # synthetic dataset
    rng = np.random.default_rng(0)
    X = rng.random((200, 32, 32))
    y = rng.integers(0, 4, 200)
    Xtr, _Xva, ytr, _yva = train_val_split(X, y)
    model = SimpleCNN()
    for e in range(epochs):
        # simple forward pass on a sample
        preds = [model.predict(x)[0] for x in Xtr[:20]]
        acc = accuracy(ytr[:20], preds)
        print(f"epoch {e+1}/{epochs} acc={acc:.3f}")
    return model


def export_model(model, path: str):
    import pickle
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"model exported to {path}")


if __name__ == "__main__":
    m = train(epochs=3)
    export_model(m, "orientation_cnn.pkl")
