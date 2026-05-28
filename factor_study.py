"""
Tech-Sector Factor Study
=========================
Do simple, price-based equity factors actually work *within* the technology
sector, or are they really just bets on tech vs. the rest of the market?

This script tests three factors that can be computed from price data alone
(so there's no look-ahead bias from point-in-time fundamentals):

    1. Momentum      (12-1): last 12 months of return, skipping the most recent month
    2. Low Volatility       : low trailing-12-month daily volatility
    3. Short-Term Reversal  : last month's losers (bet they bounce)

For each factor we rank the tech universe every month, hold an equal-weighted
top-tercile portfolio, and compare it to (a) an equal-weighted basket of the
whole universe and (b) a long/short top-minus-bottom tercile portfolio.

Run:
    .venv/bin/python factor_study.py

Outputs:
    - results/cumulative_<factor>.png   growth-of-$1 charts
    - results/summary.csv               performance table
    - prints the summary table to stdout

Author: Atharva Usturge
"""

import os
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

START = "2010-01-01"
END = "2026-05-23"

# A broad slice of the US technology sector: mega-cap platforms, semiconductors,
# enterprise software, and a handful of newer names. Newer tickers simply get
# excluded from the ranking in months where they don't yet have price history.
#
# NOTE (limitation): this is *today's* tech universe, so it carries survivorship
# bias -- names that blew up and got delisted aren't here. Results should be read
# as "among tech companies that survived to 2026," not "all tech companies."
UNIVERSE = [
    # Mega-cap platforms
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA",
    # Legacy / infrastructure
    "ORCL", "IBM", "CSCO", "INTC", "HPQ", "DELL", "ACN",
    # Semiconductors
    "AMD", "QCOM", "TXN", "AVGO", "MU", "AMAT", "LRCX",
    "ADI", "KLAC", "NXPI", "MCHP", "ON",
    # Enterprise software
    "CRM", "ADBE", "NOW", "INTU", "WDAY", "SNPS", "CDNS",
    # Newer / high-growth (shorter histories)
    "PANW", "FTNT", "CRWD", "NET", "DDOG", "SNOW", "PLTR",
    "SHOP", "UBER", "PYPL",
]

TOP_FRACTION = 1.0 / 3.0   # top tercile long, bottom tercile short
TRADING_DAYS = 252
RF_ANNUAL = 0.0            # risk-free assumed 0 for simplicity (noted in writeup)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def download_prices(tickers, start, end):
    """Download daily auto-adjusted close prices. Returns a (dates x tickers) frame."""
    raw = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=True)
    close = raw["Close"].copy()
    # Drop tickers that returned no data at all.
    close = close.dropna(axis=1, how="all")
    return close.sort_index()


# ---------------------------------------------------------------------------
# Factor scores (all computed using only data available *at* the formation date)
# ---------------------------------------------------------------------------

def momentum_scores(monthly_px):
    """12-1 momentum: return from 13 months ago to 1 month ago (skip last month)."""
    return monthly_px.shift(1) / monthly_px.shift(13) - 1.0


def low_vol_scores(daily_px, month_ends):
    """Inverse trailing-12-month daily volatility, sampled at each month end.

    Higher score = lower volatility = more attractive.
    """
    daily_ret = daily_px.pct_change()
    rolling_vol = daily_ret.rolling(TRADING_DAYS, min_periods=int(TRADING_DAYS * 0.6)).std()
    vol_at_me = rolling_vol.reindex(month_ends, method="ffill")
    return -vol_at_me  # negate so "high score" means "low vol"


def reversal_scores(monthly_px):
    """Short-term reversal: last month's return, negated (losers score high)."""
    last_month_ret = monthly_px / monthly_px.shift(1) - 1.0
    return -last_month_ret


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def backtest_factor(scores, fwd_returns, top_fraction=TOP_FRACTION):
    """Given monthly factor scores and forward monthly returns, build:

        long       : equal-weight top tercile
        short       : equal-weight bottom tercile
        long_short : long minus short

    Returns a DataFrame of monthly returns for each leg.
    """
    long_ret, short_ret = [], []
    dates = []

    for date in scores.index:
        row = scores.loc[date].dropna()
        fwd = fwd_returns.loc[date].dropna() if date in fwd_returns.index else None
        if fwd is None or len(row) < 6:
            continue
        # Only rank names that have both a score and a forward return.
        common = row.index.intersection(fwd.index)
        row = row[common]
        if len(row) < 6:
            continue

        n = max(1, int(round(len(row) * top_fraction)))
        ranked = row.sort_values(ascending=False)
        winners = ranked.index[:n]
        losers = ranked.index[-n:]

        long_ret.append(fwd[winners].mean())
        short_ret.append(fwd[losers].mean())
        dates.append(date)

    out = pd.DataFrame(
        {"long": long_ret, "short": short_ret},
        index=pd.DatetimeIndex(dates),
    )
    out["long_short"] = out["long"] - out["short"]
    return out


# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------

def performance_stats(monthly_ret, rf_annual=RF_ANNUAL):
    """CAGR, annualized vol, Sharpe, max drawdown, hit rate for a monthly series."""
    r = monthly_ret.dropna()
    if len(r) == 0:
        return {}
    growth = (1 + r).prod()
    years = len(r) / 12.0
    cagr = growth ** (1 / years) - 1 if years > 0 else np.nan
    ann_vol = r.std() * np.sqrt(12)
    rf_monthly = rf_annual / 12.0
    sharpe = ((r.mean() - rf_monthly) / r.std() * np.sqrt(12)) if r.std() > 0 else np.nan

    curve = (1 + r).cumprod()
    drawdown = curve / curve.cummax() - 1
    max_dd = drawdown.min()

    return {
        "CAGR": cagr,
        "AnnVol": ann_vol,
        "Sharpe": sharpe,
        "MaxDD": max_dd,
        "HitRate": (r > 0).mean(),
        "Months": len(r),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"Downloading {len(UNIVERSE)} tickers from {START} to {END} ...")
    daily_px = download_prices(UNIVERSE, START, END)
    print(f"Got price history for {daily_px.shape[1]} names, "
          f"{daily_px.index[0].date()} to {daily_px.index[-1].date()}.")

    # Month-end prices and forward (next-month) returns.
    monthly_px = daily_px.resample("ME").last()
    month_ends = monthly_px.index
    monthly_ret = monthly_px.pct_change()
    fwd_returns = monthly_ret.shift(-1)  # return earned *after* formation date

    # Factor scores at each month end.
    factors = {
        "Momentum (12-1)": momentum_scores(monthly_px),
        "Low Volatility": low_vol_scores(daily_px, month_ends),
        "Short-Term Reversal": reversal_scores(monthly_px),
    }

    # Equal-weight benchmark: hold the whole universe, rebalanced monthly.
    bench_ret = fwd_returns.mean(axis=1).dropna()
    bench_stats = performance_stats(bench_ret)

    summary_rows = {}
    summary_rows["Equal-Weight Tech (benchmark)"] = bench_stats

    for name, scores in factors.items():
        legs = backtest_factor(scores, fwd_returns)
        long_stats = performance_stats(legs["long"])
        ls_stats = performance_stats(legs["long_short"])
        summary_rows[f"{name} - Long top 1/3"] = long_stats
        summary_rows[f"{name} - Long/Short"] = ls_stats

        # Plot: growth of $1, long-only top tercile vs benchmark.
        plot_growth(name, legs["long"], bench_ret)

    summary = pd.DataFrame(summary_rows).T
    summary = summary[["CAGR", "AnnVol", "Sharpe", "MaxDD", "HitRate", "Months"]]

    # Pretty print.
    fmt = summary.copy()
    for col in ["CAGR", "AnnVol", "MaxDD", "HitRate"]:
        fmt[col] = (fmt[col] * 100).round(1).astype(str) + "%"
    fmt["Sharpe"] = fmt["Sharpe"].round(2)
    fmt["Months"] = fmt["Months"].astype(int)

    print("\n" + "=" * 78)
    print("PERFORMANCE SUMMARY  (monthly rebalance, equal-weight, RF=0)")
    print("=" * 78)
    print(fmt.to_string())
    print("=" * 78)

    summary.to_csv(os.path.join(RESULTS_DIR, "summary.csv"))
    print(f"\nSaved table -> {os.path.join(RESULTS_DIR, 'summary.csv')}")
    print(f"Saved charts -> {RESULTS_DIR}/cumulative_*.png")


def plot_growth(factor_name, long_ret, bench_ret):
    """Save a growth-of-$1 chart comparing the factor's long leg to the benchmark."""
    df = pd.DataFrame({"factor": long_ret, "benchmark": bench_ret}).dropna()
    if df.empty:
        return
    curves = (1 + df).cumprod()

    plt.figure(figsize=(10, 5.5))
    plt.plot(curves.index, curves["factor"], label=f"{factor_name} (top 1/3)", linewidth=2)
    plt.plot(curves.index, curves["benchmark"], label="Equal-weight tech", linewidth=2,
             linestyle="--", color="gray")
    plt.yscale("log")
    plt.title(f"Growth of $1 — {factor_name} within US tech", fontsize=13, fontweight="bold")
    plt.ylabel("Growth of $1 (log scale)")
    plt.legend(loc="upper left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    safe = factor_name.split()[0].lower().replace("/", "")
    path = os.path.join(RESULTS_DIR, f"cumulative_{safe}.png")
    plt.savefig(path, dpi=130)
    plt.close()


if __name__ == "__main__":
    main()
