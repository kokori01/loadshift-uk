from datetime import UTC, datetime, timedelta
from unittest import TestCase

from pydantic import ValidationError

from loadshift.contracts import CarbonIntensityRecord, TariffPriceRecord


class ContractTests(TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 7, 23, 0, 0, tzinfo=UTC)
        self.end = self.start + timedelta(minutes=30)

    def test_valid_carbon_record(self) -> None:
        record = CarbonIntensityRecord(
            interval_start=self.start,
            interval_end=self.end,
            forecast_gco2_per_kwh=121,
            actual_gco2_per_kwh=118,
            index="low",
        )
        self.assertEqual(record.forecast_gco2_per_kwh, 121)

    def test_rejects_non_half_hour_interval(self) -> None:
        with self.assertRaises(ValidationError):
            TariffPriceRecord(
                interval_start=self.start,
                interval_end=self.start + timedelta(minutes=60),
                price_pence_per_kwh_inc_vat=17.2,
            )

    def test_rejects_naive_timestamp(self) -> None:
        with self.assertRaises(ValidationError):
            CarbonIntensityRecord(
                interval_start=datetime(2026, 7, 23, 0, 0),
                interval_end=datetime(2026, 7, 23, 0, 30),
                forecast_gco2_per_kwh=121,
            )
