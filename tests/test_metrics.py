from unittest import TestCase

import pandas as pd

from loadshift.metrics import (
    mean_absolute_error,
    weighted_absolute_percentage_error,
)


class MetricTests(TestCase):
    def test_metrics(self) -> None:
        index = pd.date_range("2026-07-23", periods=3, freq="30min", tz="UTC")
        actual = pd.Series([1.0, 2.0, 3.0], index=index)
        predicted = pd.Series([2.0, 2.0, 2.0], index=index)

        self.assertAlmostEqual(mean_absolute_error(actual, predicted), 2 / 3)
        self.assertAlmostEqual(
            weighted_absolute_percentage_error(actual, predicted),
            2 / 6,
        )

    def test_rejects_misaligned_index(self) -> None:
        actual = pd.Series(
            [1.0],
            index=pd.DatetimeIndex(["2026-07-23T00:00Z"]),
        )
        predicted = pd.Series(
            [1.0],
            index=pd.DatetimeIndex(["2026-07-23T00:30Z"]),
        )
        with self.assertRaises(ValueError):
            mean_absolute_error(actual, predicted)
