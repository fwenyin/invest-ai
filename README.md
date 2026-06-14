# 🚀 to-the-moon — Multi-Agent Investment Desk

A personal, AI-driven trading desk that runs on your Claude subscription. It mirrors how a
real trading desk operates — specialist analysts → bull/bear debate → trader → risk manager →
portfolio manager → reflection — across two sleeves:

- **Short-term desk** — runs 5× per trading day around the US session and produces vetted,
  risk-checked, *backtested* trade ideas for **US stocks/ETFs, options, and FX/futures**.
- **Long-term desk** — runs weekly to build a buy-and-hold conviction list, fed by the
  **Bottom Up Bulletin** Substack plus web research.

You execute trades **manually**. The desk's output is *decisions, game plans, position sizing,
and journals* — never broker orders.

> ⚠️ **Not financial advice.** Educational tooling. Backtests are not predictive. You are
> responsible for every trade you place. Start with paper trading.

---

## A trading day, automated

| Command | When (ET) | Purpose |
|---|---|---|
| `/premarket` | 08:30 | Overnight gaps/futures, econ calendar, earnings, news/Trump/Reddit + yesterday's lessons → **day's game plan** |
| `/open` | 09:30 | Opening-range read, which planned setups are triggering, anti-chase checklist |
| `/midmorning` | 10:30 | Trend confirmation, manage positions, new intraday setups |
| `/powerhour` | 15:00 | EOD positioning, close day-trades, swing hold/exit |
| `/postmarket` | 16:15 | P&L review, **journal + reflection** (updates memory), tomorrow's bias |
| `/weekly-longterm` | Sun | Buy-and-hold research + Substack themes → conviction list |
| `/backtest TICKER STRAT` | ad-hoc | vectorbt validation before you trade a setup |
| `/positions` | ad-hoc | View / update your portfolio |
| `/setup` | once | Guided install + keys + scheduling |

---

## The desk (subagents in `.claude/agents/`)

**Analysts** — `macro-strategist`, `technical-analyst`, `news-catalyst-analyst`,
`sentiment-analyst`, `fundamentals-analyst`.
**Decision layer** — `bull-researcher` ⇄ `bear-researcher` (debate) → `trader` →
`risk-manager` (sizing + veto) → `portfolio-manager` (final action list) → `reflection-agent`
(journals outcomes + lessons).
**Long-term** — `moat-quality-analyst`, `valuation-analyst`, `secular-trend-analyst`.

Each daily slash command in `.claude/commands/` orchestrates these in sequence and writes a
dated report to `reports/daily/<date>/`.

---

## Data layer (`tools/`)

One cheap key (**Finnhub** free tier) + free sources. Exposed to the agents via a local
**FastMCP** server (`tools/mcp_server.py`, registered in `.mcp.json`) and runnable as CLIs:

| Tool | Source | Notes |
|---|---|---|
| `prices.py` | yfinance | quotes, intraday, gaps, indicator snapshot |
| `options.py` | yfinance | chain, IV, put/call (delayed) |
| `news.py` | Finnhub → Yahoo RSS | company + market news |
| `calendar_econ.py` | Finnhub | econ (FOMC/CPI/NFP) + earnings calendar |
| `financials.py` | yfinance | valuation multiples, margins, growth, balance-sheet health |
| `trump.py` | free auto-updating archive (ix.cnn.io mirror) | Truth Social posts, ~5-min refresh, no auth |
| `reddit.py` | public reddit JSON | WSB/stocks/options sentiment |
| `substack.py` | your private RSS | Bottom Up Bulletin full posts |

---

## Backtesting (`backtest/`)

`engine.py` is a self-contained pandas/numpy backtester (no vectorbt/numba, so it installs
cleanly on Intel macOS) with realistic fees + slippage, a **70/30 walk-forward split**
(in-sample vs out-of-sample to expose overfitting), a buy-&-hold benchmark, an optional
equity-curve PNG, and a plain-English verdict. Strategies live in `backtest/strategies/`:
`ma_cross`, `rsi_meanrev`, `breakout`, `gap_and_go`. Signals use `shift(1)` lookbacks and
positions are shifted one bar (no look-ahead bias).

```bash
.venv/bin/python backtest/engine.py SPY ma_cross --tearsheet
.venv/bin/python backtest/engine.py --list
```

---

## Risk engine (`config/risk_rules.yaml`)

Enforced by the `risk-manager` on every idea: ≤1% risk/trade, ≤6% portfolio heat, ≥2:1 R:R,
concentration/correlation caps, **FOMC/CPI event blackouts**, and a daily-loss kill switch.
Position size = `(equity × risk%) / (entry − stop)`.

---

## Reflection memory — the compounding edge

`/postmarket` journals each day to `portfolio/journal/` and distills durable lessons into
`portfolio/memory/lessons.json`. `/premarket` loads them back in. The desk learns from its own
track record over time.

---

## Setup

```bash
# 1. Install (creates .venv, installs deps, scaffolds .env)
bash scripts/install.sh

# 2. Add your keys
#    edit .env →  FINNHUB_API_KEY,  SUBSTACK_PRIVATE_RSS,  ACCOUNT_EQUITY
#    (also set account.equity in config/risk_rules.yaml)

# 3. Verify
.venv/bin/python tools/prices.py AAPL
.venv/bin/python backtest/engine.py SPY ma_cross

# 4. Schedule the daily runs (optional; ET times auto-converted to your local tz)
python scripts/gen_schedule.py            # preview
python scripts/gen_schedule.py --install  # activate launchd jobs
```

Or just open this folder in Claude Code and run `/setup`.

### Scheduling notes
- **Local launchd (default)** — free, private, keys stay on your Mac; **requires the Mac awake**
  at those times. Generated by `scripts/gen_schedule.py`.
- **Cloud `/schedule`** — runs even when your Mac is off, but needs the repo pushed to GitHub +
  secrets in the routine. Use Claude Code's `/schedule` skill if you prefer this.
- Aligns with ~5 runs/day on a Claude Pro plan.

### Keeping state truthful
After you execute a trade, update `portfolio/positions.json` (or run `/positions add ...`).
The daily runs reconcile against it — garbage in, garbage out.

---

## Workflow each day
1. **Before open** → read `reports/daily/<today>/premarket.md`, place planned orders.
2. **Open / mid / power hour** → check the run reports, manage positions per the action lists.
3. **After close** → `/postmarket` journals results; update `positions.json` with your fills.
4. **Weekly** → `/weekly-longterm` refreshes your buy-and-hold list.

## Layout
```
.claude/agents      desk subagents          backtest/      engine + strategies + tests
.claude/commands    slash-command workflows portfolio/     positions, journal, memory
.claude/skills      reusable procedures     tools/         data layer + MCP server
.claude/templates   shared report template  config/        risk rules, universe, .env
.claude/settings.json  shared permissions   scripts/       install + scheduling
reports/            generated game plans
```

## Tests
```bash
.venv/bin/python -m pytest backtest/test_engine.py -q
```
Pins the backtest engine's correctness claims — **no look-ahead**, next-bar fills, and honest
trade accounting. Pure-function tests, so they need no network or API keys.
