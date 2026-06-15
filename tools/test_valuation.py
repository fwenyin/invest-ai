"""Tests for the deterministic valuation math.

Run:  .venv/bin/python -m pytest tools/test_valuation.py -q
"""
from __future__ import annotations

import pytest

import valuation as v


def test_two_stage_ev_is_positive_and_growth_monotonic():
    lo = v.two_stage_ev(fcf=1e9, growth=0.05, discount=0.10)
    hi = v.two_stage_ev(fcf=1e9, growth=0.15, discount=0.10)
    assert 0 < lo < hi  # higher growth ⇒ higher EV


def test_discount_must_exceed_terminal_growth():
    with pytest.raises(ValueError):
        v.two_stage_ev(fcf=1e9, growth=0.05, discount=0.02, terminal_growth=0.025)


def test_implied_growth_roundtrips_against_fair_value():
    # Build a market cap from a known growth, then recover that growth.
    fcf, g, r, shares = 1e10, 0.12, 0.10, 1e9
    ev = v.two_stage_ev(fcf, g, r)
    mktcap = ev  # net_debt = 0 ⇒ EV == equity == mktcap
    recovered = v.implied_growth(mktcap, fcf, r, net_debt=0.0)
    assert recovered == pytest.approx(g, abs=1e-3)


def test_net_cash_raises_fair_value_per_share():
    base = v.fair_value_per_share(fcf=1e9, growth=0.08, discount=0.10, shares=1e8, net_debt=0.0)
    netcash = v.fair_value_per_share(fcf=1e9, growth=0.08, discount=0.10, shares=1e8, net_debt=-5e9)
    assert netcash > base  # net cash adds to equity value


def test_fcf_yield():
    assert v.fcf_yield(5e9, 1e11) == pytest.approx(0.05)


def test_assess_buy_when_price_below_fv_with_mos():
    # Price well under the conservative fair value ⇒ BUY NOW.
    res = v.assess(price=50, fcf=1e9, growth=0.10, discount=0.10, shares=1e8, net_debt=0.0)
    assert res["fair_value_low"] > res["price"]
    assert res["verdict"] == "BUY NOW"


def test_assess_avoid_when_wildly_priced():
    res = v.assess(price=5000, fcf=1e9, growth=0.10, discount=0.10, shares=1e8, net_debt=0.0)
    assert res["verdict"].startswith("AVOID")
    assert res["margin_of_safety_to_low_pct"] < 0  # price above fair value
