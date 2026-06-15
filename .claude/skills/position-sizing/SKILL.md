---
name: position-sizing
description: Canonical position-sizing and risk-gate math for the desk. Use whenever sizing a trade, computing portfolio heat, or checking an idea against config/risk_rules.yaml — entry/stop/target, R:R, shares, notional, per-trade risk, and the open-heat cap. The risk-manager agent's single source of truth.
---

# Position sizing & risk-gate math

The one place the desk computes size and verifies an idea against the hard limits in
`config/risk_rules.yaml`. Keep every check tied to a number — never approve on vibes.

## Enforcement: run the code, don't eyeball it
The math below is **enforced by `tools/risk_gate.py`** (and the `risk_gate_check` MCP tool), not
by hand. An LLM approximating floating-point math is not a risk control. Always run the gate and
report its result; an idea the gate marks `REJECTED` must not be traded.
```bash
.venv/bin/python tools/risk_gate.py --ticker IWM --side long \
  --entry 291.6 --stop 289.4 --target 299 --sector financials \
  --day-pnl-pct 0 --new-trades-today 0 --correlated-open 0   # blackout assumed ACTIVE unless --no-blackout
```
Context flags (blackout / day-P&L / trades-today / correlation) default to the **most restrictive**
value when unknown — `--no-blackout` is only legitimate after the econ calendar is verified clear.
The formulas below are the reference for *reading* the gate output, not a substitute for running it.

## Inputs
- `equity` — from `account.equity` in `config/risk_rules.yaml` (kept in sync with `ACCOUNT_EQUITY`).
- `entry`, `stop`, `target` — from real chart levels (the technical-analyst's levels).
- Current open positions / heat — from `portfolio/positions.json`.

## Size formula (long example; mirror for shorts)
```
risk_per_share = abs(entry - stop)          # must be > 0; reject if no stop
shares         = floor( (equity * max_risk_pct/100) / risk_per_share )
notional       = shares * entry
trade_risk$    = shares * risk_per_share
rr             = abs(target - entry) / risk_per_share
```
**Always round shares DOWN.** A trade with no stop is unsizable → reject outright.

## Checks (mark PASS/FAIL with the number, against `risk_rules.yaml`)
- **R:R** ≥ `per_trade.min_reward_to_risk` (default 2.0).
- **Per-trade risk** `trade_risk$ / equity` ≤ `per_trade.max_risk_pct` (default 1%).
- **Open heat** after adding this trade ≤ `portfolio.max_open_heat_pct` (default 6%).
  Heat = sum of open `trade_risk$` across positions, as % of equity.
- **Concentration** single name `notional/equity` ≤ `portfolio.max_position_pct`;
  sector ≤ `portfolio.max_sector_pct`.
- **Correlation** ≤ `portfolio.max_correlated_positions` highly-correlated longs in one theme.
- **Event blackout** no new intraday entry within `event_blackout.window_minutes` of a
  `high_impact` release.
- **Daily-loss kill switch** if realized day P&L ≤ `-daily.max_loss_pct`, REJECT ALL new ideas.
- **Overtrading** ≤ `daily.max_new_trades` new entries/day.
- **Options** total premium at risk ≤ `instruments.options.max_pct_of_equity`; respect
  `avoid_dte_below` / `prefer_dte_range`.

## Doing the arithmetic
Use Python for exact figures, e.g.:
```bash
.venv/bin/python -c "import math; eq=10000; r=0.01; entry=50.0; stop=48.5; \
print(math.floor(eq*r/abs(entry-stop)))"
```

## Output
`SIZE: <shares/contracts> | notional $___ (__% equity) | risk $___ (__% equity)`, the
per-check PASS/FAIL line, and `PORTFOLIO HEAT AFTER APPROVALS: __% / <cap>%`. When in doubt,
cut size or reject — capital preservation beats FOMO.
