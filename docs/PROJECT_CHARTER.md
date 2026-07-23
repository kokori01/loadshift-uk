# Project charter

## Objective

Build a defensible decision system that predicts half-hourly residential
electricity demand, estimates heterogeneous response to dynamic prices, and
recommends flexible-load schedules that balance cost, carbon, and comfort.

## Primary audience

The first audience is a UK energy supplier, flexibility provider, or data
science hiring panel. The product must therefore support both a business
decision and a technically rigorous interview discussion.

## Core hypotheses

1. Daily and weekly load patterns provide a strong forecast baseline.
2. Dynamic price signals change consumption for only a subset of households.
3. Targeting responsive households produces more value than a uniform
   incentive policy.
4. A joint price-and-carbon schedule improves over fixed-time operation.

Each hypothesis can fail. Negative findings will be reported rather than hidden.

## Minimum viable product

The MVP will:

1. Transform a reproducible subset of Low Carbon London data.
2. Compare demand forecasts with seasonal-naive and simple statistical
   baselines.
3. Audit treatment assignment and estimate tariff response with uncertainty.
4. Backtest one flexible-appliance scheduling policy.
5. Expose results through a documented API and small decision dashboard.

## Non-goals for the MVP

1. Real-time control of physical appliances.
2. Claims that historical London households represent current UK households.
3. Deep learning before a simpler method is shown to be insufficient.
4. A chatbot that does not improve the underlying decision.
5. Commercial deployment or personalised financial advice.

## Definition of done

The MVP is complete when a reviewer can reproduce the pipeline, inspect the
time splits and assumptions, compare against baselines, call the prediction
API, and see measured cost and carbon outcomes from an out-of-sample backtest.
