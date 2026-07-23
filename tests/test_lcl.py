import csv
import io
import json
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import TestCase

import duckdb

from loadshift.lcl_pipeline import (
    LCLDataQualityError,
    ingest_lcl_csv,
    iter_lcl_csv,
    parse_lcl_row,
)
from loadshift.lcl_source import (
    LCL_RAW_COLUMNS,
    HTTPRangeReader,
    discover_lcl_archive,
    extract_lcl_rows,
)

FIXTURE = Path(__file__).parent / "fixtures" / "lcl_sample.csv"


class LCLParserTests(TestCase):
    def test_parses_documented_gmt_interval_end(self) -> None:
        record = parse_lcl_row(
            {
                "LCLid": " MAC000001 ",
                "stdorToU": "Std",
                "DateTime": "2013-01-01 00:30:00.0000000",
                "KWH/hh (per half hour)": " 0.125",
            }
        )
        self.assertEqual(record.household_id, "MAC000001")
        self.assertEqual(record.tariff_group, "standard")
        self.assertEqual(
            record.interval_start,
            datetime(2013, 1, 1, 0, 0, tzinfo=UTC),
        )
        self.assertEqual(
            record.interval_end,
            datetime(2013, 1, 1, 0, 30, tzinfo=UTC),
        )
        self.assertEqual(record.consumption_kwh, 0.125)

    def test_streams_null_consumption_without_imputation(self) -> None:
        records = list(iter_lcl_csv(FIXTURE))
        self.assertEqual(len(records), 6)
        self.assertIsNone(records[2].consumption_kwh)
        self.assertEqual(records[-1].tariff_group, "dynamic_tou")


class LCLArchiveTests(TestCase):
    def test_extracts_requested_rows_from_numeric_partition_zero(self) -> None:
        buffer = io.BytesIO()
        payload = (
            ",".join(LCL_RAW_COLUMNS[:-1])
            + ","
            + LCL_RAW_COLUMNS[-1]
            + " "
            + "\nMAC000001,Std,2013-01-01 00:30:00.0000000, 0.1\n"
            + "MAC000001,Std,2013-01-01 01:00:00.0000000, 0.2\n"
        )
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "Small LCL Data/LCL-June2015v2_10.csv",
                payload,
            )
            archive.writestr(
                "Small LCL Data/LCL-June2015v2_0.csv",
                payload,
            )
        buffer.seek(0)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sample.csv"
            with zipfile.ZipFile(buffer) as archive:
                member, rows = extract_lcl_rows(
                    archive,
                    output,
                    rows=1,
                )
            self.assertTrue(member.endswith("_0.csv"))
            self.assertEqual(rows, 1)
            with output.open(encoding="utf-8", newline="") as handle:
                written = list(csv.reader(handle))
            self.assertEqual(len(written), 2)

    def test_range_reader_uses_cache(self) -> None:
        source = b"abcdefghijklmnopqrstuvwxyz"

        class FakeResponse:
            def __init__(
                self,
                payload: bytes,
                content_range: str,
            ) -> None:
                self.status = 206
                self.headers = {
                    "ETag": '"test-etag"',
                    "Last-Modified": "Wed, 01 Jan 2025 00:00:00 GMT",
                    "Content-Range": content_range,
                }
                self.payload = payload

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return self.payload

        def opener(request: object, *, timeout: float) -> FakeResponse:
            del timeout
            range_header = request.headers["Range"]
            start_text, end_text = range_header.removeprefix("bytes=").split("-")
            start = int(start_text)
            end = int(end_text)
            return FakeResponse(
                source[start : end + 1],
                f"bytes {start}-{end}/{len(source)}",
            )

        reader = HTTPRangeReader(
            "https://example.test/archive.zip",
            size_bytes=len(source),
            block_size=8,
            opener=opener,
        )
        self.assertEqual(reader.read(3), b"abc")
        self.assertEqual(reader.read(3), b"def")
        self.assertEqual(reader.range_requests, 1)
        reader.seek(20)
        self.assertEqual(reader.read(6), b"uvwxyz")
        self.assertEqual(reader.range_requests, 2)
        self.assertEqual(reader.etag, '"test-etag"')

    def test_range_reader_rejects_full_file_fallback(self) -> None:
        class FullResponse:
            status = 200
            headers: dict[str, str] = {}

            def __enter__(self) -> "FullResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b"full archive"

        def opener(request: object, *, timeout: float) -> FullResponse:
            del request, timeout
            return FullResponse()

        reader = HTTPRangeReader(
            "https://example.test/archive.zip",
            size_bytes=100,
            opener=opener,
        )
        with self.assertRaisesRegex(OSError, "refusing"):
            reader.read(10)

    def test_range_reader_rejects_large_unbounded_read(self) -> None:
        reader = HTTPRangeReader(
            "https://example.test/archive.zip",
            size_bytes=100,
            block_size=8,
        )
        with self.assertRaisesRegex(OSError, "unbounded"):
            reader.read()

    def test_discovers_partitioned_resource_from_catalogue(self) -> None:
        class FakeHttp:
            def get_json(self, url: str) -> dict[str, object]:
                self.url = url
                return {
                    "licence": {
                        "title": "Creative Commons Attribution",
                        "url": "https://creativecommons.org/licenses/by/4.0/",
                    },
                    "resources": {
                        "resource-id": {
                            "title": "low-carbon-london-data-168-files",
                            "url": (
                                "https://data.london.gov.uk/download/"
                                "vqm0d/resource-id/archive.zip"
                            ),
                            "size": 123,
                            "hash": "source-hash",
                        }
                    },
                }

        resource = discover_lcl_archive(FakeHttp())  # type: ignore[arg-type]
        self.assertEqual(resource.resource_id, "resource-id")
        self.assertEqual(resource.size_bytes, 123)
        self.assertEqual(resource.source_hash, "source-hash")


class LCLPipelineTests(TestCase):
    def test_accepts_official_trailing_header_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "official_header.csv"
            source.write_text(
                ",".join(LCL_RAW_COLUMNS)
                + " \nMAC1,Std,2013-01-01 00:30:00.0000000, 0.1\n",
                encoding="utf-8",
            )

            report = ingest_lcl_csv(
                source,
                directory / "output.parquet",
                directory / "profile.json",
            )

            self.assertEqual(report["quality"]["status"], "pass")
            self.assertEqual(report["profile"]["output_rows"], 1)

    def test_converts_valid_csv_to_profiled_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory / "sample.parquet"
            report_path = directory / "profile.json"

            report = ingest_lcl_csv(FIXTURE, output, report_path)

            self.assertEqual(report["quality"]["status"], "warn")
            self.assertEqual(report["profile"]["input_rows"], 6)
            self.assertEqual(report["profile"]["output_rows"], 6)
            self.assertEqual(report["profile"]["households"], 2)
            self.assertEqual(
                report["profile"]["missing_consumption_rows"],
                1,
            )
            self.assertEqual(report["profile"]["non_half_hour_gap_rows"], 0)
            self.assertEqual(
                report["profile"]["expected_rows_on_observed_spans"],
                6,
            )
            self.assertEqual(
                report["profile"]["interval_coverage_ratio"],
                1.0,
            )
            self.assertTrue(output.exists())
            self.assertTrue(report_path.exists())

            rows = duckdb.sql(
                "SELECT count(*) FROM read_parquet(?)",
                params=[str(output)],
            ).fetchone()
            self.assertEqual(rows, (6,))

    def test_rejects_duplicate_primary_key_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "duplicates.csv"
            source.write_text(
                ",".join(LCL_RAW_COLUMNS)
                + "\nMAC1,Std,2013-01-01 00:30:00.0000000, 0.1"
                + "\nMAC1,Std,2013-01-01 00:30:00.0000000, 0.2\n",
                encoding="utf-8",
            )
            output = directory / "duplicates.parquet"
            report_path = directory / "profile.json"

            with self.assertRaises(LCLDataQualityError):
                ingest_lcl_csv(source, output, report_path)

            self.assertFalse(output.exists())
            with report_path.open(encoding="utf-8") as handle:
                report = json.load(handle)
            self.assertEqual(report["quality"]["status"], "fail")
            self.assertEqual(
                report["profile"]["conflicting_duplicate_keys"],
                1,
            )

    def test_removes_only_exact_duplicate_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "exact_duplicates.csv"
            source.write_text(
                ",".join(LCL_RAW_COLUMNS)
                + "\nMAC1,Std,2013-01-01 00:30:00.0000000, 0.1"
                + "\nMAC1,Std,2013-01-01 00:30:00.0000000, 0.1\n",
                encoding="utf-8",
            )
            output = directory / "deduplicated.parquet"
            report_path = directory / "profile.json"

            report = ingest_lcl_csv(source, output, report_path)

            self.assertEqual(report["quality"]["status"], "warn")
            self.assertEqual(
                report["profile"]["duplicate_primary_key_rows"],
                1,
            )
            self.assertEqual(report["profile"]["output_rows"], 1)
            rows = duckdb.sql(
                "SELECT count(*) FROM read_parquet(?)",
                params=[str(output)],
            ).fetchone()
            self.assertEqual(rows, (1,))

    def test_rejects_missing_household_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "missing_household.csv"
            source.write_text(
                ",".join(LCL_RAW_COLUMNS) + "\n,Std,2013-01-01 00:30:00.0000000, 0.1\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                LCLDataQualityError,
                "missing_household_rows=1",
            ):
                ingest_lcl_csv(
                    source,
                    directory / "output.parquet",
                    directory / "profile.json",
                )
