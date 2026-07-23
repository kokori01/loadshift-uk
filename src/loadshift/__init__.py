"""LoadShift UK core package."""

from loadshift.baseline import seasonal_naive_forecast
from loadshift.contracts import (
    CarbonIntensityRecord,
    SmartMeterReading,
    TariffPriceRecord,
)

__all__ = [
    "CarbonIntensityRecord",
    "SmartMeterReading",
    "TariffPriceRecord",
    "seasonal_naive_forecast",
]

__version__ = "0.2.0"
