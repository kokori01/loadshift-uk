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
