"""Deterministic valuation math for the buy-and-hold sleeve.

The valuation-analyst used to estimate intrinsic value by reasoning — an LLM doing
a reverse-DCF in its head is the least trustworthy number in the system, and it's
the most important one. This module pins the arithmetic: a two-stage DCF, the
growth the current price is implying, FCF yield, and a margin-of-safety verdict.
The agent supplies the *inputs* (FCF, growth assumption, discount rate, net debt,
shares — sourced and stated) and *interprets* the output; it does not invent the math.

All inputs in absolute currency units (e.g. FCF and net_debt in $, shares as a count).

CLI (note: pass NEGATIVE values with '=' so argparse doesn't read them as flags,
e.g. a net-cash company is `--net-debt=-2.0e10`):
    python tools/valuation.py fair-value --price 180 --fcf 1.0e10 --growth 0.12 \
        --discount 0.10 --shares 1.0e9 --net-debt=-2.0e10
    python tools/valuation.py implied-growth --mktcap 2.0e12 --fcf 6.0e10 --discount 0.10
"""
from __future__ import annotations

import argparse

from common import emit, err, ok

DEFAULT_YEARS = 10
DEFAULT_DISCOUNT = 0.10        # required return / WACC proxy
DEFAULT_TERMINAL_GROWTH = 0.025


def two_stage_ev(fcf: float, growth: float, discount: float,
                 years: int = DEFAULT_YEARS,
                 terminal_growth: float = DEFAULT_TERMINAL_GROWTH) -> float:
    """Enterprise value from a two-stage FCF model.

    Stage 1: FCF grows at `growth` for `years`. Stage 2: Gordon terminal value at
    `terminal_growth`. Discounted at `discount`. Returns enterprise value (pre-debt).
    """
    if discount <= terminal_growth:
        raise ValueError("discount rate must exceed terminal growth")
    pv = 0.0
    cf = fcf
    for t in range(1, years + 1):
        cf = cf * (1 + growth)
        pv += cf / (1 + discount) ** t
    terminal = cf * (1 + terminal_growth) / (discount - terminal_growth)
    pv += terminal / (1 + discount) ** years
    return pv


def fair_value_per_share(fcf: float, growth: float, discount: float, shares: float,
                         net_debt: float = 0.0, years: int = DEFAULT_YEARS,
                         terminal_growth: float = DEFAULT_TERMINAL_GROWTH) -> float:
    """Intrinsic equity value per share = (EV - net_debt) / shares.

    `net_debt` is debt minus cash; a net-cash company passes a NEGATIVE net_debt.
    """
    if shares <= 0:
        raise ValueError("shares must be > 0")
    ev = two_stage_ev(fcf, growth, discount, years, terminal_growth)
    equity = ev - net_debt
    return equity / shares


def implied_growth(mktcap: float, fcf: float, discount: float, net_debt: float = 0.0,
                   years: int = DEFAULT_YEARS,
                   terminal_growth: float = DEFAULT_TERMINAL_GROWTH) -> float:
    """The stage-1 FCF growth the current price is implying (reverse DCF).

    Solves for g such that EV(g) == mktcap + net_debt, by bisection. Returns the
    implied annual growth as a decimal (0.15 = 15%). The key question for the agent:
    *is that growth realistic for this business?*
    """
    target_ev = mktcap + net_debt
    if target_ev <= 0:
        raise ValueError("implied target EV must be positive")

    def f(g: float) -> float:
        return two_stage_ev(fcf, g, discount, years, terminal_growth) - target_ev

    lo, hi = -0.50, 1.50
    flo, fhi = f(lo), f(hi)
    if flo > 0:   # even -50% growth overvalues vs price → price implies decline beyond bound
        return lo
    if fhi < 0:   # even +150% growth can't reach price → wildly priced
        return hi
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(fm) < 1e-3 or (hi - lo) < 1e-6:
            return mid
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def fcf_yield(fcf: float, mktcap: float) -> float:
    """Trailing FCF yield = FCF / market cap, as a decimal."""
    if mktcap <= 0:
        raise ValueError("mktcap must be > 0")
    return fcf / mktcap


def assess(price: float, fcf: float, growth: float, discount: float, shares: float,
           net_debt: float = 0.0, mktcap: float | None = None,
           margin_of_safety: float = 0.25, years: int = DEFAULT_YEARS,
           terminal_growth: float = DEFAULT_TERMINAL_GROWTH) -> dict:
    """Full valuation read for one name: fair value, implied growth, FCF yield, verdict.

    `growth` is the agent's (sourced, defensible) base-case stage-1 growth. Verdict
    compares price to a fair-value band built around the base case ±, with a margin
    of safety required for BUY NOW. This is a price-discipline gate, not a forecast.
    """
    mktcap = mktcap if mktcap is not None else price * shares
    fv_base = fair_value_per_share(fcf, growth, discount, shares, net_debt, years, terminal_growth)
    # Band: a conservative and an optimistic leg around the base growth assumption.
    fv_low = fair_value_per_share(fcf, max(growth - 0.03, terminal_growth + 0.001), discount,
                                  shares, net_debt, years, terminal_growth)
    fv_high = fair_value_per_share(fcf, growth + 0.03, discount, shares, net_debt, years, terminal_growth)
    lo, hi = sorted((fv_low, fv_high))
    impl_g = implied_growth(mktcap, fcf, discount, net_debt, years, terminal_growth)
    fcfy = fcf_yield(fcf, mktcap)

    mos_to_low = (lo / price - 1)            # positive ⇒ price below conservative FV
    buy_threshold = lo * (1 - margin_of_safety)
    if price <= buy_threshold:
        verdict = "BUY NOW"
    elif price <= hi:
        verdict = "ACCUMULATE ON DIPS"
    elif price <= hi * 1.25:
        verdict = "WATCH"
    else:
        verdict = "AVOID (expensive)"

    return {
        "price": round(price, 2),
        "fair_value_low": round(lo, 2),
        "fair_value_base": round(fv_base, 2),
        "fair_value_high": round(hi, 2),
        "implied_growth_pct": round(impl_g * 100, 1),
        "base_growth_pct": round(growth * 100, 1),
        "fcf_yield_pct": round(fcfy * 100, 2),
        "margin_of_safety_to_low_pct": round(mos_to_low * 100, 1),
        "suggested_entry_below": round(buy_threshold, 2),
        "verdict": verdict,
        "assumptions": {
            "discount_rate_pct": round(discount * 100, 1),
            "terminal_growth_pct": round(terminal_growth * 100, 1),
            "years": years,
            "net_debt": net_debt,
            "shares": shares,
            "required_margin_of_safety_pct": round(margin_of_safety * 100, 1),
        },
        "note": ("Inputs (FCF, growth, discount, net debt, shares) must be sourced and stated. "
                 "The verdict is price discipline, not a forecast — compare implied_growth to what "
                 "the business can realistically deliver, and still clear the QQQ hurdle (lt_ledger)."),
    }


def _cli_fair_value(a) -> dict:
    try:
        fv = fair_value_per_share(a.fcf, a.growth, a.discount, a.shares, a.net_debt,
                                  a.years, a.terminal_growth)
        if a.price is not None:
            return ok(assess(a.price, a.fcf, a.growth, a.discount, a.shares, a.net_debt,
                             margin_of_safety=a.mos, years=a.years, terminal_growth=a.terminal_growth))
        return ok({"fair_value_per_share": round(fv, 2)})
    except Exception as e:
        return err(f"fair-value failed: {e}")


def _cli_implied_growth(a) -> dict:
    try:
        g = implied_growth(a.mktcap, a.fcf, a.discount, a.net_debt, a.years, a.terminal_growth)
        return ok({"implied_growth_pct": round(g * 100, 1),
                   "fcf_yield_pct": round(fcf_yield(a.fcf, a.mktcap) * 100, 2)})
    except Exception as e:
        return err(f"implied-growth failed: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Deterministic valuation math (two-stage DCF).")
    sub = p.add_subparsers(dest="cmd", required=True)

    fv = sub.add_parser("fair-value")
    fv.add_argument("--fcf", type=float, required=True)
    fv.add_argument("--growth", type=float, required=True, help="stage-1 annual growth, decimal")
    fv.add_argument("--discount", type=float, default=DEFAULT_DISCOUNT)
    fv.add_argument("--shares", type=float, required=True)
    fv.add_argument("--net-debt", dest="net_debt", type=float, default=0.0,
                    help="debt minus cash; net-cash is negative — pass as --net-debt=-2.0e10")
    fv.add_argument("--price", type=float, default=None, help="if given, return the full assess() verdict")
    fv.add_argument("--mos", type=float, default=0.25, help="required margin of safety, decimal")
    fv.add_argument("--years", type=int, default=DEFAULT_YEARS)
    fv.add_argument("--terminal-growth", dest="terminal_growth", type=float, default=DEFAULT_TERMINAL_GROWTH)
    fv.set_defaults(func=_cli_fair_value)

    ig = sub.add_parser("implied-growth")
    ig.add_argument("--mktcap", type=float, required=True)
    ig.add_argument("--fcf", type=float, required=True)
    ig.add_argument("--discount", type=float, default=DEFAULT_DISCOUNT)
    ig.add_argument("--net-debt", dest="net_debt", type=float, default=0.0)
    ig.add_argument("--years", type=int, default=DEFAULT_YEARS)
    ig.add_argument("--terminal-growth", dest="terminal_growth", type=float, default=DEFAULT_TERMINAL_GROWTH)
    ig.set_defaults(func=_cli_implied_growth)

    args = p.parse_args()
    emit(args.func(args))
