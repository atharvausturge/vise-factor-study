# Tech-Sector Factor Study

A small research project: **do simple price-based equity factors (momentum,
low-volatility, short-term reversal) add value *within* the US technology
sector, or are they really just a bet on tech vs. the rest of the market?**

Read [`FINDINGS.md`](FINDINGS.md) for the writeup and conclusions.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python factor_study.py
```

This downloads ~16 years of daily prices for 42 tech names (via `yfinance`),
ranks them every month by each factor, backtests equal-weight top-tercile and
long/short portfolios, and writes:

- `results/summary.csv` — performance table
- `results/cumulative_*.png` — growth-of-$1 charts

## Method notes

- All factors are computed from price data only, so there's **no look-ahead
  bias** from point-in-time fundamentals.
- Monthly rebalance, equal-weight, risk-free rate assumed 0.
- Known limitations (survivorship bias, no transaction costs, no fundamental
  factors, single sector/regime) are spelled out in `FINDINGS.md`.

Built by Atharva Usturge.
