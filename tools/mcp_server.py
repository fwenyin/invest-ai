"""FastMCP server exposing the whole data layer to the agents as tools.

Registered in ../.mcp.json so Claude Code can call these during interactive and
scheduled runs. Each tool is a thin wrapper over the same functions the CLIs use,
so behaviour and caching are identical.

Run standalone for a smoke test:  python tools/mcp_server.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make sibling modules importable whether launched from repo root or tools/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calendar_econ
import financials
from common import err, ok
import ledger
import lt_ledger
import news
import options
import prices
import risk_gate
import substack
import trump
import valuation

from fastmcp import FastMCP

mcp = FastMCP("to-the-moon-data")


# ── Prices / technicals ──────────────────────────────────────────────
@mcp.tool
def get_quote(ticker: str) -> dict:
    """Latest price, previous close, day change %, and overnight gap % for a ticker."""
    return prices.quote(ticker)


@mcp.tool
def get_technical_snapshot(ticker: str, interval: str = "1d") -> dict:
    """Indicator snapshot: SMA/EMA, RSI, MACD, ATR, VWAP, support/resistance, trend label."""
    return prices.snapshot(ticker, interval=interval)


@mcp.tool
def get_intraday(ticker: str, interval: str = "5m") -> dict:
    """Today's intraday stats incl. opening-range high/low and session VWAP."""
    return prices.intraday(ticker, interval=interval)


@mcp.tool
def scan_gaps(tickers: list[str]) -> dict:
    """Overnight gap scan across a list of tickers, sorted by absolute gap %."""
    return prices.gaps(tickers)


@mcp.tool
def get_price_history(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    """Recent OHLCV bars (last ~120) for reasoning over price action."""
    return prices.history(ticker, period=period, interval=interval)


# ── Options ──────────────────────────────────────────────────────────
@mcp.tool
def get_options_chain(ticker: str, expiry: str = "") -> dict:
    """ATM options summary: IV, put/call OI & volume ratios for an expiry (nearest if omitted)."""
    return options.chain(ticker, expiry or None)


@mcp.tool
def get_option_expiries(ticker: str) -> dict:
    """List available option expiration dates for a ticker."""
    return options.expiries(ticker)


# ── News / catalysts ─────────────────────────────────────────────────
@mcp.tool
def get_company_news(ticker: str) -> dict:
    """Recent news headlines for a ticker (Finnhub if keyed, else Yahoo RSS)."""
    return news.company_news(ticker)


@mcp.tool
def get_market_news() -> dict:
    """Top general market news headlines."""
    return news.market_news()


@mcp.tool
def get_economic_calendar() -> dict:
    """Upcoming US economic events (FOMC/CPI/NFP...) for the next week, by impact."""
    return calendar_econ.economic()


@mcp.tool
def get_earnings_calendar() -> dict:
    """Upcoming earnings releases for the next week."""
    return calendar_econ.earnings()


@mcp.tool
def get_fundamentals(ticker: str) -> dict:
    """Structured fundamentals: valuation multiples, margins, growth, balance-sheet health, statement trend."""
    return financials.fundamentals(ticker)


# ── Alt data / sentiment ─────────────────────────────────────────────
@mcp.tool
def get_trump_posts(hours: int = 24) -> dict:
    """Recent Trump / Truth Social posts (market-moving catalyst scan)."""
    return trump.recent(hours)


@mcp.tool
def get_substack_research(limit: int = 8) -> dict:
    """Latest Bottom Up Bulletin posts via your private Substack RSS (long-term research)."""
    return substack.latest(limit)


# ── Risk gate / forward ledger ───────────────────────────────────────
@mcp.tool
def risk_gate_check(ticker: str, side: str, entry: float, stop: float, target: float,
                    sector: str = "unknown", instrument: str = "stock",
                    option_premium_per_contract: float = 0.0,
                    realized_day_pnl_pct: float = 0.0, event_blackout_active: bool = True,
                    new_trades_today: int = 0, correlated_open_count: int = 0) -> dict:
    """DETERMINISTIC risk gate: sizes an idea and PASS/FAILs it against config/risk_rules.yaml
    using the live portfolio/positions.json. A REJECTED idea must not be traded — this is the
    enforced version of the rules, not advice. Unknown context flags default to the most
    restrictive (safe) setting (e.g. blackout assumed active)."""
    idea = {"ticker": ticker, "side": side, "entry": entry, "stop": stop, "target": target,
            "sector": sector, "instrument": instrument,
            "option_premium_per_contract": option_premium_per_contract}
    ctx = {"realized_day_pnl_pct": realized_day_pnl_pct, "event_blackout_active": event_blackout_active,
           "new_trades_today": new_trades_today, "correlated_open_count": correlated_open_count}
    return risk_gate.gate(idea, ctx)


@mcp.tool
def ledger_log(session: str, ticker: str, side: str, entry: float, stop: float,
               target: float, conviction: str = "med", thesis: str = "",
               instrument: str = "stock", approved: bool = False, vetoed: bool = False) -> dict:
    """Log a desk decision to the forward ledger (portfolio/ledger.json) at decision time.
    Log EVERY idea — taken and vetoed — so the desk can later grade its own calls."""
    return ok(ledger.log_idea({
        "session": session, "ticker": ticker, "side": side, "entry": entry, "stop": stop,
        "target": target, "conviction": conviction, "thesis": thesis, "instrument": instrument,
        "approved": approved, "vetoed": vetoed,
    }))


@mcp.tool
def ledger_score(entry_id: str = "", exit_price: float = 0.0) -> dict:
    """Score open ledger entries against the actual price path → realized R, win/loss, what it hit.
    Omit entry_id to mark-to-market all open entries off live quotes; pass exit_price to override."""
    data = ledger._load()
    targets = [e for e in data["entries"] if e["status"] == "open" and (not entry_id or e["id"] == entry_id)]
    if not targets:
        return err("no matching open ledger entries to score")
    scored = []
    for e in targets:
        px = exit_price if exit_price else None
        if px is None:
            q = prices.quote(e["ticker"])
            if not q.get("ok"):
                return err(f"could not fetch price to score {e['id']}: {q.get('error')}")
            px = q["data"]["price"]
        e["outcome"] = ledger.score_entry(e, px)
        e["status"] = "scored"
        scored.append(e["id"])
    ledger._save(data)
    return ok({"scored": scored, "scorecard": ledger.report(data["entries"])})


@mcp.tool
def ledger_report() -> dict:
    """Forward-only scorecard from the decision ledger: hit rate, avg R, expectancy, profit factor."""
    return ok(ledger.report(ledger._load()["entries"]))


# ── Long-term: deterministic valuation + QQQ-benchmarked pick ledger ──
@mcp.tool
def valuation_assess(price: float, fcf: float, growth: float, shares: float,
                     net_debt: float = 0.0, discount: float = 0.10,
                     margin_of_safety: float = 0.25) -> dict:
    """DETERMINISTIC two-stage DCF for a buy-and-hold candidate: fair-value band, the growth the
    current price implies (reverse DCF), FCF yield, margin of safety, and a BUY/ACCUMULATE/WATCH/
    AVOID verdict. Supply SOURCED inputs (FCF, base-case growth as a decimal, shares, net debt =
    debt-minus-cash). The math is enforced — do not estimate intrinsic value by reasoning."""
    try:
        return ok(valuation.assess(price, fcf, growth, discount, shares, net_debt,
                                   margin_of_safety=margin_of_safety))
    except Exception as e:
        return err(f"valuation_assess failed: {e}")


@mcp.tool
def lt_ledger_log(ticker: str, verdict: str, thesis: str, entry_price: float,
                  benchmark_price_at_entry: float, fair_value_low: float = 0.0,
                  fair_value_high: float = 0.0, key_assumption: str = "",
                  thesis_indicators: list[str] | None = None) -> dict:
    """Log a long-term conviction pick to portfolio/lt_ledger.json, benchmarked vs QQQ.
    Pass the QQQ price at entry so future checkpoints can compute EXCESS return. thesis_indicators
    are 'name:baseline=..:target=..' strings — the leading metrics the thesis rides on."""
    inds = [lt_ledger._parse_indicator(s) for s in (thesis_indicators or [])]
    return ok(lt_ledger.log_pick({
        "ticker": ticker, "verdict": verdict, "thesis": thesis, "entry_price": entry_price,
        "benchmark_price_at_entry": benchmark_price_at_entry, "fair_value_low": fair_value_low,
        "fair_value_high": fair_value_high, "key_assumption": key_assumption,
        "thesis_indicators": inds,
    }))


@mcp.tool
def lt_ledger_checkpoint(entry_id: str = "") -> dict:
    """Checkpoint long-term picks against live prices + QQQ → return, benchmark return, EXCESS.
    Omit entry_id to checkpoint all picks. A pick beating QQQ has positive excess."""
    data = lt_ledger._load()
    targets = [e for e in data["entries"] if not entry_id or e["id"] == entry_id]
    if not targets:
        return err("no matching lt_ledger entries")
    try:
        bench = prices.quote(lt_ledger.BENCHMARK)
        if not bench.get("ok"):
            return err(f"could not fetch {lt_ledger.BENCHMARK}: {bench.get('error')}")
        bench_px = bench["data"]["price"]
        done = []
        for e in targets:
            q = prices.quote(e["ticker"])
            if not q.get("ok"):
                return err(f"could not fetch {e['ticker']}: {q.get('error')}")
            lt_ledger.add_checkpoint(e, q["data"]["price"], bench_px)
            done.append(e["id"])
    except Exception as ex:
        return err(f"lt_ledger_checkpoint failed: {ex}")
    lt_ledger._save(data)
    return ok({"checkpointed": done, "report": lt_ledger.report(data["entries"])})


@mcp.tool
def lt_ledger_report() -> dict:
    """How the long-term picks are doing vs QQQ: how many beating the index and average excess."""
    return ok(lt_ledger.report(lt_ledger._load()["entries"]))


if __name__ == "__main__":
    mcp.run()
