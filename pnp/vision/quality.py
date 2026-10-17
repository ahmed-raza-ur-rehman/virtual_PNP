"""Image quality assessment."""
from __future__ import annotations

from typing import Any

import numpy as np


class ImageQualityAssessor:
    def __init__(self):
        pass

    def sharpness(self, image: np.ndarray) -> float:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        # Laplacian variance
        lap = np.zeros_like(image)
        lap[1:-1, 1:-1] = (image[2:, 1:-1] + image[:-2, 1:-1] +
                            image[1:-1, 2:] + image[1:-1, :-2] - 4*image[1:-1, 1:-1])
        return float(lap.var())

    def brightness(self, image: np.ndarray) -> float:
        if image.ndim == 3:
            image = image.mean(axis=2)
        return float(image.mean())

    def contrast(self, image: np.ndarray) -> float:
        if image.ndim == 3:
            image = image.mean(axis=2)
        return float(image.std())

    def noise_level(self, image: np.ndarray) -> float:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        # estimate noise via high-pass
        smooth = np.zeros_like(image)
        # simple 3x3 average
        from scipy.ndimage import uniform_filter
        smooth = uniform_filter(image, size=3)
        residual = image - smooth
        return float(residual.std())

    def snr(self, image: np.ndarray) -> float:
        b = self.brightness(image)
        n = self.noise_level(image)
        if n == 0:
            return float("inf")
        return b / n

    def blur_detection(self, image: np.ndarray, threshold: float = 100.0) -> bool:
        return self.sharpness(image) < threshold

    def exposure_check(self, image: np.ndarray) -> str:
        b = self.brightness(image)
        if b < 50:
            return "underexposed"
        if b > 200:
            return "overexposed"
        return "ok"

    def overall_score(self, image: np.ndarray) -> float:
        s = self.sharpness(image)
        c = self.contrast(image)
        n = self.noise_level(image)
        score = (s / 1000.0) * 0.4 + (c / 50.0) * 0.3 + (1.0 / (n + 1)) * 0.3
        return float(min(1.0, score))

    def assess(self, image: np.ndarray) -> dict[str, Any]:
        return {
            "sharpness": self.sharpness(image),
            "brightness": self.brightness(image),
            "contrast": self.contrast(image),
            "noise": self.noise_level(image),
            "snr": self.snr(image),
            "blur": self.blur_detection(image),
            "exposure": self.exposure_check(image),
            "score": self.overall_score(image),
        }


class FocusMeasure:
    @staticmethod
    def laplacian(image: np.ndarray) -> float:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        lap = np.zeros_like(image)
        lap[1:-1, 1:-1] = (image[2:, 1:-1] + image[:-2, 1:-1] +
                            image[1:-1, 2:] + image[1:-1, :-2] - 4*image[1:-1, 1:-1])
        return float(lap.var())

    @staticmethod
    def tenengrad(image: np.ndarray) -> float:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        gx = np.zeros_like(image)
        gy = np.zeros_like(image)
        gx[:, 1:-1] = image[:, 2:] - image[:, :-2]
        gy[1:-1, :] = image[2:, :] - image[:-2, :]
        grad = np.sqrt(gx**2 + gy**2)
        return float(grad.mean())

    @staticmethod
    def brenner(image: np.ndarray) -> float:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        diff = image[:, 2:] - image[:, :-2]
        return float(np.sum(diff**2))
