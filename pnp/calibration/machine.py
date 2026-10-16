"""Machine calibration: backlash, squareness, scale."""
from __future__ import annotations

import numpy as np


def estimate_scale(measured, nominal):
    return float(np.polyfit(nominal, measured, 1)[0])


def estimate_backlash(forward, backward):
    return float(np.mean(np.abs(np.array(forward) - np.array(backward))))
