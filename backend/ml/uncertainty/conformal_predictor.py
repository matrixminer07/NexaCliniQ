from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np
from crepes import ConformalRegressor


class MolecularConformalPredictor:
    """Conformal prediction wrapper for molecular base regressors."""

    def __init__(self, base_model, calibration_x: Iterable, calibration_y: Iterable, alpha: float = 0.1):
        self.base_model = base_model
        self.alpha = alpha
        self.cp = ConformalRegressor()

        x_cal = np.asarray(list(calibration_x))
        y_cal = np.asarray(list(calibration_y)).reshape(-1)
        y_hat = np.asarray(self.base_model.predict(x_cal)).reshape(-1)
        residuals = np.abs(y_cal - y_hat)
        self.cp.fit(residuals=residuals)

    def predict_with_intervals(self, x) -> Tuple[float, float, float, float]:
        x_arr = np.asarray(x).reshape(1, -1)
        point = float(self.base_model.predict(x_arr)[0])
        lower, upper = self.cp.predict(y_hat=np.array([point]), confidence=1 - self.alpha)
        return point, float(lower[0]), float(upper[0]), float(1 - self.alpha)
