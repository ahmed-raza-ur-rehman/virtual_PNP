"""Inference engine and model serving."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class InferenceResult:
    output: Any
    latency_ms: float
    model_name: str
    batch_size: int = 1


class InferenceEngine:
    def __init__(self, model: Any, device: str = "cpu"):
        self.model = model
        self.device = device
        self.warmup_done = False
        self.stats = {"calls": 0, "total_latency": 0.0, "max_latency": 0.0}

    def warmup(self, input_shape: tuple, n: int = 5):
        dummy = np.zeros(input_shape, dtype=np.float32)
        for _ in range(n):
            self.predict(dummy)
        self.warmup_done = True

    def predict(self, x: np.ndarray) -> InferenceResult:
        t0 = time.time()
        if hasattr(self.model, "eval"):
            self.model.eval()
        out = self.model(x) if callable(self.model) else x
        latency = (time.time() - t0) * 1000
        self.stats["calls"] += 1
        self.stats["total_latency"] += latency
        self.stats["max_latency"] = max(self.stats["max_latency"], latency)
        return InferenceResult(output=out, latency_ms=latency, model_name=getattr(self.model, "name", "model"), batch_size=x.shape[0] if hasattr(x, "shape") else 1)

    def predict_batch(self, xs: list[np.ndarray]) -> list[InferenceResult]:
        return [self.predict(x) for x in xs]

    def get_stats(self) -> dict[str, Any]:
        calls = self.stats["calls"]
        avg = self.stats["total_latency"] / calls if calls else 0.0
        return {"calls": calls, "avg_latency_ms": avg, "max_latency_ms": self.stats["max_latency"]}

    def benchmark(self, input_shape: tuple, n: int = 100) -> dict[str, Any]:
        dummy = np.zeros(input_shape, dtype=np.float32)
        latencies = []
        for _ in range(n):
            r = self.predict(dummy)
            latencies.append(r.latency_ms)
        latencies = np.array(latencies)
        return {
            "n": n,
            "mean_ms": float(latencies.mean()),
            "std_ms": float(latencies.std()),
            "min_ms": float(latencies.min()),
            "max_ms": float(latencies.max()),
            "p50_ms": float(np.percentile(latencies, 50)),
            "p95_ms": float(np.percentile(latencies, 95)),
            "p99_ms": float(np.percentile(latencies, 99)),
            "throughput_fps": float(1000.0 / latencies.mean()) if latencies.mean() > 0 else 0.0,
        }


class ModelOptimizer:
    """Post-training optimization: quantization, pruning."""
    @staticmethod
    def quantize_weights(weights: np.ndarray, bits: int = 8) -> tuple[np.ndarray, float, float]:
        w_min = weights.min()
        w_max = weights.max()
        scale = (w_max - w_min) / (2 ** bits - 1)
        round(-w_min / scale)
        q = np.clip(np.round((weights - w_min) / scale), 0, 2 ** bits - 1).astype(np.uint8)
        return q, float(scale), float(w_min)

    @staticmethod
    def dequantize(q: np.ndarray, scale: float, zero_point_offset: float) -> np.ndarray:
        return q.astype(float) * scale + zero_point_offset

    @staticmethod
    def prune_weights(weights: np.ndarray, sparsity: float = 0.5) -> np.ndarray:
        flat = np.abs(weights).flatten()
        threshold = np.percentile(flat, sparsity * 100)
        mask = np.abs(weights) >= threshold
        return weights * mask

    @staticmethod
    def magnitude_prune(model: Any, sparsity: float = 0.5):
        for p in model.params():
            p[:] = ModelOptimizer.prune_weights(p, sparsity)


class TensorRTExporter:
    @staticmethod
    def export_onnx(model: Any, path: str, input_shape: tuple):
        # placeholder
        with open(path, "w") as f:
            f.write("onnx placeholder")

    @staticmethod
    def export_torchscript(model: Any, path: str):
        with open(path, "w") as f:
            f.write("torchscript placeholder")
