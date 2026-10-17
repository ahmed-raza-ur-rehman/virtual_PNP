"""Clustering algorithms."""
from __future__ import annotations

import numpy as np


class KMeans:
    def __init__(self, k: int = 3, max_iters: int = 100, tol: float = 1e-6):
        self.k = k
        self.max_iters = max_iters
        self.tol = tol
        self.centroids = None
        self.labels = None
        self.inertia = 0.0

    def fit(self, X: np.ndarray) -> KMeans:
        X = np.asarray(X, dtype=float)
        n = X.shape[0]
        rng = np.random.default_rng(0)
        idx = rng.choice(n, self.k, replace=False)
        self.centroids = X[idx].copy()
        for _ in range(self.max_iters):
            dists = np.linalg.norm(X[:, None, :] - self.centroids[None, :, :], axis=2)
            labels = np.argmin(dists, axis=1)
            new_centroids = np.array([X[labels == k].mean(axis=0) if np.any(labels == k) else self.centroids[k] for k in range(self.k)])
            if np.linalg.norm(new_centroids - self.centroids) < self.tol:
                self.centroids = new_centroids
                self.labels = labels
                break
            self.centroids = new_centroids
            self.labels = labels
        dists = np.linalg.norm(X[:, None, :] - self.centroids[None, :, :], axis=2)
        self.labels = np.argmin(dists, axis=1)
        self.inertia = float(np.sum((X - self.centroids[self.labels]) ** 2))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        dists = np.linalg.norm(X[:, None, :] - self.centroids[None, :, :], axis=2)
        return np.argmin(dists, axis=1)


class DBSCAN:
    def __init__(self, eps: float = 0.5, min_samples: int = 5):
        self.eps = eps
        self.min_samples = min_samples
        self.labels = None

    def fit(self, X: np.ndarray) -> DBSCAN:
        X = np.asarray(X, dtype=float)
        n = X.shape[0]
        labels = np.full(n, -1)
        visited = np.zeros(n, dtype=bool)
        cluster_id = 0
        for i in range(n):
            if visited[i]:
                continue
            visited[i] = True
            neighbors = self._region_query(X, i)
            if len(neighbors) < self.min_samples:
                labels[i] = -1  # noise
                continue
            labels[i] = cluster_id
            seeds = list(neighbors)
            while seeds:
                j = seeds.pop()
                if not visited[j]:
                    visited[j] = True
                    j_neighbors = self._region_query(X, j)
                    if len(j_neighbors) >= self.min_samples:
                        seeds.extend([x for x in j_neighbors if x not in seeds])
                if labels[j] == -1:
                    labels[j] = cluster_id
            cluster_id += 1
        self.labels = labels
        return self

    def _region_query(self, X, i):
        dists = np.linalg.norm(X - X[i], axis=1)
        return np.where(dists <= self.eps)[0]


class HierarchicalClustering:
    def __init__(self, n_clusters: int = 2, linkage: str = "single"):
        self.n_clusters = n_clusters
        self.linkage = linkage
        self.labels = None

    def fit(self, X: np.ndarray) -> HierarchicalClustering:
        X = np.asarray(X, dtype=float)
        n = X.shape[0]
        # distance matrix
        D = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
        np.fill_diagonal(D, float("inf"))
        clusters = [[i] for i in range(n)]
        while len(clusters) > self.n_clusters:
            # find closest pair
            best = (float("inf"), -1, -1)
            for i in range(len(clusters)):
                for j in range(i+1, len(clusters)):
                    d = self._cluster_dist(clusters[i], clusters[j], D)
                    if d < best[0]:
                        best = (d, i, j)
            _, i, j = best
            clusters[i] = clusters[i] + clusters[j]
            del clusters[j]
        labels = np.zeros(n, dtype=int)
        for ci, cl in enumerate(clusters):
            for idx in cl:
                labels[idx] = ci
        self.labels = labels
        return self

    def _cluster_dist(self, c1, c2, D):
        if self.linkage == "single":
            return min(D[i, j] for i in c1 for j in c2)
        if self.linkage == "complete":
            return max(D[i, j] for i in c1 for j in c2)
        # average
        return np.mean([D[i, j] for i in c1 for j in c2])


class GaussianMixture:
    def __init__(self, n_components: int = 3, max_iters: int = 100):
        self.n_components = n_components
        self.max_iters = max_iters
        self.weights = None
        self.means = None
        self.covs = None

    def fit(self, X: np.ndarray) -> GaussianMixture:
        X = np.asarray(X, dtype=float)
        n, d = X.shape
        rng = np.random.default_rng(0)
        self.weights = np.ones(self.n_components) / self.n_components
        self.means = X[rng.choice(n, self.n_components, replace=False)].copy()
        self.covs = [np.eye(d) for _ in range(self.n_components)]
        for _ in range(self.max_iters):
            # E-step
            resp = np.zeros((n, self.n_components))
            for k in range(self.n_components):
                diff = X - self.means[k]
                cov = self.covs[k]
                try:
                    inv = np.linalg.inv(cov)
                except np.linalg.LinAlgError:
                    inv = np.eye(d)
                det = np.linalg.det(cov)
                norm = 1.0 / (np.sqrt((2*np.pi)**d * abs(det)) + 1e-12)
                resp[:, k] = self.weights[k] * norm * np.exp(-0.5 * np.sum(diff @ inv * diff, axis=1))
            resp /= resp.sum(axis=1, keepdims=True) + 1e-12
            # M-step
            Nk = resp.sum(axis=0)
            self.weights = Nk / n
            for k in range(self.n_components):
                self.means[k] = (resp[:, k] @ X) / Nk[k]
                diff = X - self.means[k]
                self.covs[k] = (resp[:, k][:, None] * diff).T @ diff / Nk[k] + 1e-6 * np.eye(d)
        self.labels = np.argmax(resp, axis=1) if resp is not None else None
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        n = X.shape[0]
        resp = np.zeros((n, self.n_components))
        for k in range(self.n_components):
            diff = X - self.means[k]
            cov = self.covs[k]
            try:
                inv = np.linalg.inv(cov)
            except np.linalg.LinAlgError:
                inv = np.eye(X.shape[1])
            det = np.linalg.det(cov)
            norm = 1.0 / (np.sqrt((2*np.pi)**X.shape[1] * abs(det)) + 1e-12)
            resp[:, k] = self.weights[k] * norm * np.exp(-0.5 * np.sum(diff @ inv * diff, axis=1))
        return np.argmax(resp, axis=1)
