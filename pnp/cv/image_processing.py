"""Image processing utilities."""
from __future__ import annotations

import numpy as np


class ImageFilter:
    @staticmethod
    def gaussian_blur(image: np.ndarray, sigma: float = 1.0, kernel_size: int = 5) -> np.ndarray:
        from scipy.ndimage import gaussian_filter
        if image.ndim == 3:
            out = np.zeros_like(image)
            for c in range(image.shape[2]):
                out[..., c] = gaussian_filter(image[..., c], sigma=sigma)
            return out.astype(image.dtype)
        return gaussian_filter(image, sigma=sigma).astype(image.dtype)

    @staticmethod
    def median_filter(image: np.ndarray, size: int = 3) -> np.ndarray:
        from scipy.ndimage import median_filter
        if image.ndim == 3:
            out = np.zeros_like(image)
            for c in range(image.shape[2]):
                out[..., c] = median_filter(image[..., c], size=size)
            return out.astype(image.dtype)
        return median_filter(image, size=size).astype(image.dtype)

    @staticmethod
    def bilateral_filter(image: np.ndarray, sigma_color: float = 75, sigma_space: float = 75) -> np.ndarray:
        # simplified: gaussian
        return ImageFilter.gaussian_blur(image, sigma=sigma_space/25.0)

    @staticmethod
    def sobel(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        gx = np.zeros_like(image)
        gy = np.zeros_like(image)
        gx[:, 1:-1] = image[:, 2:] - image[:, :-2]
        gy[1:-1, :] = image[2:, :] - image[:-2, :]
        mag = np.sqrt(gx**2 + gy**2)
        return mag.astype(np.uint8)

    @staticmethod
    def canny(image: np.ndarray, low: float = 50, high: float = 150) -> np.ndarray:
        mag = ImageFilter.sobel(image)
        # threshold
        out = np.zeros_like(mag, dtype=np.uint8)
        out[mag >= high] = 255
        # hysteresis
        from scipy.ndimage import binary_dilation
        strong = mag >= high
        weak = (mag >= low) & (mag < high)
        out2 = np.zeros_like(mag, dtype=np.uint8)
        out2[strong] = 255
        # connect weak to strong
        dilated = binary_dilation(strong, iterations=2)
        out2[weak & dilated] = 255
        return out2

    @staticmethod
    def morphological(image: np.ndarray, operation: str = "erode", kernel_size: int = 3) -> np.ndarray:
        from scipy.ndimage import binary_closing, binary_dilation, binary_erosion, binary_opening
        binary = image > 127
        if operation == "erode":
            out = binary_erosion(binary, iterations=1)
        elif operation == "dilate":
            out = binary_dilation(binary, iterations=1)
        elif operation == "open":
            out = binary_opening(binary, iterations=1)
        elif operation == "close":
            out = binary_closing(binary, iterations=1)
        else:
            out = binary
        return (out * 255).astype(np.uint8)

    @staticmethod
    def resize(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
        from scipy.ndimage import zoom
        if image.ndim == 3:
            factors = (size[0]/image.shape[0], size[1]/image.shape[1], 1)
        else:
            factors = (size[0]/image.shape[0], size[1]/image.shape[1])
        return zoom(image, factors, order=1).astype(image.dtype)

    @staticmethod
    def rotate(image: np.ndarray, angle: float) -> np.ndarray:
        from scipy.ndimage import rotate
        return rotate(image, angle, reshape=False, mode="nearest").astype(image.dtype)

    @staticmethod
    def flip(image: np.ndarray, axis: int = 1) -> np.ndarray:
        return np.flip(image, axis=axis).copy()

    @staticmethod
    def crop(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = bbox
        return image[y:y+h, x:x+w].copy()

    @staticmethod
    def normalize(image: np.ndarray, mean=0, std=1) -> np.ndarray:
        return (image.astype(float) - mean) / std

    @staticmethod
    def histogram_equalize(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            # equalize each channel
            out = np.zeros_like(image)
            for c in range(image.shape[2]):
                out[..., c] = ImageFilter._eq_channel(image[..., c])
            return out
        return ImageFilter._eq_channel(image)

    @staticmethod
    def _eq_channel(channel: np.ndarray) -> np.ndarray:
        hist, _bins = np.histogram(channel.flatten(), 256, [0, 256])
        cdf = hist.cumsum()
        cdf_min = cdf[cdf > 0].min() if np.any(cdf > 0) else 0
        cdf = (cdf - cdf_min) * 255 / (cdf.max() - cdf_min + 1e-9)
        return cdf[channel.astype(np.uint8)].astype(np.uint8)

    @staticmethod
    def threshold(image: np.ndarray, t: int) -> np.ndarray:
        if image.ndim == 3:
            image = image.mean(axis=2)
        return (image > t).astype(np.uint8) * 255

    @staticmethod
    def adaptive_threshold(image: np.ndarray, block_size: int = 11, C: int = 2) -> np.ndarray:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        h, w = image.shape
        out = np.zeros_like(image, dtype=np.uint8)
        half = block_size // 2
        for y in range(h):
            for x in range(w):
                y0 = max(0, y - half); y1 = min(h, y + half + 1)
                x0 = max(0, x - half); x1 = min(w, x + half + 1)
                local_mean = image[y0:y1, x0:x1].mean()
                out[y, x] = 255 if image[y, x] > local_mean - C else 0
        return out

    @staticmethod
    def find_contours(image: np.ndarray) -> list[np.ndarray]:
        # simplified: return bounding boxes of connected components
        from scipy import ndimage
        if image.ndim == 3:
            image = image.mean(axis=2)
        binary = image > 127
        labeled, n = ndimage.label(binary)
        contours = []
        for i in range(1, n + 1):
            ys, xs = np.where(labeled == i)
            if len(xs) > 0:
                contours.append(np.array(list(zip(xs, ys))))
        return contours

    @staticmethod
    def connected_components(image: np.ndarray) -> tuple[np.ndarray, int]:
        from scipy import ndimage
        if image.ndim == 3:
            image = image.mean(axis=2)
        binary = image > 127
        labeled, n = ndimage.label(binary)
        return labeled, n

    @staticmethod
    def hough_lines(image: np.ndarray, threshold: int = 100) -> list[tuple[float, float]]:
        # simplified: return empty
        return []

    @staticmethod
    def hough_circles(image: np.ndarray, min_radius: int = 10, max_radius: int = 50) -> list[tuple[int, int, int]]:
        return []
