# Data contracts

## Canonical interval

Every observation represents a closed-open 30-minute interval:

```text
[interval_start, interval_end)
```

Both timestamps must be timezone-aware. In storage and API boundaries they are
normalised to UTC. Local UK time is a presentation concern because daylight
saving transitions create days with 46 or 50 half-hour intervals.

## Units

| Field | Unit |
| --- | --- |
| Household consumption | kWh per 30-minute interval |
| Carbon intensity | gCO2 per kWh |
| Retail price | pence per kWh |
| Grid demand | MW |

Units are encoded in field names where practical. A value is never converted
without retaining its source unit in transformation metadata.

## Low Carbon London contract

The official long-form partition has four logical columns. The published CSV
contains trailing whitespace in one header, so ingestion strips header
whitespace and then requires an exact logical match.

| Raw field | Canonical field | Rule |
| --- | --- | --- |
| `LCLid` | `household_id` | Non-empty anonymised identifier |
| `stdorToU` | `tariff_group` | `Std` becomes `standard`; `ToU` becomes `dynamic_tou` |
| `DateTime` | `interval_end` | Source-documented GMT interval end |
| Derived | `interval_start` | `interval_end` minus 30 minutes |
| `KWH/hh (per half hour)` | `consumption_kwh` | kWh in the interval; source `Null` stays null |

The UK Data Service guide identifies the timestamps as GMT and as the end of
each measurement period. The pipeline therefore interprets the source's naive
timestamp as UTC, rather than as Europe/London wall-clock time. This avoids
inventing daylight-saving ambiguity.

Exact duplicate measurements are measured and reduced to one canonical row.
If the same household and interval contain different tariff or consumption
values, ingestion fails because choosing one would manufacture evidence.

## Required raw-data metadata

Each ingested dataset will record:

1. Source name and source URL.
2. Retrieval timestamp in UTC.
3. Requested time range.
4. File checksum or API response identifier.
5. Schema version.
6. Transformation version.

## Quality checks

1. Interval duration is exactly 30 minutes.
2. Primary keys are unique.
3. Expected interval coverage is measured, not assumed.
4. Negative consumption is flagged and investigated.
5. Missing values are never silently filled.
6. Daylight saving transitions are validated explicitly.
7. Future information is excluded from forecast features.
8. Exact duplicates are counted; conflicting duplicate keys fail ingestion.
