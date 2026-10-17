"""Regression algorithms."""
from __future__ import annotations

import numpy as np


class LinearRegression:
    def __init__(self, fit_intercept: bool = True, method: str = "lstsq"):
        self.fit_intercept = fit_intercept
        self.method = method
        self.coef_ = None
        self.intercept_ = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if self.fit_intercept:
            Xb = np.column_stack([np.ones(len(X)), X])
        else:
            Xb = X
        if self.method == "lstsq":
            sol = np.linalg.lstsq(Xb, y, rcond=None)[0]
        elif self.method == "normal":
            sol = np.linalg.solve(Xb.T @ Xb + 1e-9*np.eye(Xb.shape[1]), Xb.T @ y)
        else:
            sol = np.linalg.lstsq(Xb, y, rcond=None)[0]
        if self.fit_intercept:
            self.intercept_ = sol[0]
            self.coef_ = sol[1:]
        else:
            self.coef_ = sol
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return X @ self.coef_ + self.intercept_

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        pred = self.predict(X)
        ss_res = np.sum((y - pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        return 1 - ss_res / (ss_tot + 1e-9)


class RidgeRegression(LinearRegression):
    def __init__(self, alpha: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if self.fit_intercept:
            Xb = np.column_stack([np.ones(len(X)), X])
        else:
            Xb = X
        n_features = Xb.shape[1]
        A = Xb.T @ Xb + self.alpha * np.eye(n_features)
        sol = np.linalg.solve(A, Xb.T @ y)
        if self.fit_intercept:
            self.intercept_ = sol[0]
            self.coef_ = sol[1:]
        else:
            self.coef_ = sol
        return self


class LassoRegression(LinearRegression):
    def __init__(self, alpha: float = 1.0, max_iters: int = 1000, tol: float = 1e-4, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha
        self.max_iters = max_iters
        self.tol = tol

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        _, d = X.shape
        if self.fit_intercept:
            X_mean = X.mean(axis=0)
            y_mean = y.mean()
            Xc = X - X_mean
            yc = y - y_mean
        else:
            Xc = X; yc = y; X_mean = np.zeros(d); y_mean = 0
        coef = np.zeros(d)
        for _ in range(self.max_iters):
            coef_old = coef.copy()
            for j in range(d):
                r = yc - Xc @ coef + Xc[:, j] * coef[j]
                rho = Xc[:, j] @ r
                z = Xc[:, j] @ Xc[:, j]
                if z == 0:
                    continue
                soft = np.sign(rho) * max(abs(rho) - self.alpha, 0) / z
                coef[j] = soft
            if np.linalg.norm(coef - coef_old) < self.tol:
                break
        self.coef_ = coef
        if self.fit_intercept:
            self.intercept_ = y_mean - X_mean @ coef
        return self


class ElasticNet(LinearRegression):
    def __init__(self, alpha: float = 1.0, l1_ratio: float = 0.5, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X, y):
        # use coordinate descent with combined penalty
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        _, d = X.shape
        if self.fit_intercept:
            X_mean = X.mean(axis=0)
            y_mean = y.mean()
            Xc = X - X_mean
            yc = y - y_mean
        else:
            Xc = X; yc = y; X_mean = np.zeros(d); y_mean = 0
        coef = np.zeros(d)
        l1 = self.alpha * self.l1_ratio
        l2 = self.alpha * (1 - self.l1_ratio)
        for _ in range(1000):
            coef_old = coef.copy()
            for j in range(d):
                r = yc - Xc @ coef + Xc[:, j] * coef[j]
                rho = Xc[:, j] @ r
                z = Xc[:, j] @ Xc[:, j] + l2
                coef[j] = np.sign(rho) * max(abs(rho) - l1, 0) / z
            if np.linalg.norm(coef - coef_old) < 1e-4:
                break
        self.coef_ = coef
        if self.fit_intercept:
            self.intercept_ = y_mean - X_mean @ coef
        return self


class PolynomialRegression:
    def __init__(self, degree: int = 2, fit_intercept: bool = True):
        self.degree = degree
        self.fit_intercept = fit_intercept
        self.coef_ = None
        self.intercept_ = 0.0
        self._poly_features = None

    def _transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float).ravel() if X.ndim == 1 else np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        features = [np.ones(len(X))]
        for d in range(1, self.degree + 1):
            features.append(X[:, 0] ** d)
        return np.column_stack(features)

    def fit(self, X, y):
        Xp = self._transform(X)
        y = np.asarray(y, dtype=float)
        sol = np.linalg.lstsq(Xp, y, rcond=None)[0]
        self.intercept_ = sol[0]
        self.coef_ = sol[1:]
        return self

    def predict(self, X):
        Xp = self._transform(X)
        return Xp @ np.concatenate([[self.intercept_], self.coef_])


class LogisticRegression:
    def __init__(self, lr: float = 0.01, max_iters: int = 1000, fit_intercept: bool = True):
        self.lr = lr
        self.max_iters = max_iters
        self.fit_intercept = fit_intercept
        self.coef_ = None
        self.intercept_ = 0.0

    def _sigmoid(self, z):
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n, _ = X.shape
        if self.fit_intercept:
            Xb = np.column_stack([np.ones(n), X])
        else:
            Xb = X
        w = np.zeros(Xb.shape[1])
        for _ in range(self.max_iters):
            z = Xb @ w
            pred = self._sigmoid(z)
            grad = Xb.T @ (pred - y) / n
            w -= self.lr * grad
        if self.fit_intercept:
            self.intercept_ = w[0]
            self.coef_ = w[1:]
        else:
            self.coef_ = w
        return self

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        z = X @ self.coef_ + self.intercept_
        return self._sigmoid(z)

    def predict(self, X):
        return (self.predict_proba(X) >= 0.5).astype(int)


class SVR:
    def __init__(self, C: float = 1.0, epsilon: float = 0.1, kernel: str = "rbf", gamma: float = 0.1):
        self.C = C
        self.epsilon = epsilon
        self.kernel = kernel
        self.gamma = gamma
        self.support_vectors = None
        self.support_labels = None
        self.alpha = None

    def _kernel(self, X1, X2):
        if self.kernel == "linear":
            return X1 @ X2.T
        if self.kernel == "rbf":
            # gaussian
            sq = np.sum(X1**2, axis=1)[:, None] + np.sum(X2**2, axis=1)[None, :] - 2 * X1 @ X2.T
            return np.exp(-self.gamma * sq)
        return X1 @ X2.T

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        # simplified: store as support vectors
        self.support_vectors = X
        self.support_labels = y
        self.alpha = np.ones(len(X)) * self.C / len(X)
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        K = self._kernel(X, self.support_vectors)
        return K @ self.alpha + self.support_labels.mean()
