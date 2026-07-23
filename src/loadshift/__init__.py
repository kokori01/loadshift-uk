"""LoadShift UK core package."""

from loadshift.baseline import seasonal_naive_forecast
from loadshift.contracts import CarbonIntensityRecord, TariffPriceRecord

__all__ = [
    "CarbonIntensityRecord",
    "TariffPriceRecord",
    "seasonal_naive_forecast",
]

__version__ = "0.1.0"
