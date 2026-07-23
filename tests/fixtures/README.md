# Test fixtures

`lcl_sample.csv` is synthetic data shaped like the official Low Carbon London
long-form partitions. It contains no real household observations. Tests use it
to exercise schema, interval, missing-value, tariff-group, and Parquet logic
without depending on the network.
