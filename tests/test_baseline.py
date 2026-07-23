from unittest import TestCase

import pandas as pd

from loadshift.baseline import seasonal_naive_forecast


class SeasonalNaiveTests(TestCase):
    def test_repeats_latest_daily_profile(self) -> None:
        index = pd.date_range(
            "2026-07-20T00:00:00Z",
            periods=96,
            freq="30min",
        )
        history = pd.Series(
            list(range(48)) + list(range(100, 148)),
            index=index,
            dtype=float,
        )

        forecast = seasonal_naive_forecast(history, horizon=50)

        self.assertEqual(len(forecast), 50)
        self.assertEqual(forecast.iloc[0], 100)
        self.assertEqual(forecast.iloc[47], 147)
        self.assertEqual(forecast.iloc[48], 100)
        self.assertEqual(
            forecast.index[0],
            history.index[-1] + pd.Timedelta(minutes=30),
        )

    def test_rejects_irregular_history(self) -> None:
        index = pd.DatetimeIndex(
            [
                "2026-07-20T00:00:00Z",
                "2026-07-20T00:30:00Z",
                "2026-07-20T01:30:00Z",
            ]
        )
        history = pd.Series([1, 2, 3], index=index, dtype=float)
        with self.assertRaises(ValueError):
            seasonal_naive_forecast(
                history,
                horizon=1,
                season_length=2,
            )
