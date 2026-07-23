"""Command-line entry point for reproducible ingestion tasks."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    start = parse_api_datetime(args.from_time)
    end = parse_api_datetime(args.to_time)

    if args.command == "carbon":
        records = CarbonIntensityClient().fetch_range(start, end)
    elif args.command == "prices":
        records = OctopusPriceClient(
            product_code=args.product_code,
            tariff_code=args.tariff_code,
        ).fetch_range(start, end)
    else:
        raise AssertionError(f"unexpected command: {args.command}")

    write_jsonl(records, args.output)
    print(f"Wrote {len(records)} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
