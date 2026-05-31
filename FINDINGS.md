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

## The advisor's dial: a risk-tolerance overlay

The low-vol finding above raises an obvious question: instead of going all-in or
all-out on the defensive tilt, what does the trade-off look like *between*?
That's the actual advisor problem — clients don't pick "defensive vs.
aggressive," they sit somewhere on a spectrum.

I built a family of blended portfolios that mix the equal-weight tech benchmark
with the low-vol tilt at 0 / 25 / 50 / 75 / 100% defensive weight:

| Blend | CAGR | Ann Vol | Sharpe | Max DD |
|---|---|---|---|---|
| 0% defensive (pure benchmark) | 27.9% | 21.4% | **1.27** | -37.1% |
| 25% defensive | 25.8% | 20.1% | 1.26 | -35.7% |
| 50% defensive | 23.7% | 18.9% | 1.23 | -34.4% |
| 75% defensive | 21.6% | 17.9% | 1.19 | -33.1% |
| 100% defensive (pure low-vol) | 19.4% | 17.2% | 1.12 | -31.8% |

(See `results/risk_tolerance_frontier.png`.)

**The interesting point: a 25% defensive tilt is almost free on Sharpe (1.27 →
1.26) but already cuts vol by 1.3 points and trims ~1.5 points of drawdown.**
That's the kind of "low-cost downside protection" knob that maps cleanly onto
how an advisor would actually personalize. Larger tilts give up more return for
diminishing risk benefit — the curve flattens.

What this *doesn't* say: it doesn't tell you the *right* weight for a given
client. That depends on stated loss tolerance, behavioral history, time horizon,
and tax situation — exactly the inputs a personalization product would take in.
But it does give a clean menu of trade-offs to choose from.

## Net of transaction costs

Turnover matters a lot for which of these is actually implementable in a taxable
advisor account. I added a one-side cost knob (round-trip = 2× one-side) and
re-ran the long-only legs at 0 / 10 / 25 bps per side:

| Factor | Avg monthly turnover | CAGR @ 0bp | CAGR @ 10bp | CAGR @ 25bp |
|---|---|---|---|---|
| Momentum (12-1) | 18% | 29.5% | 28.9% | 28.1% |
| Low Volatility | **7%** | 19.4% | 19.2% | **18.9%** |
| Short-Term Reversal | **67%** | 25.8% | 23.8% | **20.9%** |

Two things jump out:

- **Reversal looks competitive gross, but it bleeds ~5 points of CAGR at 25 bps**
  — it's the highest-turnover and the most fragile to implementation friction.
- **Low-vol is by far the most cost-friendly** (~7% monthly turnover) — it loses
  almost nothing net of costs. That reinforces the "defensive sleeve for the
  right client" angle: it's cheap to run *and* easier on the ride.

## Honest limitations

- **Survivorship bias:** this is today's tech universe, so blow-ups that got
  delisted aren't included. Real-world results would be worse.
- **Costs are a simple knob, not a model:** I'm not modeling spread, market
  impact, or taxes — just a flat one-side bps haircut on turnover.
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
