# Local data zones

Large and licensed datasets are not stored in Git.

| Directory | Purpose |
| --- | --- |
| `raw` | Immutable source files |
| `interim` | Validated and normalised intermediate data |
| `processed` | Model-ready, versioned features and labels |

The pipeline will create these directories as needed. Only documentation and
empty placeholders belong in the repository.
