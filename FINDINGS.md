# Do equity factors work *inside* the tech sector?

**A first-cut study — Atharva Usturge, May 2026**

## The question

Factor investing (momentum, low-volatility, value, etc.) is usually tested
across the *whole* market. I wanted to know something narrower and, I think,
more relevant to a personalized-portfolio product: **if a client already wants
tech exposure, does tilting *within* tech by a simple factor beat just owning
the whole sector?**

## Setup

- **Universe:** 42 large US tech names (mega-cap platforms, semis, enterprise
  software, plus a few newer high-growth names). Equal-weighted.
- **Period:** Jan 2010 – May 2026, monthly rebalance.
- **Factors** (all price-based, so no look-ahead from point-in-time fundamentals):
  - **Momentum (12-1):** trailing 12-month return, skipping the most recent month
  - **Low Volatility:** low trailing-12-month daily volatility
  - **Short-Term Reversal:** last month's losers
- For each factor: hold the **top tercile** (long-only), and separately a
  **long/short** top-minus-bottom tercile. Benchmark = equal-weight whole universe.

## Results

| Strategy | CAGR | Ann Vol | Sharpe | Max DD | Hit Rate |
|---|---|---|---|---|---|
| **Equal-Weight Tech (benchmark)** | 26.8% | 21.4% | **1.23** | -37.1% | 65.8% |
| Momentum — long top 1/3 | **29.5%** | 24.6% | 1.18 | -34.5% | 61.2% |
| Momentum — long/short | 4.4% | 17.8% | 0.33 | -32.3% | 53.6% |
| Low Vol — long top 1/3 | 19.4% | **17.2%** | 1.12 | **-31.8%** | 66.1% |
| Low Vol — long/short | -18.3% | 19.3% | -0.94 | -96.3% | 41.8% |
| Reversal — long top 1/3 | 25.8% | 24.6% | 1.06 | -34.7% | 62.1% |
| Reversal — long/short | -2.2% | 15.7% | -0.06 | -57.1% | 49.2% |

(See `results/cumulative_*.png` for growth-of-$1 charts.)

## What I take away

**1. The boring answer wins on risk-adjusted return: nothing beat just owning the
basket.** The equal-weight tech sleeve had the highest Sharpe (1.23). No long-only
factor tilt improved risk-adjusted performance over this window. That's a useful
*negative* result — inside an already-strong, highly-correlated sector, there's
less cross-sectional dispersion for a factor to exploit.

**2. Momentum added raw return but not risk-adjusted return.** It earned the
highest CAGR (29.5% vs 26.8%) but at higher volatility, so the Sharpe actually
dipped. If a client cares about ending wealth and can stomach the ride, the tilt
helped; if they care about the ride, it didn't.

**3. Low-vol is the interesting one for an advisor.** It gave up ~7 points of CAGR
but delivered the lowest volatility *and* the shallowest drawdown (-31.8% vs
-37.1%). For raw performance that's a loss. But for an advisor managing a real
client's behavior, a smaller drawdown is the difference between a client holding
on and a client panic-selling at the bottom. **The "best" tilt depends on the
client's loss tolerance, not just the backtest** — which is exactly the kind of
personalization Vise exists to do.

**4. Long/short factors mostly broke down inside a single trending sector** — and
low-vol L/S was catastrophic (-96% drawdown). Shorting the highest-momentum,
highest-vol tech names during a secular bull market is a losing trade. Factors
that work *across* the market can fail badly when you confine them to one sector.

## Honest limitations

- **Survivorship bias:** this is today's tech universe, so blow-ups that got
  delisted aren't included. Real-world results would be worse.
- **No transaction costs or taxes:** monthly rebalancing isn't free, and a taxable
  advisor account would care a lot about turnover. Momentum/reversal are the
  highest-turnover here and would suffer most.
- **No fundamental factors:** I deliberately skipped value/quality because testing
  them properly needs point-in-time fundamentals (using today's numbers on past
  dates would be look-ahead bias). That's the natural next step with better data.
- **One sector, one regime:** 2010–2026 was an extraordinary period for tech. The
  conclusions might invert in a tech bear market.

## Where I'd take this next

- Add **point-in-time fundamentals** to test value & quality cleanly.
- Layer in **turnover / transaction-cost** assumptions to see which tilts survive
  net of costs (relevant for a taxable advisor account).
- Test the **low-vol tilt as a client-specific lever** — i.e., scale the defensive
  tilt to a stated loss tolerance and measure the behavioral payoff, not just CAGR.
