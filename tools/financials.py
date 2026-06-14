"""Company fundamentals via yfinance (free, no key): valuation multiples,
profitability, growth, balance-sheet health, and a short statement trend.

Feeds the fundamentals-analyst and valuation-analyst — the structured anchor the
desk was missing (the calendar only carries *forward* estimates, not actuals).
Numbers are point-in-time from Yahoo and can lag a quarter; treat as a starting
read, confirm anything thesis-critical against the latest filing.
CLI:  python tools/financials.py AAPL
      python tools/financials.py NVDA AMD MSFT
"""
from __future__ import annotations

import argparse

from common import cache_get, cache_set, emit, err, ok


def _pct(x) -> float | None:
    """Yahoo reports margins/growth as fractions (0.23 → 23.0%)."""
    return round(float(x) * 100, 2) if isinstance(x, (int, float)) else None


def _num(x, nd: int = 2) -> float | None:
    return round(float(x), nd) if isinstance(x, (int, float)) else None


def _statement_trend(tk) -> list[dict]:
    """Last few fiscal years of revenue / net income, newest first. Best-effort."""
    try:
        stmt = tk.income_stmt
        if stmt is None or stmt.empty:
            return []
    except Exception:
        return []

    def _row(*names):
        for n in names:
            if n in stmt.index:
                return stmt.loc[n]
        return None

    rev = _row("Total Revenue", "TotalRevenue")
    ni = _row("Net Income", "NetIncome", "Net Income Common Stockholders")
    if rev is None:
        return []
    out = []
    for col in list(stmt.columns)[:4]:
        period = getattr(col, "year", None) or str(col)[:10]
        out.append({
            "period": str(period),
            "revenue": _num(rev.get(col), 0) if rev is not None else None,
            "net_income": _num(ni.get(col), 0) if ni is not None else None,
        })
    return out


def fundamentals(ticker: str) -> dict:
    """Structured fundamental snapshot for one ticker."""
    cached = cache_get(f"fundamentals_{ticker}", ttl_seconds=21600)  # 6h — slow-moving
    if cached:
        return cached
    try:
        import yfinance as yf

        tk = yf.Ticker(ticker)
        info = tk.info or {}
        if not info.get("symbol") and not info.get("shortName") and not info.get("longName"):
            return err(f"no fundamentals for {ticker} (unknown symbol or no data)")

        mcap = info.get("marketCap")
        fcf = info.get("freeCashflow")
        fcf_yield = _pct(fcf / mcap) if isinstance(fcf, (int, float)) and isinstance(mcap, (int, float)) and mcap else None

        out = ok({
            "ticker": ticker.upper(),
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "currency": info.get("currency"),
            "market_cap": mcap,
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),

            "valuation": {
                "trailing_pe": _num(info.get("trailingPE")),
                "forward_pe": _num(info.get("forwardPE")),
                "peg_ratio": _num(info.get("trailingPegRatio") or info.get("pegRatio")),
                "price_to_sales": _num(info.get("priceToSalesTrailing12Months")),
                "price_to_book": _num(info.get("priceToBook")),
                "ev_to_ebitda": _num(info.get("enterpriseToEbitda")),
                "ev_to_revenue": _num(info.get("enterpriseToRevenue")),
                "fcf_yield_pct": fcf_yield,
            },
            "profitability": {
                "gross_margin_pct": _pct(info.get("grossMargins")),
                "operating_margin_pct": _pct(info.get("operatingMargins")),
                "net_margin_pct": _pct(info.get("profitMargins")),
                "roe_pct": _pct(info.get("returnOnEquity")),
                "roa_pct": _pct(info.get("returnOnAssets")),
            },
            "growth": {
                "revenue_growth_pct": _pct(info.get("revenueGrowth")),
                "earnings_growth_pct": _pct(info.get("earningsGrowth")),
                "earnings_q_growth_pct": _pct(info.get("earningsQuarterlyGrowth")),
            },
            "balance_sheet": {
                "total_cash": info.get("totalCash"),
                "total_debt": info.get("totalDebt"),
                "debt_to_equity": _num(info.get("debtToEquity")),
                "current_ratio": _num(info.get("currentRatio")),
                "quick_ratio": _num(info.get("quickRatio")),
                "free_cash_flow": fcf,
                "operating_cash_flow": info.get("operatingCashflow"),
            },
            "per_share": {
                "trailing_eps": _num(info.get("trailingEps")),
                "forward_eps": _num(info.get("forwardEps")),
                "book_value": _num(info.get("bookValue")),
                # yfinance (>=0.2.x / 1.x) returns dividendYield already as a percent
                # (0.49 = 0.49%), unlike payoutRatio which is still a fraction.
                "dividend_yield_pct": _num(info.get("dividendYield")),
                "payout_ratio_pct": _pct(info.get("payoutRatio")),
            },
            "analyst": {
                "target_mean": _num(info.get("targetMeanPrice")),
                "recommendation": info.get("recommendationKey"),
                "num_opinions": info.get("numberOfAnalystOpinions"),
            },
            "statement_trend": _statement_trend(tk),
        })
        cache_set(f"fundamentals_{ticker}", out)
        return out
    except Exception as e:
        return err(f"fundamentals failed for {ticker}: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("tickers", nargs="+")
    a = p.parse_args()
    emit({t: fundamentals(t) for t in a.tickers} if len(a.tickers) > 1 else fundamentals(a.tickers[0]))
