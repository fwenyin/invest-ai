---
description: Backtest a strategy on a ticker (realistic costs + walk-forward split) before you trade it.
allowed-tools: Bash, Read
argument-hint: "TICKER STRATEGY  (e.g. 'SPY ma_cross'; strategies: ma_cross, rsi_meanrev, breakout, gap_and_go)"
---

# Backtest

Run the backtest engine and interpret the result. Arguments: $ARGUMENTS

## Steps
1. If no/invalid args, run `.venv/bin/python backtest/engine.py --list` and show available strategies.
2. Otherwise run: `.venv/bin/python backtest/engine.py <TICKER> <STRATEGY> --tearsheet`
   (default 5y, fees 5bps, slippage 5bps, $10k).
3. Interpret the JSON for the human, plainly:
   - **Edge vs buy & hold** (total return).
   - **Robustness**: compare in-sample vs out-of-sample Sharpe/profit factor — large degradation = overfit.
   - **Sharpe, max drawdown, win rate, profit factor, # trades** (flag if < 20 trades = not significant).
   - State the engine's `verdict` and whether you'd trust this edge.
4. Remind: past performance ≠ future results; this is one instrument over one period — confirm across a few tickers before relying on a strategy.

Be honest about weak results. A strategy that only works in-sample is a trap.
