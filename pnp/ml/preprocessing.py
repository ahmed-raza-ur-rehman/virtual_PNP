"""Data preprocessing utilities."""
from __future__ import annotations

import numpy as np


class StandardScaler:
    def __init__(self):
        self.mean_ = None
        self.scale_ = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        self.mean_ = X.mean(axis=0)
        self.scale_ = X.std(axis=0)
        self.scale_[self.scale_ == 0] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return (X - self.mean_) / self.scale_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return X * self.scale_ + self.mean_


class MinMaxScaler:
    def __init__(self, feature_range: tuple[float, float] = (0, 1)):
        self.feature_range = feature_range
        self.min_ = None
        self.scale_ = None
        self.data_min_ = None
        self.data_max_ = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        self.data_min_ = X.min(axis=0)
        self.data_max_ = X.max(axis=0)
        data_range = self.data_max_ - self.data_min_
        data_range[data_range == 0] = 1.0
        self.scale_ = (self.feature_range[1] - self.feature_range[0]) / data_range
        self.min_ = self.feature_range[0] - self.data_min_ * self.scale_
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return X * self.scale_ + self.min_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.min_) / self.scale_


class RobustScaler:
    def __init__(self):
        self.center_ = None
        self.scale_ = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        self.center_ = np.median(X, axis=0)
        q75 = np.percentile(X, 75, axis=0)
        q25 = np.percentile(X, 25, axis=0)
        self.scale_ = q75 - q25
        self.scale_[self.scale_ == 0] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return (X - self.center_) / self.scale_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)


class LabelEncoder:
    def __init__(self):
        self.classes_ = None

    def fit(self, y):
        self.classes_ = np.unique(y)
        return self

    def transform(self, y):
        return np.array([np.where(self.classes_ == val)[0][0] for val in y])

    def fit_transform(self, y):
        self.fit(y)
        return self.transform(y)

    def inverse_transform(self, y):
        return self.classes_[y]


class OneHotEncoder:
    def __init__(self):
        self.categories_ = None

    def fit(self, y):
        self.categories_ = np.unique(y)
        return self

    def transform(self, y):
        y = np.asarray(y)
        out = np.zeros((len(y), len(self.categories_)))
        for i, val in enumerate(y):
            idx = np.where(self.categories_ == val)[0]
            if len(idx) > 0:
                out[i, idx[0]] = 1
        return out

    def fit_transform(self, y):
        self.fit(y)
        return self.transform(y)


class PCA:
    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self.components_ = None
        self.mean_ = None
        self.explained_variance_ = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        self.mean_ = X.mean(axis=0)
        Xc = X - self.mean_
        cov = Xc.T @ Xc / (len(X) - 1)
        eigvals, eigvecs = np.linalg.eigh(cov)
        idx = np.argsort(eigvals)[::-1]
        eigvals = eigvals[idx]
        eigvecs = eigvecs[:, idx]
        self.components_ = eigvecs[:, :self.n_components].T
        self.explained_variance_ = eigvals[:self.n_components]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return (X - self.mean_) @ self.components_.T

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)


class TrainTestSplit:
    @staticmethod
    def split(X, y, test_size: float = 0.2, random_state: int | None = None, shuffle: bool = True):
        X = np.asarray(X); y = np.asarray(y)
        n = len(X)
        rng = np.random.default_rng(random_state)
        idx = np.arange(n)
        if shuffle:
            rng.shuffle(idx)
        n_test = int(n * test_size)
        test_idx = idx[:n_test]
        train_idx = idx[n_test:]
        return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def normalize_image(image: np.ndarray, mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)) -> np.ndarray:
    image = image.astype(np.float32) / 255.0
    mean = np.array(mean).reshape(1, 1, -1)
    std = np.array(std).reshape(1, 1, -1)
    return (image - mean) / std


def resize_image(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    from scipy.ndimage import zoom
    if image.ndim == 3:
        factors = (size[0] / image.shape[0], size[1] / image.shape[1], 1)
    else:
        factors = (size[0] / image.shape[0], size[1] / image.shape[1])
    return zoom(image, factors, order=1)


def pad_image(image: np.ndarray, padding: int, mode: str = "constant") -> np.ndarray:
    if image.ndim == 3:
        return np.pad(image, ((padding, padding), (padding, padding), (0, 0)), mode=mode)
    return np.pad(image, padding, mode=mode)
