"""Lightweight CNN for component orientation classification (numpy-based)."""
import numpy as np


class SimpleCNN:
    def __init__(self, input_size=32, num_classes=4):
        self.input_size = input_size
        self.num_classes = num_classes
        rng = np.random.default_rng(42)
        # conv 3x3 -> 8 filters
        self.W1 = rng.normal(0, 0.1, (8, 1, 3, 3))
        self.b1 = np.zeros(8)
        # fc
        feat = (input_size - 2) // 2
        self.W2 = rng.normal(0, 0.1, (num_classes, 8 * feat * feat))
        self.b2 = np.zeros(num_classes)

    def _conv(self, x):
        # x: (1,H,W)
        H, W = x.shape[1], x.shape[2]
        out = np.zeros((8, H-2, W-2))
        for f in range(8):
            for i in range(H-2):
                for j in range(W-2):
                    out[f, i, j] = np.sum(x[:, i:i+3, j:j+3] * self.W1[f]) + self.b1[f]
        return np.maximum(out, 0)  # relu

    def _pool(self, x):
        # 2x2 max pool
        c, h, w = x.shape
        out = np.zeros((c, h//2, w//2))
        for ci in range(c):
            for i in range(0, h-1, 2):
                for j in range(0, w-1, 2):
                    out[ci, i//2, j//2] = x[ci, i:i+2, j:j+2].max()
        return out

    def forward(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        if x.ndim == 2:
            x = x[None, None, :, :]
        elif x.ndim == 3:
            x = x[None, :, :, :]
        conv = self._conv(x[0])
        pool = self._pool(conv)
        flat = pool.flatten()
        # resize weights if needed
        if flat.shape[0] != self.W2.shape[1]:
            # pad/truncate
            w = np.zeros(self.W2.shape[1])
            n = min(len(flat), len(w))
            w[:n] = flat[:n]
            flat = w
        logits = self.W2 @ flat + self.b2
        # softmax
        e = np.exp(logits - logits.max())
        return e / e.sum()

    def predict(self, x):
        p = self.forward(x)
        return int(np.argmax(p)), float(p.max())
