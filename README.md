# Dynamic Relative Volume & Value Breakout Research

A daily research scanner for finding recent stock gainers and checking whether unusually high trading activity accompanies their momentum. It produces watchlists, historical signals, and forward-return analysis.

> **Research only.** This project does not recommend trades, place orders, connect to a broker, or manage positions. Its current signal calculations use daily bars; it does not provide a live intraday monitor.

## At a glance

1. Rank symbols by price change over the previous 3 and 6 trading sessions.
2. Combine each day's top 10 lists, removing duplicate symbols.
3. Compare daily volume and traded value with their own previous 252-session averages.
4. Mark a research signal when a watchlist symbol has RVOL ≥ 2 **or** RVAL ≥ 2.
5. Evaluate each historical signal using 1, 3, 5, and 10-session forward returns.

```text
Daily OHLCV → validation → momentum and activity features → daily watchlist
            → RVOL/RVAL research signals → forward-return statistics and reports
```

The 252-session averages exclude the current session. Forward returns are evaluation fields only and are not used to create the signal.

## Quick start

Run commands from the repository root. The project uses the existing Conda environment named `dram`.

```bash
conda activate dram
python -m src.run_research
```

The research run reads `data/` and `watchlists/symbols.csv`, then regenerates the files in `output/`. To run the test suite:

```bash
python -m unittest discover -s tests -v
```

If the `dram` environment has not been created on a new machine, create it from the checked-in definition:

```bash
conda env create -f environment.yml
conda activate dram
```

Alternatively, install the pinned Python packages into an already activated environment with `python -m pip install -r requirements.txt`.

## Getting daily OHLCV data

The research pipeline does not fetch data itself. The repository includes a TradingView-based daily data ingestion script. It writes one CSV per symbol under the configured data folder. It is not a broker connection and does not place trades.

### Create the local ingestion configuration

The real configuration file is intentionally excluded from Git because the TradingView session ID is private. After cloning, create it from the safe template:

```bash
cp ingestion/config/.env.example ingestion/config/.env
```

The template contains:

```dotenv
SESSION_ID=
DATA_PATH=../../data
```

- `SESSION_ID` is refreshed and written by `ingestion/session.py` when ingestion runs. The script needs to launch Playwright's Chromium browser for this step. If Chromium is missing, install it in the active environment with `python -m playwright install chromium`.
- `DATA_PATH` chooses where the daily CSVs are saved. Relative paths are resolved from `ingestion/config/`, so `../../data` points to the repository's top-level `data/` folder. The default is `data`, which would instead mean `ingestion/config/data`.
- Keep `ingestion/config/.env` private. Do not paste its session ID into notebooks, commits, screenshots, or chat.

Fetch/update the symbols listed in `watchlists/symbols.csv` with daily bars:

```bash
python ingestion/fetch_all_data.py --interval 1D --bars 100000 --mode direct
```

The default symbol column is `symbol` and column matching is case-insensitive, so the supplied `Symbol` header works. The script refreshes the TradingView session and reports symbols that fail. Check that every requested ticker resolves correctly on TradingView and review failures before treating the data as a complete market snapshot. The fetch loop uses a short delay between symbols; large refreshes may take time.

Once the CSVs are present, run the research pipeline:

```bash
python -m src.run_research
```

## Data format and filename mapping

Each data file is expected to contain `Date` or `TimeStamp`, `Open`, `High`, `Low`, `Close`, and `Volume`. The research loader validates dates and OHLC values, counts missing/invalid/duplicate rows, and does not fabricate or forward-fill prices.

Ingestion normalizes characters in filenames. The research loader uses the same mapping and preserves the original symbol in outputs. For example, `M&M` is read from `M_AMP_M.csv`, and `NAM-INDIA` from `NAM_DASH_INDIA.csv`.

The supplied symbol list is used as the research universe. Symbols with insufficient price history cannot enter a momentum list until enough observations are available. Activity benchmarks remain missing until 252 prior valid observations exist.

## Understanding the outputs

All outputs are written to `output/` and recreated on each research run.

| File | What it contains | When to use it |
|---|---|---|
| `latest_broad_coverage_observations.csv` | Watchlist candidates on the newest date with at least 90% of the valid data universe present | Best daily list to share when its date and coverage are acceptable |
| `latest_observation_candidates.csv` | Candidates on the newest date found, even if only a few symbols have data | Check the newest data and its coverage; do not treat a partial date as a full-universe scan |
| `daily_watchlist.csv` | Historical 3D/6D ranks and consolidated membership for each date | Inspect a selected date or trace why a symbol entered the watchlist |
| `signal_events.csv` | Historical rows that met the combined OR activity rule | Review individual combined research signals |
| `signal_statistics.csv` | Forward-return summary by strategy and horizon | Compare historical strategy results |
| `signal_frequency.csv` | Signal counts and frequency by strategy | Compare how often each rule triggers |
| `master_daily.parquet` | Full daily feature, watchlist, signal, and forward-return panel | Efficient programmatic analysis |
| `master_daily.csv` | Same full panel in CSV format | Inspect in a spreadsheet; the file is large |
| `validation_report.csv` | Files, rows, symbols, date range, and data-quality counts | Check input quality and universe coverage |
| `plots/` | Return distributions, signal frequency, RVOL/RVAL scatter, and return comparison | Visual review of the historical research |

### Candidate-list columns

- `Selected_3D` and `Rank_3D`: whether the symbol is in the 3-day top 10 and its rank (1 is highest).
- `Selected_6D` and `Rank_6D`: the equivalent 6-day selection and rank.
- `RVOL`: daily volume divided by its average volume over the prior 252 sessions.
- `RVAL`: daily traded value (`Volume × Close`) divided by its prior-252-session average.
- `ActivityQualified`: true when the symbol is in the momentum watchlist and RVOL ≥ 2 or RVAL ≥ 2.
- `signal_reason`: `RVOL`, `RVAL`, or `RVOL_AND_RVAL` when the combined signal fires.
- `ResearchStatus`: a readable label for a momentum-only candidate versus one with activity expansion.
- `SymbolsWithData`, `ExpectedSymbols`, `CoveragePct`, and `CoverageStatus`: how much of the valid research universe has data for that date.

These labels identify candidates for observation under the research rules. They are not buy/sell recommendations.

## Strategy comparison

The historical report evaluates five variants independently:

| Strategy | Rule |
|---|---|
| Momentum | In the consolidated 3D/6D watchlist |
| RVOL | In the watchlist and RVOL ≥ 2 |
| RVAL | In the watchlist and RVAL ≥ 2 |
| OR | In the watchlist and (RVOL ≥ 2 or RVAL ≥ 2) |
| AND | In the watchlist and (RVOL ≥ 2 and RVAL ≥ 2) |

For each strategy, forward returns are measured from the signal-day close to the close 1, 3, 5, and 10 symbol trading observations later. Signal-time features use only information available by that date. Historical results are descriptive; they do not establish future performance.

## Configuration

Research parameters are centralized in `src/config.py`: top-N size, 3D/6D momentum windows, 252-session benchmark lookback, RVOL/RVAL thresholds, and forward-return horizons. The broad-coverage candidate report uses a 90% coverage threshold.

## Current limitations

- **Daily, not intraday:** the current dataset contains daily OHLCV bars. The intraday provider class is only an interface for future data; time-of-day-normalized RVOL/RVAL and continuous market monitoring are not implemented.
- **No trading execution:** there is no broker API, order placement, portfolio, position sizing, or risk management.
- **Universe history:** the symbol file represents the available/current list, not point-in-time index constituents. Historical research may therefore have survivorship bias.
- **Corporate actions:** adjustment metadata is not stored with the CSVs, so historical prices and forward returns may be affected by splits or other corporate actions.
- **Coverage varies by date:** always check `CoverageStatus` and `CoveragePct`. A newest date with only a few symbols is not a complete market scan; use the broad-coverage file for a more representative list.
- **Data-source limits:** ingestion depends on TradingView symbol resolution, session availability, and access. Failed fetches must be resolved before treating a date as complete.
