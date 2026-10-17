"""Optimizers for neural networks."""
from __future__ import annotations

import math

import numpy as np


class Optimizer:
    def __init__(self, params: list[np.ndarray], lr: float = 0.01):
        self.params = params
        self.lr = lr
        self.grads: list[np.ndarray] = [np.zeros_like(p) for p in params]

    def zero_grad(self):
        for g in self.grads:
            g[:] = 0

    def step(self):
        raise NotImplementedError


class SGD(Optimizer):
    def __init__(self, params, lr=0.01, momentum=0.0, weight_decay=0.0, nesterov=False):
        super().__init__(params, lr)
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.nesterov = nesterov
        self.velocities = [np.zeros_like(p) for p in params]

    def step(self):
        for i, p in enumerate(self.params):
            g = self.grads[i]
            if self.weight_decay > 0:
                g = g + self.weight_decay * p
            self.velocities[i] = self.momentum * self.velocities[i] + g
            if self.nesterov:
                p -= self.lr * (g + self.momentum * self.velocities[i])
            else:
                p -= self.lr * self.velocities[i]


class Adam(Optimizer):
    def __init__(self, params, lr=0.001, beta1=0.9, beta2=0.999, eps=1e-8, weight_decay=0.0):
        super().__init__(params, lr)
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.weight_decay = weight_decay
        self.m = [np.zeros_like(p) for p in params]
        self.v = [np.zeros_like(p) for p in params]
        self.t = 0

    def step(self):
        self.t += 1
        for i, p in enumerate(self.params):
            g = self.grads[i]
            if self.weight_decay > 0:
                g = g + self.weight_decay * p
            self.m[i] = self.beta1 * self.m[i] + (1 - self.beta1) * g
            self.v[i] = self.beta2 * self.v[i] + (1 - self.beta2) * (g * g)
            m_hat = self.m[i] / (1 - self.beta1 ** self.t)
            v_hat = self.v[i] / (1 - self.beta2 ** self.t)
            p -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


class AdamW(Optimizer):
    def __init__(self, params, lr=0.001, beta1=0.9, beta2=0.999, eps=1e-8, weight_decay=0.01):
        super().__init__(params, lr)
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.weight_decay = weight_decay
        self.m = [np.zeros_like(p) for p in params]
        self.v = [np.zeros_like(p) for p in params]
        self.t = 0

    def step(self):
        self.t += 1
        for i, p in enumerate(self.params):
            g = self.grads[i]
            self.m[i] = self.beta1 * self.m[i] + (1 - self.beta1) * g
            self.v[i] = self.beta2 * self.v[i] + (1 - self.beta2) * (g * g)
            m_hat = self.m[i] / (1 - self.beta1 ** self.t)
            v_hat = self.v[i] / (1 - self.beta2 ** self.t)
            p -= self.lr * (m_hat / (np.sqrt(v_hat) + self.eps) + self.weight_decay * p)


class RMSprop(Optimizer):
    def __init__(self, params, lr=0.001, rho=0.9, eps=1e-8, weight_decay=0.0):
        super().__init__(params, lr)
        self.rho = rho
        self.eps = eps
        self.weight_decay = weight_decay
        self.sq = [np.zeros_like(p) for p in params]

    def step(self):
        for i, p in enumerate(self.params):
            g = self.grads[i]
            if self.weight_decay > 0:
                g = g + self.weight_decay * p
            self.sq[i] = self.rho * self.sq[i] + (1 - self.rho) * (g * g)
            p -= self.lr * g / (np.sqrt(self.sq[i]) + self.eps)


class Adagrad(Optimizer):
    def __init__(self, params, lr=0.01, eps=1e-8):
        super().__init__(params, lr)
        self.eps = eps
        self.acc = [np.zeros_like(p) for p in params]

    def step(self):
        for i, p in enumerate(self.params):
            g = self.grads[i]
            self.acc[i] += g * g
            p -= self.lr * g / (np.sqrt(self.acc[i]) + self.eps)


class LearningRateScheduler:
    def __init__(self, optimizer: Optimizer, mode: str = "step", **kwargs):
        self.optimizer = optimizer
        self.mode = mode
        self.kwargs = kwargs
        self.base_lr = optimizer.lr
        self.epoch = 0

    def step_epoch(self):
        self.epoch += 1
        if self.mode == "step":
            step_size = self.kwargs.get("step_size", 10)
            gamma = self.kwargs.get("gamma", 0.1)
            if self.epoch % step_size == 0:
                self.optimizer.lr *= gamma
        elif self.mode == "cosine":
            total = self.kwargs.get("total_epochs", 100)
            self.optimizer.lr = self.base_lr * 0.5 * (1 + math.cos(math.pi * self.epoch / total))
        elif self.mode == "warmup":
            warmup = self.kwargs.get("warmup_epochs", 5)
            if self.epoch < warmup:
                self.optimizer.lr = self.base_lr * (self.epoch + 1) / warmup
        elif self.mode == "exponential":
            gamma = self.kwargs.get("gamma", 0.95)
            self.optimizer.lr = self.base_lr * (gamma ** self.epoch)

    def get_lr(self) -> float:
        return self.optimizer.lr
