"""Time parsing and formatting helpers."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_api_datetime(value: str) -> datetime:
    """Parse an ISO 8601 API timestamp and normalise it to UTC."""

    normalised = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalised)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp is missing a timezone: {value!r}")
    return parsed.astimezone(UTC)


def format_api_datetime(value: datetime) -> str:
    """Format a timezone-aware timestamp for public UK energy APIs."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")
