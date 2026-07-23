"""Octopus Energy half-hourly tariff price client."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from urllib.parse import quote

from loadshift.clients.http import JsonHttpClient
from loadshift.contracts import TariffPriceRecord
from loadshift.time_utils import format_api_datetime, parse_api_datetime


def parse_octopus_prices(payload: Mapping[str, Any]) -> list[TariffPriceRecord]:
    rows = payload.get("results")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("price response must contain a results array")

    records: list[TariffPriceRecord] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each price row must be an object")
        records.append(
            TariffPriceRecord(
                interval_start=parse_api_datetime(str(row["valid_from"])),
                interval_end=parse_api_datetime(str(row["valid_to"])),
                price_pence_per_kwh_inc_vat=float(row["value_inc_vat"]),
                price_pence_per_kwh_exc_vat=(
                    None
                    if row.get("value_exc_vat") is None
                    else float(row["value_exc_vat"])
                ),
                payment_method=(
                    None
                    if row.get("payment_method") is None
                    else str(row["payment_method"])
                ),
            )
        )
    return sorted(records, key=lambda record: record.interval_start)


class OctopusPriceClient:
    """Read public price observations for a selected Octopus tariff."""

    def __init__(
        self,
        product_code: str,
        tariff_code: str,
        http: JsonHttpClient | None = None,
        *,
        base_url: str = "https://api.octopus.energy",
    ) -> None:
        if not product_code.strip() or not tariff_code.strip():
            raise ValueError("product_code and tariff_code are required")
        self.product_code = product_code
        self.tariff_code = tariff_code
        self.http = http or JsonHttpClient()
        self.base_url = base_url.rstrip("/")

    def fetch_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[TariffPriceRecord]:
        if end <= start:
            raise ValueError("end must be after start")

        product = quote(self.product_code, safe="")
        tariff = quote(self.tariff_code, safe="")
        endpoint = (
            f"{self.base_url}/v1/products/{product}/electricity-tariffs/"
            f"{tariff}/standard-unit-rates/"
        )
        payload = self.http.get_json(
            endpoint,
            params={
                "period_from": format_api_datetime(start),
                "period_to": format_api_datetime(end),
                "page_size": 1500,
            },
        )
        if payload.get("next") is not None:
            raise ValueError(
                "response is paginated; narrow the requested date interval"
            )
        return parse_octopus_prices(payload)
