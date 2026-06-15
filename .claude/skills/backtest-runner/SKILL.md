---
name: backtest-runner
description: Run the backtest engine and interpret its result honestly before trusting a strategy. Use when asked to backtest, validate, or sanity-check a trading setup/strategy on a ticker, or to read a backtest JSON/verdict. Covers the walk-forward split, overfitting checks, and the significance bar.
---

# Backtest runner & interpretation

Validate a strategy's edge BEFORE trading it. The engine (`backtest/engine.py`) is long-only,
one position at a time, next-bar fills with realistic fees + slippage, and has **no look-ahead**
(signals use `shift(1)`; positions are shifted one bar). A 70/30 walk-forward split exposes
overfitting. Strategies: `ma_cross`, `rsi_meanrev`, `breakout`, `gap_and_go`.

## Run
```bash
.venv/bin/python backtest/engine.py --list                    # available strategies
.venv/bin/python backtest/engine.py <TICKER> <STRATEGY> --tearsheet
.venv/bin/python backtest/engine.py --universe <STRATEGY>     # run across the WHOLE universe
# defaults: 5y, fees 5bps, slippage 5bps, $10k. Result JSON → backtest/results/.
```
A single-ticker result is cherry-picked by construction. Prefer `--universe`: a rule with a real
edge works across the names the desk scans; one that only works on a single ticker is curve-fit.

## Read the JSON honestly
- **Edge vs buy & hold** — compare `full_period.total_return_pct` to `buy_hold_return_pct`.
  Beating B&H is the bar; not beating it means the strategy isn't worth the risk.
- **Robustness** — compare `in_sample` vs `out_of_sample` Sharpe and profit factor. Large
  degradation = overfit. Distrust an edge that only exists in-sample.
- **Significance** — `num_trades` < 20 → not statistically trustworthy; say so.
- **Risk-adjusted** — Sharpe/Sortino, `max_drawdown_pct`, `win_rate_pct`, `profit_factor`.
- State the engine's `verdict` field and whether you'd actually trust this edge.

## Always caveat
Past performance ≠ future results. This is one instrument over one period — confirm across a
few tickers (or use `--universe`) before relying on a strategy. A setup that only works in-sample
is a trap; be blunt about weak results rather than rationalizing them.

**Survivorship**: the universe is today's *surviving/listed* names — delisted, merged, and
bankrupt tickers are absent and the list skews to recent winners (`survivorship_warning` in every
result). Backtest returns are an **upper bound**, not an estimate. And because an LLM is in the
decision loop, a historical backtest of a rule the desk trades is contaminated by the model's
hindsight — the only clean proof of edge is the **forward** ledger scorecard (`tools/ledger.py
report`), not any backtest. See `docs/EDGE.md`.
