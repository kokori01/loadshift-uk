"""Forecasting baselines that establish the minimum acceptable model quality."""

from __future__ import annotations

import math

import pandas as pd


def _validate_history(history: pd.Series, season_length: int) -> pd.Series:
    if season_length <= 0:
        raise ValueError("season_length must be positive")
    if not isinstance(history.index, pd.DatetimeIndex):
        raise TypeError("history must use a DatetimeIndex")
    if history.index.tz is None:
        raise ValueError("history index must be timezone-aware")
    if not history.index.is_monotonic_increasing or not history.index.is_unique:
        raise ValueError("history index must be unique and increasing")
    if history.isna().any():
        raise ValueError("history cannot contain missing values")
    if len(history) < season_length:
        raise ValueError("history is shorter than one season")
    if len(history.index) > 1:
        gaps = history.index.to_series().diff().dropna().unique()
        if len(gaps) != 1 or gaps[0] != pd.Timedelta(minutes=30):
            raise ValueError("history must have a regular 30-minute frequency")
    return history.astype(float)


def seasonal_naive_forecast(
    history: pd.Series,
    *,
    horizon: int,
    season_length: int = 48,
) -> pd.Series:
    """Repeat the latest observed season over a future half-hourly horizon."""

    if horizon <= 0:
        raise ValueError("horizon must be positive")
    validated = _validate_history(history, season_length)
    latest_season = validated.iloc[-season_length:].to_numpy()
    repetitions = math.ceil(horizon / season_length)
    forecast_values = list(latest_season) * repetitions
    forecast_values = forecast_values[:horizon]
    forecast_index = pd.date_range(
        start=validated.index[-1] + pd.Timedelta(minutes=30),
        periods=horizon,
        freq="30min",
        tz=validated.index.tz,
    )
    return pd.Series(
        forecast_values,
        index=forecast_index,
        name="forecast_kwh",
        dtype=float,
    )
