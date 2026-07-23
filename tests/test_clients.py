from datetime import UTC, datetime
from unittest import TestCase

from loadshift.clients.carbon_intensity import parse_carbon_intensity
from loadshift.clients.octopus import parse_octopus_prices


class CarbonParserTests(TestCase):
    def test_parses_carbon_response(self) -> None:
        payload = {
            "data": [
                {
                    "from": "2026-07-23T00:00Z",
                    "to": "2026-07-23T00:30Z",
                    "intensity": {
                        "forecast": 116,
                        "actual": 111,
                        "index": "low",
                    },
                }
            ]
        }
        records = parse_carbon_intensity(payload)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].actual_gco2_per_kwh, 111)
        self.assertEqual(
            records[0].interval_start,
            datetime(2026, 7, 23, 0, 0, tzinfo=UTC),
        )


class OctopusParserTests(TestCase):
    def test_sorts_reverse_chronological_response(self) -> None:
        payload = {
            "results": [
                {
                    "value_exc_vat": 20,
                    "value_inc_vat": 21,
                    "valid_from": "2026-07-23T00:30Z",
                    "valid_to": "2026-07-23T01:00Z",
                    "payment_method": None,
                },
                {
                    "value_exc_vat": 10,
                    "value_inc_vat": 10.5,
                    "valid_from": "2026-07-23T00:00Z",
                    "valid_to": "2026-07-23T00:30Z",
                    "payment_method": None,
                },
            ]
        }
        records = parse_octopus_prices(payload)
        self.assertEqual(records[0].price_pence_per_kwh_inc_vat, 10.5)
        self.assertLess(records[0].interval_start, records[1].interval_start)
