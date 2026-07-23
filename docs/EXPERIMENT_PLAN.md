# Experiment plan

## Forecasting question

How accurately can the next 48 half-hourly intervals be forecast for a
household or household segment using only information available at prediction
time?

The first comparison includes:

1. Previous-day seasonal naive.
2. Previous-week seasonal naive.
3. Regularised linear regression with calendar and lag features.
4. Gradient-boosted trees.

Evaluation uses rolling-origin splits. Random train-test splitting is
prohibited because it leaks future temporal structure.

Primary metrics are MAE, WAPE, and pinball loss for prediction intervals.
Metrics will also be reported by hour, season, and household segment.

## Tariff-response question

Which households reduce or shift usage after high-price signals, and can the
response be predicted before offering an incentive?

Before model selection, the analysis must establish:

1. How dynamic-tariff households were selected.
2. Whether assignment was random.
3. Which pre-treatment covariates are available.
4. Whether treatment timing and price signals are observed without leakage.
5. Whether interference between households is plausible.

If assignment is random, heterogeneous treatment-effect estimators can be used
with honest sample splitting. If it is not random, the result will be framed as
quasi-experimental and tested with matching, weighting, or
difference-in-differences assumptions.

No causal wording is allowed unless the identification assumptions are
documented and supported.

## Decision-policy question

Given a forecast load, a price path, a carbon-intensity path, and appliance
constraints, when should the flexible load operate?

The optimiser will be compared with:

1. A fixed user-selected schedule.
2. Cheapest-price scheduling.
3. Lowest-carbon scheduling.
4. A weighted price-and-carbon policy.

Outcomes are measured as cost, carbon, comfort-constraint violations, and
regret under forecast error.
