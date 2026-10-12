"""Small optional plotting helpers for daily signal research."""

from pathlib import Path

import pandas as pd


def create_research_plots(frame: pd.DataFrame, statistics: pd.DataFrame, output_dir: str | Path) -> list[Path]:
    """Write return histograms, signal frequency, and RVOL/RVAL scatter when matplotlib exists."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Research plots require matplotlib; it is not included in the configured environment.") from exc
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    outputs = []
    for horizon in (1, 3, 5, 10):
        col = f"ForwardReturn_{horizon}D"
        fig, ax = plt.subplots(figsize=(9, 5))
        for strategy, signal_col in (("Momentum", "signal_momentum"), ("RVOL", "signal_rvol"), ("RVAL", "signal_rval"), ("OR", "signal_or"), ("AND", "signal_and")):
            values = frame.loc[frame[signal_col], col].dropna()
            if len(values): ax.hist(values, bins=60, alpha=.28, density=True, label=strategy)
        ax.set(title=f"{horizon}D forward return distribution", xlabel="Forward return", ylabel="Density")
        ax.legend(); fig.tight_layout()
        path = root / f"forward_return_{horizon}d.png"; fig.savefig(path, dpi=140); plt.close(fig); outputs.append(path)
    counts = frame.groupby("Date")[["signal_momentum", "signal_rvol", "signal_rval", "signal_or", "signal_and"]].sum()
    ax = counts.plot(figsize=(11, 5), title="Research signals over time"); ax.set_ylabel("Signals")
    path = root / "signal_frequency.png"; ax.figure.tight_layout(); ax.figure.savefig(path, dpi=140); plt.close(ax.figure); outputs.append(path)
    labels = {"Momentum": "signal_momentum", "RVOL": "signal_rvol", "RVAL": "signal_rval", "OR": "signal_or", "AND": "signal_and"}
    horizons = (1, 3, 5, 10)
    fig, ax = plt.subplots(figsize=(9, 5))
    for strategy, signal_col in labels.items():
        means = [frame.loc[frame[signal_col], f"ForwardReturn_{h}D"].mean() for h in horizons]
        ax.plot(horizons, means, marker="o", label=strategy)
    ax.set(title="Mean forward return by holding horizon", xlabel="Trading days ahead", ylabel="Mean forward return")
    ax.legend(); fig.tight_layout()
    path = root / "mean_forward_return_comparison.png"; fig.savefig(path, dpi=140); plt.close(fig); outputs.append(path)
    sample = frame.loc[frame["in_watchlist"] & frame["RVOL"].notna() & frame["RVAL"].notna()]
    fig, ax = plt.subplots(figsize=(7, 6)); points = ax.scatter(sample.RVOL, sample.RVAL, c=sample.signal_or, alpha=.45, s=10, cmap="coolwarm")
    ax.set(xscale="log", yscale="log", xlabel="RVOL", ylabel="RVAL", title="RVOL vs RVAL (watchlist)"); fig.colorbar(points, ax=ax, label="OR signal")
    path = root / "rvol_rval_scatter.png"; fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig); outputs.append(path)
    return outputs
