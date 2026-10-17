"""Model evaluation."""
from __future__ import annotations

from pnp.ml.training import accuracy


def evaluate(model, X, y):
    preds = [model.predict(x)[0] for x in X]
    return {"accuracy": accuracy(y, preds), "n": len(y)}
