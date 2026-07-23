# Low Carbon London ingestion

## Why this pipeline exists

The official London Datastore archive is 795,722,689 bytes and contains 168
CSV partitions. Downloading the entire archive just to prove a parser creates a
slow onboarding path and weakens reproducibility.

The archive server advertises byte-range support. LoadShift therefore treats
the remote ZIP as a seekable file:

1. Resolve the current resource URL, size, hash, and licence through the
   official metadata API.
2. Read the ZIP central directory from the end of the remote file.
3. Select numeric partition zero unless a member is explicitly requested.
4. Fetch compressed blocks on demand with a one-megabyte read-ahead cache.
5. Stop after the requested number of CSV rows.
6. Write source provenance and a SHA-256 checksum beside the sample.

If the server ignores a range request and returns a full response, the reader
fails instead of accidentally downloading the entire archive.

## Transformation

DuckDB reads every raw field as text first. This prevents automatic type
inference from hiding malformed values. The transformation then:

1. Normalises the source header after verifying its four logical fields.
2. Maps the tariff group to `standard` or `dynamic_tou`.
3. Parses the source-documented GMT timestamp as an interval end in UTC.
4. Derives the interval start by subtracting 30 minutes.
5. Parses consumption as `DOUBLE` while preserving source `Null` as null.
6. Sorts by household and time and writes Zstandard-compressed Parquet.

## Quality policy

The pipeline fails on:

1. Missing or unexpected columns.
2. Missing household identifiers.
3. Unknown tariff groups.
4. Invalid timestamps or numeric values.
5. Negative consumption.
6. Conflicting values for the same household and interval.

It reports warnings for missing consumption, exact duplicate rows, and
non-half-hour gaps. Exact duplicates are deterministically reduced to the
first source occurrence only after confirming that their canonical tariff and
consumption values agree.

## Source evidence

The source is the [London Datastore Low Carbon London
dataset](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d),
published by UK Power Networks under [Creative Commons Attribution
4.0](https://creativecommons.org/licenses/by/4.0/). Timestamp and trial-design
semantics come from the [UK Data Service user
guide](https://doc.ukdataservice.ac.uk/doc/7857/mrdoc/pdf/7857_userguide.pdf).
