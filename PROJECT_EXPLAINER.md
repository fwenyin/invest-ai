# to-the-moon — Full Project Explainer

> A walkthrough of **every file** in this repo and how the pieces fit together.
> This is documentation *about* the project, not part of its runtime. Read top-to-bottom
> for the concepts, or jump to a section to look up a specific file.

---

## 1. What this project actually is

`to-the-moon` is a **multi-agent AI investment desk** that runs inside Claude Code on your own
Claude subscription. It imitates how a real trading desk works — a chain of specialists hand work
to each other:

```
analysts → bull/bear debate → trader → risk-manager → portfolio-manager → reflection
```

There are **two sleeves**:

- **Short-term desk** — runs ~5×/trading day (premarket, open, mid-morning, power hour, postmarket).
  Produces vetted, risk-checked, sized trade ideas.
- **Long-term desk** — runs weekly. Builds a buy-and-hold conviction list, fed by the *Bottom Up
  Bulletin* Substack + web research, gated by a deterministic DCF and a "must beat QQQ" hurdle.

Three principles run through the whole codebase and explain most of the design decisions:

1. **The human trades manually.** The system never places orders or assumes execution. Its output
   is *decisions, sized plans, and journals*. `portfolio/positions.json` is the human-maintained
   source of truth that the desk reconciles against.
2. **Math is code-enforced, not "reasoned" by the LLM.** Position sizing, the risk gate, DCF
   valuation, and ledger scoring all live in deterministic Python (`tools/`). The LLM *chooses
   inputs and interprets outputs* but never does the arithmetic — an LLM doing floating-point math
   is not a control.
3. **Fail loud, never guess.** If a thesis-critical feed errors (quotes, econ calendar), the desk
   marks it UNVERIFIED and stays conservative (e.g. event blackout defaults ON) rather than
   hallucinating data.

The honest thesis — *does this actually have an edge?* — is written down and held to a falsifiable
bar in [`docs/EDGE.md`](docs/EDGE.md). The whole risk + ledger apparatus exists to **prove or kill**
that thesis with forward evidence before any real money is risked.

---

## 2. The big picture — how a run flows

A **slash command** (e.g. `/premarket`) is the orchestrator. It:

1. Loads context (universe, risk rules, current positions, yesterday's lessons).
2. Runs a **data-integrity gate** (verify feeds returned real data).
3. Spawns **subagents** in sequence via the Task tool. Each subagent is a focused persona with a
   restricted toolset.
4. The subagents call the **data layer** (`tools/`) through the `to-the-moon-data` **MCP server**.
5. Deterministic **enforcement tools** (`risk_gate.py`, `ledger.py`, `valuation.py`, `lt_ledger.py`)
   do the math and logging.
6. The command writes a dated **report** to `reports/` and logs every decision to a **forward ledger**.

```
┌─────────────┐   spawns    ┌──────────────────────────────┐
│ slash cmd   │ ──────────▶ │ subagents (.claude/agents/)  │
│ (.claude/   │             │  macro, technical, news, …    │
│  commands/) │             │  bull/bear, trader, risk, PM  │
└─────┬───────┘             └───────────────┬──────────────┘
      │ reads/writes                        │ call MCP tools
      ▼                                      ▼
┌─────────────────┐            ┌──────────────────────────────┐
│ state + config  │            │ data layer (tools/*.py)       │
│ portfolio/      │◀──────────▶│ exposed via tools/mcp_server  │
│ config/         │  enforce   │  prices, news, options, …     │
│ reports/        │  tools     │  risk_gate, ledger, valuation │
└─────────────────┘            └──────────────────────────────┘
```

---

## 3. Repo layout at a glance

```
.claude/agents/      14 desk subagent personas (the "who")
.claude/commands/    9 slash-command workflows (the "when/orchestration")
.claude/skills/      2 reusable procedures (position-sizing, backtest-runner)
.claude/templates/   shared report template
.claude/settings.json shared permissions (allow/deny)
.claude/projects/…/memory/  Claude Code's own project memory (notes about YOU)
tools/               data layer + deterministic enforcement + MCP server
backtest/            self-contained backtest engine + strategies + tests
config/              risk_rules.yaml, universe.json, .env example, CA bundle
portfolio/           positions, ledgers, journal, reflection memory (state)
reports/             generated dated game plans (gitignored)
data/cache/          cached API responses (gitignored)
scripts/             install + scheduling + corp-CA helpers
docs/EDGE.md         the falsifiable edge thesis + validation bar
CLAUDE.md            project instructions Claude reads automatically
README.md            human-facing overview
PROJECT_EXPLAINER.md this file — the full file-by-file walkthrough
```

---

## 4. Top-level files

### `CLAUDE.md`
Project instructions auto-loaded into Claude's context every session. It's the condensed
operating manual: the two sleeves, how commands→agents→skills fit, where state lives, the
**rules that matter** (never approve without a stop + R:R; size via `risk_gate.py`; fail loud;
log every decision; "NO TRADE" is valid), the Python env convention (`.venv/bin/python`), and the
test commands. If you change how the desk works, this file should change too.

### `README.md`
The human-facing tour: the daily command table, the desk roster, the data layer table, the
backtest + risk engine summaries, setup steps, and scheduling notes. Functionally overlaps with
`CLAUDE.md` but aimed at a person browsing the repo.

### `PROJECT_EXPLAINER.md`
This document — a generated, file-by-file walkthrough of the whole repo. Not part of the runtime;
it's reference documentation. (Listed here for completeness, since the goal was to explain *every*
file.)

### `docs/EDGE.md`
The intellectual honesty core. It states the desk had **no inherent edge** by default (it reads
free, delayed public data an LLM can't process faster than the market) and pins down two
*falsifiable* hypotheses:
- **H1 (intraday):** fresh single-name catalysts that gap ≥2% and hold green continue 1–3 days
  often enough to be profitable net of costs — the codified proxy is the `gap_and_go` strategy.
  Edge = disciplined participation + sizing, not information.
- **H2 (long-term):** quality at a reasonable price, held with discipline, beats QQQ net of
  behaviour. Edge = structural/behavioural (long horizon kills the latency problem; low turnover
  kills costs), gated by price discipline and the QQQ hurdle.

It defines the **two gates** each must clear (cross-universe backtest + forward ledger) and the
**kill criteria**. This is *why* the risk gate and ledgers exist: to prove or kill the thesis with
forward evidence before real capital.

### `.mcp.json`
Registers the MCP server. One entry, `to-the-moon-data`, launched as
`.venv/bin/python tools/mcp_server.py`. This is what makes the `mcp__to-the-moon-data__*` tools
available to the agents.

### `requirements.txt`
Python deps: data layer (`yfinance`, `finnhub-python`, `feedparser`, `requests`, `pandas`,
`numpy`, `pyyaml`, `python-dotenv`), the MCP server (`fastmcp`), backtesting (`matplotlib`, used
only for the optional equity PNG), and `pytest`. Note: the backtest engine is intentionally pure
pandas/numpy (no vectorbt/numba) so it installs cleanly on Intel macOS without an LLVM toolchain.

### `.gitignore`
Keeps secrets and personal state out of git: `.env`, `*.key`, the machine-specific corp CA bundle,
`__pycache__`/`.venv`, regenerated artifacts (`data/cache/`, `backtest/results/`, `reports/`), and
**personal trading state** (`positions.json`, `longterm.json`, journal, `lessons.json`). Shared
rules live in `.claude/settings.json`; personal overrides in the gitignored
`.claude/settings.local.json`.

### `.env` / `config/.env.example`
`.env.example` is the committed template; you `cp` it to `.env` (gitignored). Holds
`FINNHUB_API_KEY` (free tier), the Substack credentials (`SUBSTACK_PUBLICATION` +
`SUBSTACK_SESSION_COOKIE` — a logged-in session cookie, since paid newsletters have no usable
private RSS), and `ACCOUNT_EQUITY` (kept in sync with `config/risk_rules.yaml`). The IDE currently
has `config/.env.example` open.

---

## 5. Configuration (`config/`)

### `config/risk_rules.yaml`
The **hard risk limits** enforced by `tools/risk_gate.py` on every idea. Deliberately
conservative:
- `account.equity: 10000` (keep in sync with `.env`).
- `per_trade`: ≤1% risk/trade, ≥2:1 reward-to-risk.
- `portfolio`: ≤6% open heat, ≤20% single-name, ≤35% sector, ≤3 correlated positions.
- `daily`: −3% daily-loss kill switch, ≤5 new trades/day (overtrading guard).
- `event_blackout`: no new entries within ±30 min of FOMC/CPI/NFP/PCE/PPI/Retail Sales.
- `instruments.options`: ≤5% premium at risk, no DTE <2, prefer 14–45 DTE.

These are **caps, not signals** — an idea must pass *all* checks to be approved.

### `config/universe.json`
The tradable universe the agents scan: index ETFs, the 11 sector ETFs, mega-caps, high-beta
movers, "macro tells" (futures/commodities/rates/FX/VIX), FX pairs, plus empty `watchlist` and
`earnings_watch` you can populate. The backtester's `--universe` mode pulls equity names from here.

### `config/corp-ca-bundle.pem`
A machine-specific CA bundle (gitignored, built by `scripts/setup_corp_ca.sh`) so Python's HTTPS
works behind a TLS-inspecting corporate proxy. `tools/common.py` auto-wires it if present. (See the
`corp-laptop-tls` memory note.)

---

## 6. The data layer (`tools/`)

Every module here is **dual-use**: a runnable CLI *and* a function imported by the MCP server, so
behaviour and caching are identical whether a human or an agent calls it. All return a uniform
`{"ok": true/false, ...}` envelope.

### `tools/common.py`
Shared plumbing every other tool imports:
- `ROOT`/`CACHE_DIR` paths; ensures the cache dir exists.
- `load_env()` — loads `.env` once (with a minimal parser fallback if `python-dotenv` is absent),
  then `_wire_ca_bundle()` to point `requests`/`ssl` at the corp CA bundle when needed.
- `cache_get`/`cache_set` — TTL'd JSON file cache (this is what populates `data/cache/`).
- `ok()`/`err()` — the result envelope; `emit()` — pretty-prints for CLI and exits non-zero on error.

### `tools/prices.py` (source: yfinance)
Price/technical data. `quote` (last/prev-close/day-change/gap, 60s cache), `snapshot` (full
indicator read via `indicators.py`), `intraday` (today's bars + opening-range high/low + VWAP),
`gaps` (overnight gap scan, sorted by |gap|), `history` (last ~120 OHLCV bars). CLI:
`python tools/prices.py AAPL [--intraday|--snapshot|--gaps|--history]`.

### `tools/indicators.py`
Pure-pandas technical indicators used by `prices.py` and the backtester: `sma`, `ema`, `rsi`,
`macd`, `atr`, `vwap`, naive `support_resistance`, and `snapshot()` which packages the latest-bar
values + a `_trend_label` (uptrend/downtrend/sideways from SMA20/50 vs price). No heavy deps.

### `tools/news.py` (Finnhub → free RSS fallback)
`company_news` and `market_news`. Uses Finnhub if `FINNHUB_API_KEY` is set, otherwise falls back to
free RSS (Google News search per ticker; CNBC/Yahoo/MarketWatch merged for market news), fetched
with a browser User-Agent because feeds block default agents. 15-min cache.

### `tools/calendar_econ.py` (Finnhub → Nasdaq keyless fallback)
`economic` (FOMC/CPI/NFP/PCE…) and `earnings`. Finnhub's economic endpoint is premium (403 on free
tier), so the **normal path is the keyless Nasdaq calendar**, one call per day, US events only,
tagged high/medium impact via a keyword list (`HIGH_IMPACT`) that mirrors the blackout list in
`risk_rules.yaml`. This is what the risk-manager checks to clear/confirm an event blackout. 1h cache.

### `tools/financials.py` (yfinance)
Structured fundamentals for one ticker: valuation multiples, profitability, growth, balance-sheet
health, per-share data, analyst targets, and a short `statement_trend` (last ~4 fiscal years of
revenue/net income). Feeds the fundamentals- and valuation-analysts. 6h cache (slow-moving).
Notes that Yahoo data can lag a quarter — verify thesis-critical numbers against filings.

### `tools/options.py` (yfinance, delayed)
`expiries` and `chain` — summarised ATM chain: put/call OI & volume ratios, ATM IV, the ATM call
and put rows. Feeds the sentiment-analyst's flow read. No caching (cheap, delayed).

### `tools/trump.py` (free auto-updating archive, no auth)
`recent(hours)` — Truth Social posts from a live mirror (`ix.cnn.io`, ~5-min refresh; the old
GitHub archive is frozen since 2025-10-26 and kept only as fallback — see the `trump-source-stale`
memory). Sorts newest-first, flags how many fall inside the requested window, and warns when the
freshest post is older than the window (so the agent gets latest-available context but knows it may
be stale). 15-min cache.

### `tools/substack.py` (your logged-in Substack session)
`latest(limit)` — pulls *Bottom Up Bulletin* full post bodies via the publication's JSON API,
authenticated with your `substack.sid` cookie (paid newsletters have no usable private RSS). Does a
one-time auth check; if the cookie expired, paid posts come back as previews and it attaches a
warning to refresh the cookie. Feeds the long-term research agents. 1h cache.

---

## 7. The deterministic enforcement tools (`tools/`)

These are the heart of principle #2 — **the LLM picks inputs, the code does the math.** They are
also exposed as MCP tools and have pure-function unit tests.

### `tools/risk_gate.py`
The **code-enforced risk rules**. `evaluate(idea, positions, rules, context)` is a pure function:
it sizes the idea (`shares = floor(equity * risk% / |entry−stop|)`, then caps by concentration,
always rounding DOWN), computes R:R, open heat before/after, sector exposure, and runs **every
check** (has-stop, R:R, per-trade risk, open heat, position/sector concentration, correlation,
event blackout, daily-loss kill switch, overtrading, option premium cap). It returns an
unambiguous `APPROVED` / `APPROVED (reduced size)` / `REJECTED` with the numbers and `failed_checks`.

Two critical design choices:
- **Safe defaults:** unknown context flags (blackout, day P&L, trade count, correlation) default to
  the *most restrictive* value — an omitted blackout flag is assumed ACTIVE, so nothing silently
  passes.
- **An idea with no stop is unsizable → rejected outright.**

The `risk-manager` agent may make an idea *more* conservative but **may never approve one the gate
REJECTED**. CLI: `python tools/risk_gate.py --ticker SMCI --side short --entry … --stop … --target …`.

### `tools/ledger.py`
The **forward decision ledger** (`portfolio/ledger.json`) — what lets the desk grade itself.
`log_idea` records *every* idea at decision time (taken **and** vetoed) with its plan; `score_entry`
later computes realized R, return %, win/loss/scratch, and what it hit (stop/target/timeout) against
the actual price path; `report` aggregates a **forward-only** scorecard (hit rate, avg R,
expectancy, profit factor, by-session breakdown). It deliberately refuses to call <30 scored calls
"enough" — and it's separate from `positions.json` because it measures the desk's *recommendations*,
not the human's fills. Only **scored forward** calls count; backfilled hindsight calls don't.

### `tools/valuation.py`
The **deterministic DCF** for the long-term sleeve. `two_stage_ev` (stage-1 FCF growth then a
Gordon terminal value, discounted), `fair_value_per_share`, `implied_growth` (reverse-DCF by
bisection: *what growth does the current price imply?*), `fcf_yield`, and `assess` which produces a
fair-value band, the implied growth, FCF yield, margin of safety, and a verdict
(BUY NOW / ACCUMULATE ON DIPS / WATCH / AVOID). The agent supplies sourced inputs (FCF, growth,
discount, net debt, shares) and interprets the result; an LLM-estimated intrinsic value is "the
least trustworthy number in the system," so it's pinned in code.

### `tools/lt_ledger.py`
The **long-term pick ledger** (`portfolio/lt_ledger.json`), benchmarked vs **QQQ**. `log_pick`
records a conviction pick with entry price, fair-value band, key assumption, the QQQ price at entry,
and **thesis indicators** (`name:baseline=..:target=..` — the leading metrics the thesis rides on).
`add_checkpoint`/`relative_performance` compute the pick's return, QQQ's return over the same window,
and the **excess**; `report` shows how many picks are beating QQQ and the average excess. Two ideas:
(1) the benchmark is the index, not cash — a pick that can't beat QQQ is a WATCH; (2) grade the
*thesis* (indicators) not just price, so it's falsifiable in quarters rather than years. The file
currently holds two open picks (INTU, ADBE) with no checkpoints yet.

### `tools/mcp_server.py`
The **FastMCP server** that exposes the whole data layer to the agents. Thin `@mcp.tool` wrappers
over the same functions the CLIs use, grouped: prices/technicals, options, news/catalysts,
alt-data/sentiment, the risk gate + forward ledger, and the long-term valuation + QQQ ledger. The
`ledger_score` and `lt_ledger_checkpoint` wrappers also fetch live quotes to mark entries. Registered
in `.mcp.json`. Run standalone (`python tools/mcp_server.py`) as a smoke test.

### Tests (`tools/test_*.py`, `tools/conftest.py`)
`test_risk_gate.py`, `test_ledger.py`, `test_lt_ledger.py`, `test_valuation.py` pin the
deterministic math (sizing, heat, scoring, DCF) — all pure functions, no network. `conftest.py`
just puts `tools/` on `sys.path` so `import risk_gate` works under pytest.
Run: `.venv/bin/python -m pytest tools/test_risk_gate.py tools/test_ledger.py -q`.

---

## 8. The backtest engine (`backtest/`)

Validates a strategy's edge **before** trading it — but `docs/EDGE.md` is blunt that a backtest of a
rule the LLM trades is contaminated by hindsight, so the *only clean* proof is the forward ledger.

### `backtest/engine.py`
Self-contained pandas/numpy backtester. Long-only, one position at a time, **no look-ahead**:
- `_positions` — a state machine; enter when flat on an entry, exit when long on an exit. Supports
  `max_hold` (force exit N bars **after the realized fill**, not after the signal — this is the
  correct way to express a time-based exit).
- `_simulate` — positions are `shift(1)`'d so you act *next* bar; applies fees+slippage on turnover;
  computes total return, Sharpe, Sortino, max drawdown, win rate, profit factor, # trades.
- `run` — does a **70/30 walk-forward split** (in-sample vs out-of-sample to expose overfitting),
  a buy-&-hold benchmark, an optional equity-curve PNG (`--tearsheet`), and a plain-English
  `_verdict` (needs edge over B&H **and** robust OOS **and** ≥20 trades).
- `run_universe` — runs a strategy across the *whole* `universe.json` and aggregates, because a
  single-ticker result is cherry-picked by construction. Every result carries the
  `SURVIVORSHIP_WARNING` (the universe is today's survivors → returns are an upper bound).

CLI: `python backtest/engine.py SPY ma_cross --tearsheet`, `--universe gap_and_go`, or `--list`.

### `backtest/strategies/`
Each strategy exposes `NAME`, `DESCRIPTION`, and `signals(df) -> (entries, exits)`. Signals use
`shift(1)` lookbacks (no look-ahead). Registered in `__init__.py`'s `REGISTRY`:
- `ma_cross.py` — 20/50 SMA crossover (trend following).
- `rsi_meanrev.py` — buy RSI(14)<30, exit >55 (mean reversion).
- `breakout.py` — Donchian: long above prior 20-day high, exit below prior 10-day low (momentum).
- `gap_and_go.py` — long on a >2% up-gap that closes green; exit on a red day or after `MAX_HOLD`
  bars from the fill. **This is the codified proxy for H1**, the intraday edge thesis.

### `backtest/test_engine.py`, `backtest/conftest.py`
Pins the correctness claims with pure-function tests (no network): the position state machine
enters/exits once, can't double up, **no look-ahead** (a final-bar entry earns nothing; a bar-1
entry earns bar-2-onward), costs reduce returns, trade accounting + win rate, open positions close
on the last bar, `max_hold` counts from the fill (regression for the old `entries.shift(N)` bug),
and the verdict requires edge+robustness+sample size. `conftest.py` puts `backtest/` on `sys.path`.
Run: `.venv/bin/python -m pytest backtest/test_engine.py -q`.

---

## 9. The subagents (`.claude/agents/`)

Each is a Markdown file with YAML frontmatter (`name`, `description`, `tools`) defining a focused
persona with a **restricted toolset** and a rigid output format. The command layer spawns them in
sequence. They fall into three groups.

**Short-term analysts (the "what's true now" layer):**
- `macro-strategist.md` — sets the day's **regime/bias** from futures, rates, FX, VIX, and the econ
  calendar; flags event blackouts. Doesn't pick stocks. Outputs REGIME/BIAS/KEY LEVELS/catalysts.
- `technical-analyst.md` — turns charts into **exact levels** (entry/stop/target/R:R, ATR-based
  stops). Recognises continuation/breakout/ORB/mean-reversion/gap setups. "NO TRADE" if nothing
  clean. Defers sizing to the risk-manager.
- `news-catalyst-analyst.md` — surfaces what *changed* (overnight headlines, earnings, Trump posts,
  scheduled Trump remarks as headline risk) and judges magnitude/direction/freshness/tradability.
- `sentiment-analyst.md` — reads options flow (put/call ratios, ATM IV) as a contrarian-leaning
  confirmation tool; states when sentiment confirms vs contradicts the technical/news view.
- `fundamentals-analyst.md` — light touch intraday (earnings landmines, downgrades); heavy diligence
  for the weekly run (growth/profitability/balance-sheet/valuation scored 1–5).

**Decision layer (the "what to do" pipeline):**
- `bull-researcher.md` ⇄ `bear-researcher.md` — a structured **debate**. Each uses *only* the
  analysts' gathered evidence (no inventing data), steelmans its side honestly, and rebuts the other.
- `trader.md` — converts the debate into **concrete, instrument-specific ideas** (stock/option/
  future) with entry/stop/target/R:R≥2:1. Selectivity is the job — most names are STAND ASIDE;
  "NO NEW TRADES TODAY" is valid. Does not size.
- `risk-manager.md` — the **risk gate**. Runs `tools/risk_gate.py` (never hand-computes), reports the
  verdict/size/heat/failed-checks verbatim. Can veto or cut size; can't approve what the gate
  rejected. Blackout defaults ACTIVE unless the calendar is verified clear. Leans on the
  `position-sizing` skill.
- `portfolio-manager.md` — the **final call**. Reconciles approved ideas with current holdings and
  emits THE ACTION LIST (existing positions hold/trim/add/exit, new entries, alerts, stand-aside,
  portfolio snapshot). Reconciles honestly against `positions.json`.
- `reflection-agent.md` — the desk's **memory**. At the close, journals the day to
  `portfolio/journal/<date>.md` and distills durable, specific lessons into
  `portfolio/memory/lessons.json`, anchored to the ledger's scored outcomes. Distinguishes *process*
  mistakes (fixable) from *outcome* variance. This is the compounding-edge loop.

**Long-term analysts (the weekly buy-and-hold sleeve):**
- `secular-trend-analyst.md` — multi-year themes/TAM; heavy user of Bottom Up Bulletin (as an idea
  source, not gospel); finds best-positioned beneficiaries and picks-and-shovels.
- `moat-quality-analyst.md` — durable competitive advantage, unit economics (ROIC vs WACC),
  management & capital allocation. Thinks like a long-term owner.
- `valuation-analyst.md` — the **valuation gate**. Feeds sourced inputs to `tools/valuation.py`
  (never DCFs in its head), applies the **QQQ hurdle** (a name that can't plausibly beat the index
  is WATCH, not BUY), and emits a verdict + entry zone.

---

## 10. The slash commands (`.claude/commands/`)

Each is a Markdown workflow with frontmatter (`description`, `allowed-tools`, optional
`argument-hint`). They orchestrate the agents and write reports. Names map to the Skill list the
harness surfaces.

**The five daily short-term runs (ET times via the scheduler):**
- `premarket.md` (08:30) — the big one. Loads context + yesterday's lessons, runs the **data-integrity
  gate**, then macro → scan candidates → deep-dive watchlist (technical/news/sentiment/fundamentals)
  → bull/bear debate → trader → risk-manager → portfolio-manager. **Logs every idea to the forward
  ledger**, writes `reports/daily/<date>/premarket.md` from the template, ends with a 5-line TL;DR.
- `open.md` (09:30) — execution discipline, not new ideas. Classifies pre-planned setups as
  TRIGGERED / ARMED / VOID; anti-chase reminder.
- `midmorning.md` (10:30) — manage open positions first (hold/breakeven/trim/exit); add at most 1–2
  A-quality regime-aligned setups.
- `powerhour.md` (15:00) — decide what closes today vs holds overnight; flag overnight event risk;
  re-check overnight heat.
- `postmarket.md` (16:15) — P&L review, **score the forward ledger** (`ledger.py score` then
  `report`), run the reflection-agent (journal + lessons), after-hours/tomorrow setup. Where the
  edge compounds.

**The weekly long-term run:**
- `weekly-longterm.md` (Sun) — checkpoint existing picks vs QQQ **first** (the feedback loop), then
  macro → secular-trend → moat-quality → fundamentals → valuation gate (+QQQ hurdle) → debate →
  update `portfolio/longterm.json` and log new picks to `lt_ledger`. Writes a weekly report with the
  QQQ scorecard.

**Ad-hoc / utility:**
- `backtest.md` — runs `backtest/engine.py` and interprets the JSON honestly (per the
  `backtest-runner` skill).
- `positions.md` — view or update `portfolio/positions.json` (the source of truth). Reminds you to
  keep it accurate after every fill.
- `setup.md` — guided first-time setup: disk check, `install.sh`, keys, verify the data layer,
  verify a backtest, confirm MCP, optional scheduling.

---

## 11. Skills (`.claude/skills/`)

Reusable procedures the agents/commands lean on — the **single source of truth** for their topics.
- `position-sizing/SKILL.md` — the canonical size/heat/risk-gate math and the full check list.
  Crucially: *run `tools/risk_gate.py`, don't eyeball it* — the formulas here are for **reading** the
  gate output, not replacing it. The risk-manager's reference.
- `backtest-runner/SKILL.md` — how to run the engine and read the result honestly: walk-forward
  split, edge-vs-B&H, OOS robustness, the ≥20-trades significance bar, survivorship caveat, and the
  reminder that the forward ledger — not any backtest — is the clean proof of edge.

(The harness also lists many built-in skills like `/premarket`, `/open`, etc. — those map to the
command files above.)

---

## 12. Templates, settings & Claude's project memory

### `.claude/templates/report_template.md`
The shared scannable report skeleton (TL;DR, Macro/Regime, Watchlist & Levels table, Catalysts &
Sentiment, Bull/Bear, the PM Action List, Risk Check). Lives in `templates/` (not `commands/`) so it
isn't surfaced as a slash command. The daily commands fill it in.

### `.claude/settings.json`
Shared, checked-in permissions. **Allows**: `.venv/bin/python …`, the helper scripts, all
`mcp__to-the-moon-data__*` tools, and Write/Edit to `reports/`, `portfolio/`, `backtest/results/`.
**Denies**: reading `.env`/`config/.env`/`*.key` (so secrets never leak into context). Personal
overrides go in the gitignored `.claude/settings.local.json`.

### `.claude/projects/-Users-wenyin-fun-Downloads-invest-ai/memory/`
This is **Claude Code's own persistent memory** for this project — distinct from the *desk's*
trading memory in `portfolio/memory/lessons.json`. It stores facts the assistant learned about you
and your environment, loaded into context at the start of each session. Three files:
- `MEMORY.md` — the index (one line per memory) that gets loaded each session.
- `corp-laptop-tls.md` — records that you run this on a corporate macOS laptop behind a
  TLS-inspecting proxy that breaks Python HTTPS (`CERTIFICATE_VERIFY_FAILED`), and that the fix is
  the Keychain+certifi CA bundle from `scripts/setup_corp_ca.sh`. Also flags the privacy
  consideration of running a personal trading desk on a monitored work laptop.
- `trump-source-stale.md` — records that `tools/trump.py`'s Truth Social feed is effectively stale
  (the GitHub archive stopped updating; the CNN live mirror is blocked by your proxy), so the Trump
  catalyst feed is **not reliably live** — trust the tool's `note`/`age_hours` staleness flags.

These two notes are why `tools/common.py` auto-wires a CA bundle and why `tools/trump.py` carries
the staleness warnings described in §6.

---

## 13. State (`portfolio/`)

The desk's persistent truth and memory (all gitignored except the ledger scaffolds):
- `positions.json` — **the source of truth** the human maintains; daily runs reconcile against it.
  Currently flat: $10k cash, no positions, last updated 2026-06-14.
- `ledger.json` — the forward decision ledger (short-term). Currently empty (no scored forward calls
  yet → no edge evidence yet, exactly as `docs/EDGE.md` requires before risking capital).
- `lt_ledger.json` — long-term picks vs QQQ. Holds two open picks (INTU "BUY NOW", ADBE "BUY NOW
  controversial value") logged 2026-06-15, each with thesis, fair-value band, key assumption, and
  thesis indicators — but no checkpoints yet.
- `memory/lessons.json` — the reflection memory (`{"lessons": []}` for now); `/postmarket` appends,
  `/premarket` reads it back in.
- `journal/.gitkeep` — placeholder so the journal dir exists; `<date>.md` entries land here.

---

## 14. Generated artifacts (`reports/`, `data/cache/`)

- `reports/daily/<date>/<session>.md` and `reports/weekly/<YYYY-Www>/` — the game plans the commands
  write. The repo has one sample: `reports/daily/2026-06-14/premarket.md`. (Gitignored otherwise.)
- `data/cache/*.json` — TTL'd cached API responses written by `common.cache_set`, keyed by tool +
  args: ~70 `quote_*` (incl. futures/rates/VIX like `ES=F`, `^TNX`, `^VIX`), `fundamentals_*`,
  `news_*`, `news_market`, and `trump_*`. Regenerated each run; safe to delete. One vestige —
  `reddit_wallstreetbets_stocks_options.json` — has **no matching `tools/reddit.py`** in the current
  tree (a Reddit source that was present earlier, referenced in the `corp-laptop-tls` memory note,
  but isn't wired into the data layer now); it's stale cache and can be ignored/deleted.

---

## 15. Scripts (`scripts/`)

- `install.sh` — one-shot installer: creates `.venv`, installs `requirements.txt`, scaffolds `.env`
  from the template, smoke-tests the data layer.
- `gen_schedule.py` — generates macOS **launchd** jobs for the 5 daily + 1 weekly runs. Schedule is
  defined in **US/Eastern** and auto-converted (DST-aware) to your local clock. `--install` loads the
  jobs (Mac must be awake at those times), `--uninstall` removes them, no flag = preview.
- `run_session.sh` — runs one session headlessly via `claude -p "/<session>"` with
  `--permission-mode acceptEdits`, loading `.env` and logging to `reports/logs/`. This is what
  launchd actually invokes.
- `setup_corp_ca.sh` — builds `config/corp-ca-bundle.pem` from the macOS Keychain roots + certifi so
  Python's HTTPS trusts a corporate TLS-inspection proxy; prints the env vars to export.

---

## 16. How it all connects — a worked example (`/premarket`)

1. You (or launchd via `run_session.sh`) invoke `/premarket`.
2. The command reads `config/universe.json`, `config/risk_rules.yaml`, `portfolio/positions.json`,
   the latest journal + `lessons.json`.
3. **Data-integrity gate:** it calls MCP tools (`get_quote`, `get_economic_calendar`) — if the econ
   calendar 403s, it leaves the **blackout ON** rather than guessing.
4. Spawns `macro-strategist` → regime/bias. Scans gaps/news/earnings/Trump → a 5–10 name watchlist.
5. Spawns `technical-analyst`, `news-catalyst-analyst`, `sentiment-analyst`, `fundamentals-analyst`
   on the watchlist (each calls the relevant `tools/` via MCP).
6. `bull-researcher` ⇄ `bear-researcher` debate the top candidates.
7. `trader` emits ideas with entry/stop/target/R:R.
8. `risk-manager` runs `tools/risk_gate.py` on each → APPROVED/REJECTED with size + heat. (The gate
   reads `risk_rules.yaml` + `positions.json`.)
9. `portfolio-manager` reconciles with holdings → THE ACTION LIST.
10. The command logs **every** idea (approved *and* vetoed) to `portfolio/ledger.json` via
    `tools/ledger.py`.
11. Writes `reports/daily/<date>/premarket.md` from the template; prints a 5-line TL;DR.
12. At the close, `/postmarket` runs `ledger.py score` against actual prices, the `reflection-agent`
    journals + distills lessons, and tomorrow's `/premarket` folds them back in — the learning loop.

The same skeleton, with the long-term agents and the QQQ-benchmarked `lt_ledger`, is what
`/weekly-longterm` runs.

---

## 17. The mental model to keep

- **Commands orchestrate, agents reason, tools enforce, ledgers prove.**
- The LLM is allowed to be wrong about *judgement* (which is why there's a debate and a risk gate),
  but it is **never** trusted with arithmetic or with pretending data exists.
- Nothing here is an automated trader. It's a disciplined, self-grading research-and-risk process
  whose entire reason for existing is to find out — honestly, with forward evidence — whether it has
  an edge worth real money. Until the ledgers say yes, the correct posture is paper trading.

*Not financial advice. Backtests are an upper bound; the only clean proof of edge is the forward
ledger.*
