"""Forecast metrics with explicit edge-case handling."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _aligned_arrays(
    actual: pd.Series,
    predicted: pd.Series,
) -> tuple[np.ndarray, np.ndarray]:
    if not actual.index.equals(predicted.index):
        raise ValueError("actual and predicted indexes must match exactly")
    if actual.isna().any() or predicted.isna().any():
        raise ValueError("metrics do not accept missing values")
    return actual.to_numpy(dtype=float), predicted.to_numpy(dtype=float)


def mean_absolute_error(actual: pd.Series, predicted: pd.Series) -> float:
    actual_values, predicted_values = _aligned_arrays(actual, predicted)
    return float(np.mean(np.abs(actual_values - predicted_values)))


def weighted_absolute_percentage_error(
    actual: pd.Series,
    predicted: pd.Series,
) -> float:
    actual_values, predicted_values = _aligned_arrays(actual, predicted)
    denominator = float(np.sum(np.abs(actual_values)))
    if denominator == 0:
        raise ValueError("WAPE is undefined when total absolute actual is zero")
    numerator = float(np.sum(np.abs(actual_values - predicted_values)))
    return numerator / denominator
