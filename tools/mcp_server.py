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
import news
import options
import prices
import reddit
import substack
import trump

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
def get_reddit_sentiment(subs: list[str] | None = None) -> dict:
    """Hot posts + ticker-mention counts from r/wallstreetbets, r/stocks, r/options."""
    return reddit.hot(subs)


@mcp.tool
def get_substack_research(limit: int = 8) -> dict:
    """Latest Bottom Up Bulletin posts via your private Substack RSS (long-term research)."""
    return substack.latest(limit)


if __name__ == "__main__":
    mcp.run()
