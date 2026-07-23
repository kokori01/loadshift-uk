"""Typed contracts shared by ingestion, modelling, and serving layers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


class HalfHourlyRecord(BaseModel):
    """Base contract for one closed-open half-hour interval."""

    model_config = ConfigDict(frozen=True)

    interval_start: datetime
    interval_end: datetime

    @model_validator(mode="after")
    def validate_interval(self) -> HalfHourlyRecord:
        if not _is_timezone_aware(self.interval_start):
            raise ValueError("interval_start must be timezone-aware")
        if not _is_timezone_aware(self.interval_end):
            raise ValueError("interval_end must be timezone-aware")
        if self.interval_end - self.interval_start != timedelta(minutes=30):
            raise ValueError("record must represent exactly 30 minutes")
        return self


class CarbonIntensityRecord(HalfHourlyRecord):
    """NESO forecast and optional estimated actual carbon intensity."""

    forecast_gco2_per_kwh: float = Field(ge=0)
    actual_gco2_per_kwh: float | None = Field(default=None, ge=0)
    index: Literal["very low", "low", "moderate", "high", "very high"] | None = None


class TariffPriceRecord(HalfHourlyRecord):
    """Half-hour retail electricity price from an Octopus tariff."""

    price_pence_per_kwh_inc_vat: float
    price_pence_per_kwh_exc_vat: float | None = None
    payment_method: str | None = None


class SmartMeterReading(HalfHourlyRecord):
    """Canonical Low Carbon London household-consumption observation."""

    household_id: str = Field(min_length=1)
    tariff_group: Literal["standard", "dynamic_tou"]
    consumption_kwh: float | None = Field(default=None, ge=0)
