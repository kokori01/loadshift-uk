"""NESO Carbon Intensity API client and normaliser."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Literal, cast

from loadshift.clients.http import JsonHttpClient
from loadshift.contracts import CarbonIntensityRecord
from loadshift.time_utils import format_api_datetime, parse_api_datetime

CarbonIndex = Literal[
    "very low",
    "low",
    "moderate",
    "high",
    "very high",
]


def parse_carbon_intensity(
    payload: Mapping[str, Any],
) -> list[CarbonIntensityRecord]:
    rows = payload.get("data")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("carbon response must contain a data array")

    records: list[CarbonIntensityRecord] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each carbon row must be an object")
        intensity = row.get("intensity")
        if not isinstance(intensity, Mapping):
            raise ValueError("carbon row is missing intensity values")

        raw_index = intensity.get("index")
        index: CarbonIndex | None = None
        if raw_index is not None:
            normalised_index = str(raw_index).lower()
            if normalised_index not in {
                "very low",
                "low",
                "moderate",
                "high",
                "very high",
            }:
                raise ValueError(f"unexpected carbon-intensity index: {raw_index!r}")
            index = cast(CarbonIndex, normalised_index)

        records.append(
            CarbonIntensityRecord(
                interval_start=parse_api_datetime(str(row["from"])),
                interval_end=parse_api_datetime(str(row["to"])),
                forecast_gco2_per_kwh=float(intensity["forecast"]),
                actual_gco2_per_kwh=(
                    None
                    if intensity.get("actual") is None
                    else float(intensity["actual"])
                ),
                index=index,
            )
        )
    return records


class CarbonIntensityClient:
    """Read national half-hourly forecast and actual carbon intensity."""

    def __init__(
        self,
        http: JsonHttpClient | None = None,
        *,
        base_url: str = "https://api.carbonintensity.org.uk",
    ) -> None:
        self.http = http or JsonHttpClient()
        self.base_url = base_url.rstrip("/")

    def fetch_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CarbonIntensityRecord]:
        if end <= start:
            raise ValueError("end must be after start")
        endpoint = (
            f"{self.base_url}/intensity/"
            f"{format_api_datetime(start)}/{format_api_datetime(end)}"
        )
        return parse_carbon_intensity(self.http.get_json(endpoint))
