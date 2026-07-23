# Roadmap

## Sprint 1: reliable foundation

1. Establish contracts and public API parsers.
2. Add a seasonal-naive forecast and metrics.
3. Document assumptions, units, and evaluation rules.
4. Run all tests offline.

## Sprint 2: historical data pipeline

1. Download one official one-million-row split.
2. Profile schema, missingness, duplicates, and daylight saving behaviour.
3. Convert raw CSV to partitioned Parquet with DuckDB or Polars.
4. Add data-quality checks and a reproducible sample.

## Sprint 3: forecasting benchmark

1. Define rolling-origin splits.
2. Compare daily and weekly seasonal baselines.
3. Add lag-based linear and gradient-boosted models.
4. Track experiments and prediction intervals.

## Sprint 4: tariff-response analysis

1. Audit treatment assignment.
2. Estimate average and heterogeneous response.
3. Run balance, overlap, sensitivity, and placebo checks.
4. Translate the estimate into a targeting policy.

## Sprint 5: decision product

1. Add cost-and-carbon scheduling.
2. Backtest under forecast uncertainty.
3. Serve results through FastAPI.
4. Build a focused decision dashboard.

## Sprint 6: production evidence

1. Add Docker and scheduled ingestion.
2. Track data and model drift.
3. Deploy a public read-only demo.
4. Publish a technical report, model card, and short demo video.
