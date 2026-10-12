# dynamic-relative-activity-momentum
A systematic quantitative research engine for dynamically identifying high-momentum equities and detecting abnormal market activity through relative volume and traded-value expansion.

## Daily historical research

The research pipeline reads daily OHLCV files from `data/` and the current symbol list in `watchlists/symbols.csv`. It resolves data filenames using the same symbol normalization as ingestion (for example, `M&M` maps to `M_AMP_M.csv` and `NAM-INDIA` maps to `NAM_DASH_INDIA.csv`) while preserving the original symbol in research outputs. Each selected file needs `Date` or `TimeStamp`, `Open`, `High`, `Low`, `Close`, and `Volume` columns. Invalid OHLC rows, missing required values, and duplicate dates are counted in the validation output; rows with missing or invalid data are not filled or fabricated.

From the repository root, run the pipeline in the existing `dram` Conda environment:

```bash
conda run -n dram python -m src.run_research
```

Outputs are written to `output/`: `master_daily.csv` and `master_daily.parquet` (daily features, membership, signals, and forward returns), `daily_watchlist.csv`, `signal_events.csv`, `signal_statistics.csv`, `signal_frequency.csv`, `validation_report.csv`, `latest_observation_candidates.csv` (latest available date), and `latest_broad_coverage_observations.csv` (latest date with at least 90% of the valid data universe present). For a meeting, start with `latest_broad_coverage_observations.csv`: each row is a stock to observe, with 3D/6D ranks, RVOL/RVAL, activity qualification, and a coverage status. `ActivityQualified` means the research activity threshold was met; it is not a buy recommendation. Research plots are saved under `output/plots/`, including return distributions, signal counts over time, RVOL/RVAL, and mean forward-return comparisons. Checks use the standard library and run with `conda run -n dram python -m unittest discover -s tests`.

The 3-day and 6-day watchlists are recalculated each date from the contemporaneous close history. The 252-observation volume and traded-value means are shifted by one observation, so the signal date is excluded. Forward returns are stored for evaluation only and never enter the signal rules. Strategies reported independently are momentum-only, RVOL, RVAL, OR, and AND.

## Scope and limitations

This is daily historical research, not an intraday monitor or trading system. There is no broker integration, order placement, or live feed. `src.intraday.MarketDataProvider` defines the future data-provider boundary; the current files do not contain intraday observations needed for time-of-day normalized RVOL/RVAL. Current constituent files and the current symbol list do not provide point-in-time NIFTY 500 membership, so historical results have survivorship bias. Corporate-action adjustment cannot be independently verified from these CSVs; the existing ingestion fetcher requests split-adjusted TradingView data, but the stored files do not carry adjustment metadata. Forward returns use unadjusted stored closes and can therefore be affected by corporate actions.
