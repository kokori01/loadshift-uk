# Local data zones

Large and licensed datasets are not stored in Git.

| Directory | Purpose |
| --- | --- |
| `raw` | Immutable source files |
| `interim` | Validated and normalised intermediate data |
| `processed` | Model-ready, versioned features and labels |

The pipeline will create these directories as needed. Only documentation and
empty placeholders belong in the repository.

## Low Carbon London sample

The official partitioned archive is roughly 796 MB. The sample command opens
the remote ZIP as a seekable byte-range stream, reads partition metadata, and
downloads only the compressed bytes needed for the requested rows:

```bash
loadshift lcl-sample \
  --rows 50000 \
  --output data/raw/lcl/lcl_50k.csv
```

The command also writes `lcl_50k.csv.metadata.json` with the official resource
URL, licence, archive member, retrieval time, checksums, and transfer size.

Convert and profile the sample:

```bash
loadshift lcl-ingest \
  --input data/raw/lcl/lcl_50k.csv \
  --output data/interim/lcl/lcl_50k.parquet \
  --report artifacts/lcl_50k_profile.json
```

Raw and generated data remain ignored by Git. A reviewer can reproduce them
from the commands and provenance metadata.
