"""Neural network layers (NumPy-based)."""
from __future__ import annotations

import math

import numpy as np


class Layer:
    def __init__(self):
        self.weights = None
        self.bias = None
        self.grad_weights = None
        self.grad_bias = None
        self.input_cache = None
        self.training = True

    def forward(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def backward(self, grad: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def params(self) -> list[np.ndarray]:
        return [self.weights, self.bias] if self.weights is not None else []

    def grads(self) -> list[np.ndarray]:
        return [self.grad_weights, self.grad_bias] if self.grad_weights is not None else []


class Dense(Layer):
    def __init__(self, in_features: int, out_features: int, init: str = "he"):
        super().__init__()
        if init == "he":
            self.weights = np.random.randn(in_features, out_features) * math.sqrt(2.0 / in_features)
        elif init == "xavier":
            self.weights = np.random.randn(in_features, out_features) * math.sqrt(1.0 / in_features)
        else:
            self.weights = np.random.randn(in_features, out_features) * 0.01
        self.bias = np.zeros(out_features)
        self.grad_weights = np.zeros_like(self.weights)
        self.grad_bias = np.zeros_like(self.bias)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.input_cache = x
        return x @ self.weights + self.bias

    def backward(self, grad: np.ndarray) -> np.ndarray:
        x = self.input_cache
        self.grad_weights = x.T @ grad
        self.grad_bias = grad.sum(axis=0)
        return grad @ self.weights.T


class Conv2D(Layer):
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, stride: int = 1, padding: int = 1):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride
        self.padding = padding
        scale = math.sqrt(2.0 / (in_channels * kernel_size * kernel_size))
        self.weights = np.random.randn(out_channels, in_channels, kernel_size, kernel_size) * scale
        self.bias = np.zeros(out_channels)
        self.grad_weights = np.zeros_like(self.weights)
        self.grad_bias = np.zeros_like(self.bias)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.input_cache = x
        N, _C, _H, _W = x.shape
        KH, KW = self.kernel_size, self.kernel_size
        # pad
        if self.padding > 0:
            xpad = np.pad(x, ((0,0),(0,0),(self.padding,self.padding),(self.padding,self.padding)), mode="constant")
        else:
            xpad = x
        OH = (xpad.shape[2] - KH) // self.stride + 1
        OW = (xpad.shape[3] - KW) // self.stride + 1
        out = np.zeros((N, self.out_channels, OH, OW))
        for n in range(N):
            for oc in range(self.out_channels):
                for oh in range(OH):
                    for ow in range(OW):
                        h0 = oh * self.stride
                        w0 = ow * self.stride
                        region = xpad[n, :, h0:h0+KH, w0:w0+KW]
                        out[n, oc, oh, ow] = np.sum(region * self.weights[oc]) + self.bias[oc]
        return out

    def backward(self, grad: np.ndarray) -> np.ndarray:
        # simplified: return zeros (placeholder for full impl)
        x = self.input_cache
        return np.zeros_like(x)


class BatchNorm(Layer):
    def __init__(self, num_features: int, eps: float = 1e-5, momentum: float = 0.1):
        super().__init__()
        self.num_features = num_features
        self.eps = eps
        self.momentum = momentum
        self.gamma = np.ones(num_features)
        self.beta = np.zeros(num_features)
        self.running_mean = np.zeros(num_features)
        self.running_var = np.ones(num_features)
        self.grad_gamma = np.zeros(num_features)
        self.grad_beta = np.zeros(num_features)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.input_cache = x
        if x.ndim == 2:
            mean = x.mean(axis=0)
            var = x.var(axis=0)
            self.running_mean = (1 - self.momentum) * self.running_mean + self.momentum * mean
            self.running_var = (1 - self.momentum) * self.running_var + self.momentum * var
            x_norm = (x - mean) / np.sqrt(var + self.eps)
            return self.gamma * x_norm + self.beta
        # 4D
        mean = x.mean(axis=(0, 2, 3))
        var = x.var(axis=(0, 2, 3))
        self.running_mean = (1 - self.momentum) * self.running_mean + self.momentum * mean
        self.running_var = (1 - self.momentum) * self.running_var + self.momentum * var
        x_norm = (x - mean[None, :, None, None]) / np.sqrt(var[None, :, None, None] + self.eps)
        return self.gamma[None, :, None, None] * x_norm + self.beta[None, :, None, None]

    def backward(self, grad: np.ndarray) -> np.ndarray:
        return grad  # simplified


class Dropout(Layer):
    def __init__(self, p: float = 0.5):
        self.p = p
        self.mask = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        if not self.training:
            return x
        self.mask = (np.random.rand(*x.shape) > self.p).astype(float) / (1 - self.p)
        return x * self.mask

    def backward(self, grad: np.ndarray) -> np.ndarray:
        if self.mask is None:
            return grad
        return grad * self.mask

    def params(self):
        return []


class Flatten(Layer):
    def __init__(self):
        self.shape = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.shape = x.shape
        return x.reshape(x.shape[0], -1)

    def backward(self, grad: np.ndarray) -> np.ndarray:
        return grad.reshape(self.shape)


class MaxPool2D(Layer):
    def __init__(self, kernel_size: int = 2, stride: int = 2):
        self.kernel_size = kernel_size
        self.stride = stride
        self.cache = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        N, C, H, W = x.shape
        KH = KW = self.kernel_size
        OH = (H - KH) // self.stride + 1
        OW = (W - KW) // self.stride + 1
        out = np.zeros((N, C, OH, OW))
        self.cache = (x.shape, np.zeros((N, C, OH, OW, 2), dtype=int))
        for n in range(N):
            for c in range(C):
                for oh in range(OH):
                    for ow in range(OW):
                        h0 = oh * self.stride
                        w0 = ow * self.stride
                        region = x[n, c, h0:h0+KH, w0:w0+KW]
                        idx = np.unravel_index(np.argmax(region), region.shape)
                        out[n, c, oh, ow] = region[idx]
                        self.cache[1][n, c, oh, ow] = (h0 + idx[0], w0 + idx[1])
        return out

    def backward(self, grad: np.ndarray) -> np.ndarray:
        N, C, H, W = self.cache[0]
        dx = np.zeros((N, C, H, W))
        OH, OW = grad.shape[2], grad.shape[3]
        for n in range(N):
            for c in range(C):
                for oh in range(OH):
                    for ow in range(OW):
                        h, w = self.cache[1][n, c, oh, ow]
                        dx[n, c, h, w] += grad[n, c, oh, ow]
        return dx

    def params(self):
        return []


class AvgPool2D(Layer):
    def __init__(self, kernel_size: int = 2, stride: int = 2):
        self.kernel_size = kernel_size
        self.stride = stride

    def forward(self, x: np.ndarray) -> np.ndarray:
        N, C, H, W = x.shape
        KH = KW = self.kernel_size
        OH = (H - KH) // self.stride + 1
        OW = (W - KW) // self.stride + 1
        out = np.zeros((N, C, OH, OW))
        for n in range(N):
            for c in range(C):
                for oh in range(OH):
                    for ow in range(OW):
                        h0 = oh * self.stride
                        w0 = ow * self.stride
                        out[n, c, oh, ow] = x[n, c, h0:h0+KH, w0:w0+KW].mean()
        return out

    def backward(self, grad: np.ndarray) -> np.ndarray:
        return grad  # simplified

    def params(self):
        return []


class Activation(Layer):
    def __init__(self, name: str = "relu"):
        self.name = name
        self.cache = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.cache = x
        if self.name == "relu":
            return np.maximum(0, x)
        if self.name == "sigmoid":
            return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
        if self.name == "tanh":
            return np.tanh(x)
        if self.name == "leaky_relu":
            return np.where(x > 0, x, 0.01 * x)
        if self.name == "gelu":
            return 0.5 * x * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * x**3)))
        if self.name == "softmax":
            e = np.exp(x - x.max(axis=-1, keepdims=True))
            return e / e.sum(axis=-1, keepdims=True)
        return x

    def backward(self, grad: np.ndarray) -> np.ndarray:
        x = self.cache
        if self.name == "relu":
            return grad * (x > 0)
        if self.name == "sigmoid":
            s = 1 / (1 + np.exp(-np.clip(x, -500, 500)))
            return grad * s * (1 - s)
        if self.name == "tanh":
            return grad * (1 - np.tanh(x) ** 2)
        if self.name == "leaky_relu":
            return grad * np.where(x > 0, 1, 0.01)
        if self.name == "gelu":
            return grad  # simplified
        if self.name == "softmax":
            return grad  # simplified
        return grad

    def params(self):
        return []
