"""Data augmentation for images."""
from __future__ import annotations

from typing import Any

import numpy as np


class ImageAugmentor:
    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def random_flip_horizontal(self, image: np.ndarray, p: float = 0.5) -> np.ndarray:
        if self.rng.random() < p:
            return np.flip(image, axis=1).copy()
        return image

    def random_flip_vertical(self, image: np.ndarray, p: float = 0.5) -> np.ndarray:
        if self.rng.random() < p:
            return np.flip(image, axis=0).copy()
        return image

    def random_rotation(self, image: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
        angle = self.rng.uniform(-max_angle, max_angle)
        # simplified: just return (real rotation needs scipy)
        from scipy.ndimage import rotate
        return rotate(image, angle, reshape=False, mode="nearest")

    def random_crop(self, image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
        h, w = image.shape[:2]
        ch, cw = size
        if ch > h or cw > w:
            return image
        y = self.rng.integers(0, h - ch + 1)
        x = self.rng.integers(0, w - cw + 1)
        return image[y:y+ch, x:x+cw].copy()

    def random_brightness(self, image: np.ndarray, factor_range: tuple[float, float] = (0.8, 1.2)) -> np.ndarray:
        factor = self.rng.uniform(*factor_range)
        out = image.astype(float) * factor
        return np.clip(out, 0, 255).astype(np.uint8)

    def random_contrast(self, image: np.ndarray, factor_range: tuple[float, float] = (0.8, 1.2)) -> np.ndarray:
        factor = self.rng.uniform(*factor_range)
        mean = image.mean()
        out = (image.astype(float) - mean) * factor + mean
        return np.clip(out, 0, 255).astype(np.uint8)

    def random_noise(self, image: np.ndarray, std: float = 10.0) -> np.ndarray:
        noise = self.rng.normal(0, std, image.shape)
        out = image.astype(float) + noise
        return np.clip(out, 0, 255).astype(np.uint8)

    def random_blur(self, image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        from scipy.ndimage import gaussian_filter
        sigma = self.rng.uniform(0.5, 2.0)
        if image.ndim == 3:
            out = np.zeros_like(image)
            for c in range(image.shape[2]):
                out[..., c] = gaussian_filter(image[..., c], sigma=sigma)
            return out.astype(np.uint8)
        return gaussian_filter(image, sigma=sigma).astype(np.uint8)

    def color_jitter(self, image: np.ndarray, brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1) -> np.ndarray:
        out = self.random_brightness(image, (1-brightness, 1+brightness))
        out = self.random_contrast(out, (1-contrast, 1+contrast))
        return out

    def normalize(self, image: np.ndarray, mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)) -> np.ndarray:
        image = image.astype(float) / 255.0
        mean = np.array(mean).reshape(1, 1, -1)
        std = np.array(std).reshape(1, 1, -1)
        return (image - mean) / std

    def to_tensor(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            return np.transpose(image, (2, 0, 1)).astype(np.float32)
        return image.astype(np.float32)

    def compose(self, transforms: list) -> Any:
        def apply(img):
            for t in transforms:
                img = t(img)
            return img
        return apply


class Mixup:
    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha

    def __call__(self, x1, y1, x2, y2):
        lam = np.random.beta(self.alpha, self.alpha)
        x = lam * x1 + (1 - lam) * x2
        y = lam * y1 + (1 - lam) * y2
        return x, y


class CutMix:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    def __call__(self, x1, y1, x2, y2):
        lam = np.random.beta(self.alpha, self.alpha)
        h, w = x1.shape[:2]
        cut_h = int(h * np.sqrt(1 - lam))
        cut_w = int(w * np.sqrt(1 - lam))
        cx = np.random.randint(w)
        cy = np.random.randint(h)
        x1a = max(0, cx - cut_w // 2); x1b = min(w, cx + cut_w // 2)
        y1a = max(0, cy - cut_h // 2); y1b = min(h, cy + cut_h // 2)
        x = x1.copy()
        x[y1a:y1b, x1a:x1b] = x2[y1a:y1b, x1a:x1b]
        lam = 1 - (x1b - x1a) * (y1b - y1a) / (h * w)
        y = lam * y1 + (1 - lam) * y2
        return x, y
