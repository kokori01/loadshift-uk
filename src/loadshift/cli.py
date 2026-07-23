"""Command-line entry point for reproducible ingestion tasks."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from loadshift.clients import CarbonIntensityClient, OctopusPriceClient
from loadshift.io import write_jsonl
from loadshift.time_utils import parse_api_datetime


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loadshift")
    subparsers = parser.add_subparsers(dest="command", required=True)

    carbon = subparsers.add_parser("carbon")
    carbon.add_argument("--from-time", required=True)
    carbon.add_argument("--to-time", required=True)
    carbon.add_argument("--output", type=Path, required=True)

    prices = subparsers.add_parser("prices")
    prices.add_argument("--product-code", required=True)
    prices.add_argument("--tariff-code", required=True)
    prices.add_argument("--from-time", required=True)
    prices.add_argument("--to-time", required=True)
    prices.add_argument("--output", type=Path, required=True)

    lcl_sample = subparsers.add_parser(
        "lcl-sample",
        help="stream a small sample from the official LCL ZIP archive",
    )
    lcl_sample.add_argument("--output", type=Path, required=True)
    lcl_sample.add_argument("--rows", type=int, default=50_000)
    lcl_sample.add_argument("--metadata-output", type=Path)
    lcl_sample.add_argument("--member")

    lcl_ingest = subparsers.add_parser(
        "lcl-ingest",
        help="validate an LCL CSV and convert it to canonical Parquet",
    )
    lcl_ingest.add_argument("--input", type=Path, required=True)
    lcl_ingest.add_argument("--output", type=Path, required=True)
    lcl_ingest.add_argument("--report", type=Path, required=True)
    lcl_ingest.add_argument("--limit", type=int)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "carbon":
        start = parse_api_datetime(args.from_time)
        end = parse_api_datetime(args.to_time)
        carbon_records = CarbonIntensityClient().fetch_range(start, end)
        write_jsonl(carbon_records, args.output)
        print(f"Wrote {len(carbon_records)} records to {args.output}")
    elif args.command == "prices":
        start = parse_api_datetime(args.from_time)
        end = parse_api_datetime(args.to_time)
        price_records = OctopusPriceClient(
            product_code=args.product_code,
            tariff_code=args.tariff_code,
        ).fetch_range(start, end)
        write_jsonl(price_records, args.output)
        print(f"Wrote {len(price_records)} records to {args.output}")
    elif args.command == "lcl-sample":
        from loadshift.lcl_source import fetch_lcl_sample

        result = fetch_lcl_sample(
            args.output,
            rows=args.rows,
            metadata_output=args.metadata_output,
            member_name=args.member,
        )
        print(
            f"Wrote {result.rows} rows to {result.output} "
            f"using {result.transferred_bytes} transferred bytes"
        )
        print(f"Wrote provenance metadata to {result.metadata_output}")
    elif args.command == "lcl-ingest":
        from loadshift.lcl_pipeline import ingest_lcl_csv

        report = ingest_lcl_csv(
            args.input,
            args.output,
            args.report,
            limit=args.limit,
        )
        profile = report["profile"]
        if not isinstance(profile, dict):
            raise RuntimeError("profile result must be an object")
        print(
            f"Wrote {profile['output_rows']} rows across "
            f"{profile['households']} households to {args.output}"
        )
        print(f"Wrote data-quality report to {args.report}")
    else:
        raise AssertionError(f"unexpected command: {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
