import os
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

warnings.filterwarnings("ignore")



START = "2010-01-01"
END = "2026-05-23"


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
COST_SCENARIOS_BPS = [0, 10, 25]   # one-side trading cost in basis points
DEFENSIVE_WEIGHTS = [0.0, 0.25, 0.50, 0.75, 1.0]   # weight on the defensive sleeve

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")



# Data


def download_prices(tickers, start, end):
    """Download daily auto-adjusted close prices. Returns a (dates x tickers) frame."""
    raw = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=True)
    close = raw["Close"].copy()
    # Drop tickers that returned no data at all.
    close = close.dropna(axis=1, how="all")
    return close.sort_index()



# Factor scores (all computed using only data available *at* the formation date)


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



# Backtest 


def backtest_factor(scores, fwd_returns, top_fraction=TOP_FRACTION):
    """Given monthly factor scores and forward monthly returns, build:

        long       : equal-weight top tercile
        short       : equal-weight bottom tercile
        long_short : long minus short

    Returns a DataFrame of monthly returns *and* one-side turnover per leg so
    transaction costs can be applied downstream.
    """
    long_ret, short_ret = [], []
    long_turn, short_turn = [], []
    prev_winners, prev_losers = set(), set()
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
        winners = set(ranked.index[:n])
        losers = set(ranked.index[-n:])

        # One-side turnover: fraction of names that left the portfolio.
        # First period rebalances from cash, so turnover is 1.0.
        if not prev_winners:
            l_turn, s_turn = 1.0, 1.0
        else:
            l_turn = len(prev_winners - winners) / max(len(prev_winners), 1)
            s_turn = len(prev_losers - losers) / max(len(prev_losers), 1)

        long_ret.append(fwd[list(winners)].mean())
        short_ret.append(fwd[list(losers)].mean())
        long_turn.append(l_turn)
        short_turn.append(s_turn)
        prev_winners, prev_losers = winners, losers
        dates.append(date)

    out = pd.DataFrame(
        {
            "long": long_ret,
            "short": short_ret,
            "long_turn": long_turn,
            "short_turn": short_turn,
        },
        index=pd.DatetimeIndex(dates),
    )
    out["long_short"] = out["long"] - out["short"]
    return out


def apply_costs(returns, turnover, cost_bps_one_side):
    """Subtract round-trip transaction costs from a return series.

    cost per month = 2 * one_side_turnover * (cost_bps / 10_000)
    """
    cost = 2.0 * turnover * (cost_bps_one_side / 10_000.0)
    return returns - cost


def risk_tolerance_overlay(bench_ret, defensive_ret, weights):
    """Blend the benchmark and a defensive sleeve at each weight in `weights`
    (weight on the defensive sleeve), and return a DataFrame of risk/return
    stats for each blend.

    This is the explicit "advisor dial" — pick a client's tolerance, pick a tilt.
    """
    df = pd.DataFrame({"bench": bench_ret, "def": defensive_ret}).dropna()
    rows = {}
    for w in weights:
        blended = (1 - w) * df["bench"] + w * df["def"]
        stats = performance_stats(blended)
        rows[f"{int(w*100)}% defensive"] = stats
    return pd.DataFrame(rows).T



# Performance metrics


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

    cost_table_rows = {}
    factor_legs = {}
    for name, scores in factors.items():
        legs = backtest_factor(scores, fwd_returns)
        factor_legs[name] = legs
        long_stats = performance_stats(legs["long"])
        ls_stats = performance_stats(legs["long_short"])
        summary_rows[f"{name} - Long top 1/3"] = long_stats
        summary_rows[f"{name} - Long/Short"] = ls_stats

        # Net-of-cost long-only stats across scenarios (advisor cares about long).
        avg_turn = legs["long_turn"].mean()
        cost_row = {"AvgTurnover": avg_turn}
        for bps in COST_SCENARIOS_BPS:
            net = apply_costs(legs["long"], legs["long_turn"], bps)
            stats = performance_stats(net)
            cost_row[f"CAGR@{bps}bp"] = stats["CAGR"]
            cost_row[f"Sharpe@{bps}bp"] = stats["Sharpe"]
        cost_table_rows[name] = cost_row

        # Plot: growth of $1, long-only top tercile vs benchmark.
        plot_growth(name, legs["long"], bench_ret)

    cost_table = pd.DataFrame(cost_table_rows).T

    # Risk-tolerance overlay: blend equal-weight tech with the low-vol tilt.
    # This is the "advisor dial" -- pick a client's loss tolerance, pick a tilt.
    lv_long = factor_legs["Low Volatility"]["long"]
    rt_table = risk_tolerance_overlay(bench_ret, lv_long, DEFENSIVE_WEIGHTS)
    plot_frontier(rt_table, os.path.join(RESULTS_DIR, "risk_tolerance_frontier.png"))

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

    # Pretty-print cost sensitivity.
    ct = cost_table.copy()
    for col in ct.columns:
        if col.startswith("CAGR") or col == "AvgTurnover":
            ct[col] = (ct[col] * 100).round(1).astype(str) + "%"
        elif col.startswith("Sharpe"):
            ct[col] = ct[col].round(2)

    print("\n" + "=" * 78)
    print("TRANSACTION-COST SENSITIVITY  (long-only top 1/3)")
    print("=" * 78)
    print(ct.to_string())
    print("=" * 78)
    cost_table.to_csv(os.path.join(RESULTS_DIR, "cost_sensitivity.csv"))

    # Pretty-print risk-tolerance overlay.
    rt = rt_table.copy()
    for col in ["CAGR", "AnnVol", "MaxDD", "HitRate"]:
        rt[col] = (rt[col] * 100).round(1).astype(str) + "%"
    rt["Sharpe"] = rt["Sharpe"].round(2)
    rt["Months"] = rt["Months"].astype(int)
    rt = rt[["CAGR", "AnnVol", "Sharpe", "MaxDD", "HitRate", "Months"]]

    print("\n" + "=" * 78)
    print("RISK-TOLERANCE OVERLAY  (blend: tech benchmark + low-vol tilt)")
    print("=" * 78)
    print(rt.to_string())
    print("=" * 78)
    rt_table.to_csv(os.path.join(RESULTS_DIR, "risk_tolerance.csv"))

    print(f"\nSaved tables  -> {RESULTS_DIR}/summary.csv, cost_sensitivity.csv, risk_tolerance.csv")
    print(f"Saved charts  -> {RESULTS_DIR}/cumulative_*.png, risk_tolerance_frontier.png")


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


def plot_frontier(rt_table, outpath):
    """Plot the risk-tolerance frontier: annualized vol vs CAGR for each blend."""
    if rt_table.empty:
        return

    vols = rt_table["AnnVol"].values * 100
    cagrs = rt_table["CAGR"].values * 100
    labels = rt_table.index.tolist()

    plt.figure(figsize=(9, 6))
    plt.plot(vols, cagrs, "-", color="steelblue", linewidth=2, alpha=0.7, zorder=1)
    plt.scatter(vols, cagrs, s=110, c="steelblue", edgecolor="white",
                linewidth=1.5, zorder=2)

    for x, y, lbl in zip(vols, cagrs, labels):
        plt.annotate(lbl, (x, y), textcoords="offset points",
                     xytext=(10, -4), fontsize=10)

    plt.xlabel("Annualized volatility (%)")
    plt.ylabel("CAGR (%)")
    plt.title("Risk-Tolerance Frontier — Tech Benchmark blended with Low-Vol Tilt",
              fontsize=12, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=130)
    plt.close()


if __name__ == "__main__":
    main()
