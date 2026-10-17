"""Orientation CNN model for component alignment."""
from __future__ import annotations

import numpy as np

from pnp.ml.layers import Activation, BatchNorm, Conv2D, Dense, Dropout, Flatten, MaxPool2D
from pnp.ml.models import Sequential


def build_orientation_cnn(input_shape: tuple = (1, 64, 64), num_classes: int = 360) -> Sequential:
    model = Sequential()
    model.add(Conv2D(input_shape[0], 32, kernel_size=3, padding=1))
    model.add(BatchNorm(32))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Conv2D(32, 64, kernel_size=3, padding=1))
    model.add(BatchNorm(64))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Conv2D(64, 128, kernel_size=3, padding=1))
    model.add(BatchNorm(128))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Flatten())
    model.add(Dense(128 * (input_shape[1]//8) * (input_shape[2]//8), 256))
    model.add(Activation("relu"))
    model.add(Dropout(0.5))
    model.add(Dense(256, num_classes))
    model.add(Activation("softmax"))
    return model


class OrientationPredictor:
    def __init__(self, model: Sequential | None = None):
        self.model = model if model is not None else build_orientation_cnn()
        self.classes = np.arange(360)

    def predict(self, image: np.ndarray) -> tuple[float, float]:
        # image: (H, W) or (C, H, W)
        if image.ndim == 2:
            image = image[np.newaxis, np.newaxis, :, :]
        elif image.ndim == 3:
            image = image[np.newaxis, :, :, :]
        image = image.astype(np.float32) / 255.0
        out = self.model(image)
        idx = int(np.argmax(out[0]))
        confidence = float(out[0, idx])
        return float(idx), confidence

    def predict_batch(self, images: np.ndarray) -> list[tuple[float, float]]:
        return [self.predict(img) for img in images]


def build_defect_detector(input_shape: tuple = (3, 224, 224)) -> Sequential:
    model = Sequential()
    model.add(Conv2D(input_shape[0], 16, kernel_size=3, padding=1))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Conv2D(16, 32, kernel_size=3, padding=1))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Conv2D(32, 64, kernel_size=3, padding=1))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Flatten())
    model.add(Dense(64 * (input_shape[1]//8) * (input_shape[2]//8), 128))
    model.add(Activation("relu"))
    model.add(Dense(128, 2))
    model.add(Activation("softmax"))
    return model


def build_component_classifier(num_classes: int = 10, input_shape: tuple = (3, 64, 64)) -> Sequential:
    model = Sequential()
    model.add(Conv2D(input_shape[0], 32, kernel_size=3, padding=1))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Conv2D(32, 64, kernel_size=3, padding=1))
    model.add(Activation("relu"))
    model.add(MaxPool2D(2, 2))
    model.add(Flatten())
    model.add(Dense(64 * (input_shape[1]//4) * (input_shape[2]//4), 128))
    model.add(Activation("relu"))
    model.add(Dense(128, num_classes))
    model.add(Activation("softmax"))
    return model
