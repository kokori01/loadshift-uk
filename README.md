# LoadShift UK

LoadShift UK is a production-minded data science project for forecasting
half-hourly electricity demand, estimating response to dynamic tariffs, and
scheduling flexible electricity use to reduce cost and carbon intensity.

The project is being built as evidence for UK Data Scientist placement roles.
It therefore treats data engineering, statistical validity, reproducibility,
deployment, and communication as first-class requirements.

## Current status

Sprint 1 establishes:

1. Typed contracts for half-hourly price and carbon-intensity observations.
2. Clients and parsers for the NESO Carbon Intensity and Octopus Energy APIs.
3. A leakage-safe seasonal-naive forecasting baseline.
4. Initial evaluation metrics and automated tests.
5. A documented experiment plan for the Low Carbon London trial.

No performance or savings claim is made until the historical evaluation has
been completed.

## Product question

> Which households are able and willing to shift electricity use, and when
> should flexible loads run to minimise cost and carbon without reducing user
> comfort?

The intended system has four layers:

| Layer | Responsibility |
| --- | --- |
| Data | Ingest, validate, version, and transform half-hourly observations |
| Science | Forecast demand and estimate heterogeneous tariff response |
| Decision | Optimise flexible-load schedules under user constraints |
| Product | Serve predictions, uncertainty, and backtested impact |

## Data sources

1. [Low Carbon London smart-meter data](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d)
2. [NESO Carbon Intensity API](https://carbonintensity.org.uk/)
3. [Elexon Insights API](https://bmrs.elexon.co.uk/api-documentation)
4. [Octopus Energy API](https://docs.octopus.energy/rest/guides/endpoints/)

The historical London dataset contains roughly 167 million half-hourly rows
from 5,567 households. Around 1,100 households received dynamic time-of-use
price signals in 2013. Treatment assignment and identification assumptions
must be verified before interpreting an estimate as causal.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
```

Fetch a carbon-intensity interval:

```bash
loadshift carbon \
  --from-time 2026-07-23T00:00:00Z \
  --to-time 2026-07-23T03:00:00Z \
  --output artifacts/carbon.jsonl
```

Fetch Octopus Agile prices by supplying an active product and tariff code:

```bash
loadshift prices \
  --product-code YOUR_PRODUCT_CODE \
  --tariff-code YOUR_TARIFF_CODE \
  --from-time 2026-07-23T00:00:00Z \
  --to-time 2026-07-23T03:00:00Z \
  --output artifacts/prices.jsonl
```

## Repository layout

```text
src/loadshift/       Application and modelling code
tests/               Offline unit tests
docs/                Project charter, contracts, experiments, and roadmap
data/                Local data zones, with large files excluded from Git
artifacts/           Generated model and evaluation outputs
```

## Engineering principles

1. Time-based splits only for forecasting evaluation.
2. Simple baselines before complex models.
3. Explicit units, time zones, and interval boundaries.
4. Raw data is immutable and never committed to Git.
5. Every model claim is paired with a baseline and uncertainty.
6. Business value is measured through backtesting, not estimated from training
   accuracy.

## Planned stack

The initial package deliberately stays small. Later sprints add DuckDB,
partitioned Parquet, Polars or PySpark, MLflow, FastAPI, Docker, and a deployed
decision dashboard only when each component has a measured purpose.

See [the roadmap](docs/ROADMAP.md) for the planned sequence.
