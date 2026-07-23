# Low Carbon London sample validation

## Reproduction

The validation run on 23 July 2026 used:

```bash
loadshift lcl-sample \
  --rows 50000 \
  --output data/raw/lcl/lcl_50k.csv

loadshift lcl-ingest \
  --input data/raw/lcl/lcl_50k.csv \
  --output data/interim/lcl/lcl_50k.parquet \
  --report artifacts/lcl_50k_profile.json
```

## Observed result

| Measure | Value |
| --- | ---: |
| Official archive size | 795,722,689 bytes |
| Range requests | 4 |
| Bytes transferred | 1,062,496 |
| Archive fraction transferred | 0.1335% |
| Input observations | 50,000 |
| Canonical output observations | 49,966 |
| Households represented | 2 |
| Exact duplicate rows removed | 34 |
| Conflicting duplicate keys | 0 |
| Missing consumption rows | 2 |
| Non-half-hour gap rows | 12 |
| Coverage over observed household spans | 99.8940% |
| Parquet size | 343,356 bytes |

The sample SHA-256 was
`7161c1561c9941d4f7179a933dfbe53f37735bf473afe7db5b421f19e4d794ee`.
The generated Parquet SHA-256 was
`ae79ccc8a5dc5a0ef5c62678d54d8093c68161adb46a21d33d6a42631234c03a`.

The quality status was `warn`, not `pass`, because missing measurements,
source-identical duplicates, and cadence gaps were observed and disclosed.

## Interpretation limit

This is the first 50,000 rows of numeric partition zero, not a random or
representative sample of all 5,567 households. Its quality rates must not be
generalised to the full dataset. The run proves retrieval, schema handling,
quality policy, and conversion behaviour; it does not support a population or
model claim.
