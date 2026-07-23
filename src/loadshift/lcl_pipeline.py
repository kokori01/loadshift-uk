"""Validation, Parquet conversion, and profiling for Low Carbon London CSVs."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from loadshift.contracts import SmartMeterReading
from loadshift.io import file_sha256
from loadshift.lcl_source import (
    LCL_DATASET_PAGE,
    LCL_RAW_COLUMNS,
    LCL_SCHEMA_VERSION,
)


class LCLDataQualityError(ValueError):
    """Raised when raw records cannot satisfy the canonical data contract."""


TariffGroup = Literal["standard", "dynamic_tou"]


def parse_lcl_timestamp(value: str) -> datetime:
    """Interpret the source's timezone-naive timestamp as documented GMT."""

    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalise_tariff_group(value: str) -> TariffGroup:
    normalised = value.strip().upper()
    if normalised in {"STD", "STANDARD"}:
        return "standard"
    if normalised in {"TOU", "DTOU", "DYNAMIC_TOU"}:
        return "dynamic_tou"
    raise ValueError(f"unknown LCL tariff group: {value!r}")


def parse_lcl_row(row: Mapping[str, str]) -> SmartMeterReading:
    """Parse one official long-form CSV row into the canonical contract."""

    missing = [column for column in LCL_RAW_COLUMNS if column not in row]
    if missing:
        raise ValueError(f"LCL row is missing columns: {missing}")

    interval_end = parse_lcl_timestamp(row["DateTime"])
    raw_consumption = row["KWH/hh (per half hour)"].strip()
    consumption = (
        None if raw_consumption.lower() in {"", "null"} else float(raw_consumption)
    )
    return SmartMeterReading(
        household_id=row["LCLid"].strip(),
        tariff_group=normalise_tariff_group(row["stdorToU"]),
        interval_start=interval_end - timedelta(minutes=30),
        interval_end=interval_end,
        consumption_kwh=consumption,
    )


def iter_lcl_csv(
    path: Path,
    *,
    limit: int | None = None,
) -> Iterator[SmartMeterReading]:
    """Stream validated records without loading the CSV into memory."""

    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        normalised_header = tuple(
            column.strip() for column in (reader.fieldnames or ())
        )
        if normalised_header != LCL_RAW_COLUMNS:
            raise ValueError(f"unexpected LCL columns: {reader.fieldnames!r}")
        reader.fieldnames = list(normalised_header)
        for index, row in enumerate(reader):
            if limit is not None and index >= limit:
                break
            yield parse_lcl_row(row)


def _json_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _source_metadata(path: Path) -> Mapping[str, object] | None:
    metadata_path = path.with_suffix(path.suffix + ".metadata.json")
    if not metadata_path.exists():
        return None
    with metadata_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("source metadata must be a JSON object")
    return payload


def _validate_header(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
    actual_header = tuple(header or ())
    normalised_header = tuple(column.strip() for column in actual_header)
    if normalised_header != LCL_RAW_COLUMNS:
        raise LCLDataQualityError(
            f"unexpected LCL columns: expected {LCL_RAW_COLUMNS!r}, got {header!r}"
        )
    # DuckDB trims surrounding header whitespace while reading CSV files.
    return normalised_header


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def ingest_lcl_csv(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    limit: int | None = None,
) -> Mapping[str, object]:
    """Convert official CSV rows to canonical Parquet and write a QA report."""

    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    actual_header = _validate_header(input_path)
    household_column, tariff_column, timestamp_column, consumption_column = (
        _quote_identifier(column) for column in actual_header
    )

    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError(
            "DuckDB is required; install the package with data extras"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output_path.with_suffix(output_path.suffix + ".part")
    temporary_output.unlink(missing_ok=True)

    row_limit = limit if limit is not None else 9_223_372_036_854_775_807
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(
            f"""
            CREATE TEMP TABLE lcl_stage AS
            SELECT
                row_number() OVER () AS source_row_number,
                coalesce(trim({household_column}), '') AS household_id,
                CASE upper(trim({tariff_column}))
                    WHEN 'STD' THEN 'standard'
                    WHEN 'STANDARD' THEN 'standard'
                    WHEN 'TOU' THEN 'dynamic_tou'
                    WHEN 'DTOU' THEN 'dynamic_tou'
                    WHEN 'DYNAMIC_TOU' THEN 'dynamic_tou'
                    ELSE NULL
                END AS tariff_group,
                coalesce(trim({timestamp_column}), '') AS timestamp_raw,
                try_cast(
                    coalesce(trim({timestamp_column}), '') AS TIMESTAMP
                )
                    AT TIME ZONE 'UTC' AS interval_end,
                coalesce(trim({consumption_column}), '')
                    AS consumption_raw,
                CASE
                    WHEN lower(coalesce(trim({consumption_column}), ''))
                        IN ('', 'null')
                    THEN NULL
                    ELSE try_cast(
                        coalesce(trim({consumption_column}), '') AS DOUBLE
                    )
                END AS consumption_kwh
            FROM read_csv(?, header = true, all_varchar = true)
            LIMIT ?
            """,
            [str(input_path), row_limit],
        )

        quality_row = connection.execute(
            """
            WITH valid_rows AS (
                SELECT household_id, interval_end
                FROM lcl_stage
                WHERE household_id <> '' AND interval_end IS NOT NULL
            ),
            duplicate_keys AS (
                SELECT
                    household_id,
                    interval_end,
                    count(*) AS occurrences,
                    count(DISTINCT coalesce(tariff_group, '<NULL>'))
                        AS tariff_versions,
                    count(DISTINCT coalesce(
                        cast(consumption_kwh AS VARCHAR),
                        '<NULL>'
                    )) AS consumption_versions
                FROM lcl_stage
                WHERE household_id <> '' AND interval_end IS NOT NULL
                GROUP BY household_id, interval_end
                HAVING count(*) > 1
            ),
            valid_intervals AS (
                SELECT DISTINCT household_id, interval_end
                FROM valid_rows
            ),
            ordered_intervals AS (
                SELECT
                    household_id,
                    interval_end,
                    interval_end - lag(interval_end) OVER (
                        PARTITION BY household_id ORDER BY interval_end
                    ) AS gap
                FROM valid_intervals
            ),
            interval_gaps AS (
                SELECT count(*) FILTER (
                    WHERE gap IS NOT NULL AND gap <> INTERVAL 30 MINUTE
                ) AS non_half_hour_gap_rows
                FROM ordered_intervals
            ),
            household_spans AS (
                SELECT
                    household_id,
                    count(*) AS observed_rows,
                    date_diff(
                        'minute',
                        min(interval_end),
                        max(interval_end)
                    ) // 30 + 1 AS expected_rows
                FROM valid_intervals
                GROUP BY household_id
            ),
            coverage AS (
                SELECT
                    coalesce(sum(expected_rows), 0)
                        AS expected_rows_on_observed_spans,
                    CASE
                        WHEN coalesce(sum(expected_rows), 0) = 0 THEN NULL
                        ELSE sum(observed_rows)::DOUBLE / sum(expected_rows)
                    END AS interval_coverage_ratio
                FROM household_spans
            )
            SELECT
                count(*) AS rows,
                count(DISTINCT household_id)
                    FILTER (WHERE household_id <> '') AS households,
                min(interval_end) AS min_interval_end,
                max(interval_end) AS max_interval_end,
                count(*) FILTER (WHERE household_id = '')
                    AS missing_household_rows,
                count(*) FILTER (WHERE tariff_group IS NULL)
                    AS invalid_tariff_rows,
                count(*) FILTER (WHERE interval_end IS NULL)
                    AS invalid_timestamp_rows,
                count(*) FILTER (
                    WHERE lower(consumption_raw) IN ('', 'null')
                ) AS missing_consumption_rows,
                count(*) FILTER (
                    WHERE lower(consumption_raw) NOT IN ('', 'null')
                      AND consumption_kwh IS NULL
                ) AS invalid_consumption_rows,
                count(*) FILTER (WHERE consumption_kwh < 0)
                    AS negative_consumption_rows,
                coalesce(
                    (SELECT sum(occurrences - 1) FROM duplicate_keys),
                    0
                ) AS duplicate_primary_key_rows,
                (
                    SELECT count(*)
                    FROM duplicate_keys
                    WHERE tariff_versions > 1 OR consumption_versions > 1
                ) AS conflicting_duplicate_keys,
                (SELECT non_half_hour_gap_rows FROM interval_gaps)
                    AS non_half_hour_gap_rows,
                (
                    SELECT expected_rows_on_observed_spans FROM coverage
                ) AS expected_rows_on_observed_spans,
                (SELECT interval_coverage_ratio FROM coverage)
                    AS interval_coverage_ratio
            FROM lcl_stage
            """
        ).fetchone()
        if quality_row is None:
            raise RuntimeError("DuckDB did not return a quality profile")

        (
            rows,
            households,
            min_interval_end,
            max_interval_end,
            missing_household_rows,
            invalid_tariff_rows,
            invalid_timestamp_rows,
            missing_consumption_rows,
            invalid_consumption_rows,
            negative_consumption_rows,
            duplicate_primary_key_rows,
            conflicting_duplicate_keys,
            non_half_hour_gap_rows,
            expected_rows_on_observed_spans,
            interval_coverage_ratio,
        ) = quality_row

        errors: list[str] = []
        warnings: list[str] = []
        if rows == 0:
            errors.append("input contains no data rows")
        checks = {
            "missing_household_rows": missing_household_rows,
            "invalid_tariff_rows": invalid_tariff_rows,
            "invalid_timestamp_rows": invalid_timestamp_rows,
            "invalid_consumption_rows": invalid_consumption_rows,
            "negative_consumption_rows": negative_consumption_rows,
            "conflicting_duplicate_keys": conflicting_duplicate_keys,
        }
        errors.extend(f"{name}={value}" for name, value in checks.items() if value)
        if missing_consumption_rows:
            warnings.append(f"missing_consumption_rows={missing_consumption_rows}")
        if duplicate_primary_key_rows and not conflicting_duplicate_keys:
            warnings.append(
                f"exact_duplicate_rows_removed={duplicate_primary_key_rows}"
            )
        if non_half_hour_gap_rows:
            warnings.append(f"non_half_hour_gap_rows={non_half_hour_gap_rows}")

        status = "fail" if errors else ("warn" if warnings else "pass")
        output_report: dict[str, object] = {
            "path": str(output_path),
            "format": "parquet",
            "compression": "zstd",
        }
        report: dict[str, object] = {
            "schema_version": LCL_SCHEMA_VERSION,
            "generated_at_utc": (datetime.now(UTC).isoformat().replace("+00:00", "Z")),
            "source": {
                "dataset_page": LCL_DATASET_PAGE,
                "input_path": str(input_path),
                "input_sha256": file_sha256(input_path),
                "metadata": _source_metadata(input_path),
            },
            "output": output_report,
            "profile": {
                "input_rows": rows,
                "output_rows": rows - duplicate_primary_key_rows,
                "households": households,
                "min_interval_end": _json_timestamp(min_interval_end),
                "max_interval_end": _json_timestamp(max_interval_end),
                "missing_consumption_rows": missing_consumption_rows,
                "duplicate_primary_key_rows": duplicate_primary_key_rows,
                "conflicting_duplicate_keys": conflicting_duplicate_keys,
                "non_half_hour_gap_rows": non_half_hour_gap_rows,
                "expected_rows_on_observed_spans": (expected_rows_on_observed_spans),
                "interval_coverage_ratio": interval_coverage_ratio,
                **checks,
            },
            "quality": {
                "status": status,
                "errors": errors,
                "warnings": warnings,
            },
            "assumptions": [
                (
                    "The source DateTime is the end of a half-hour interval "
                    "and is interpreted as GMT."
                ),
                ("Missing consumption remains null and is never silently imputed."),
            ],
        }

        if errors:
            _write_json_atomic(report_path, report)
            raise LCLDataQualityError("; ".join(errors))

        connection.execute(
            """
            COPY (
                SELECT
                    household_id,
                    tariff_group,
                    interval_end - INTERVAL 30 MINUTE AS interval_start,
                    interval_end,
                    consumption_kwh
                FROM lcl_stage
                WHERE household_id <> ''
                  AND interval_end IS NOT NULL
                QUALIFY row_number() OVER (
                    PARTITION BY household_id, interval_end
                    ORDER BY source_row_number
                ) = 1
                ORDER BY household_id, interval_end
            )
            TO ? (FORMAT PARQUET, COMPRESSION ZSTD)
            """,
            [str(temporary_output)],
        )
        os.replace(temporary_output, output_path)
        output_report["sha256"] = file_sha256(output_path)
        output_report["size_bytes"] = output_path.stat().st_size
        _write_json_atomic(report_path, report)
        return report
    except BaseException:
        temporary_output.unlink(missing_ok=True)
        raise
    finally:
        connection.close()
