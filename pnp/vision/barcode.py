"""Barcode and QR code detection/decoding."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Barcode:
    type: str
    data: str
    bbox: tuple[int, int, int, int]
    confidence: float = 1.0


class BarcodeDetector:
    def __init__(self):
        self.supported = ["EAN13", "EAN8", "UPCA", "UPCE", "CODE128", "CODE39", "QR", "DATAMATRIX"]

    def detect(self, image: np.ndarray) -> list[Barcode]:
        # simplified: detect horizontal line patterns
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(np.uint8)
        h, _w = image.shape
        results = []
        # scan rows
        for y in range(0, h, 5):
            row = image[y, :]
            # find transitions
            transitions = np.where(np.diff(row.astype(int)) != 0)[0]
            if len(transitions) >= 20:
                x0 = int(transitions[0])
                x1 = int(transitions[-1])
                if x1 - x0 > 50:
                    results.append(Barcode(type="CODE128", data="", bbox=(x0, y, x1 - x0, 10), confidence=0.5))
        # deduplicate
        uniq = []
        for r in results:
            if not uniq or abs(r.bbox[1] - uniq[-1].bbox[1]) > 10:
                uniq.append(r)
        return uniq[:10]

    def decode_ean13(self, bars: list[int]) -> str:
        # simplified
        return "0" * 13

    def decode_qr(self, image: np.ndarray) -> str:
        return ""


class QRCodeGenerator:
    def __init__(self, version: int = 1, error_correction: str = "M"):
        self.version = version
        self.error_correction = error_correction

    def generate(self, data: str) -> np.ndarray:
        size = 21 + 4 * (self.version - 1)
        img = np.ones((size, size), dtype=np.uint8) * 255
        # finder patterns
        for (r, c) in [(0, 0), (0, size-7), (size-7, 0)]:
            img[r:r+7, c:c+7] = 0
            img[r+1:r+6, c+1:c+6] = 255
            img[r+2:r+5, c+2:c+5] = 0
        # timing patterns
        for i in range(8, size-8):
            img[6, i] = 0 if i % 2 == 0 else 255
            img[i, 6] = 0 if i % 2 == 0 else 255
        return img

    def save(self, img: np.ndarray, path: str):
        # save as PGM
        h, w = img.shape
        with open(path, "wb") as f:
            f.write(f"P5\n{w} {h}\n255\n".encode())
            f.write(img.tobytes())
