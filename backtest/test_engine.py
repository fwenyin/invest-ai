"""Tests for the backtest engine's correctness guarantees.

Focus: the claims the README/CLAUDE.md make — **no look-ahead bias**, next-bar
fills, and honest trade accounting. These exercise only the pure functions
(_positions, _trades, _simulate, _verdict), so they need no network/yfinance.

Run:  .venv/bin/python -m pytest backtest/test_engine.py -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import engine  # backtest/ is on sys.path via engine.py's bootstrap; see conftest


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2020-01-01", periods=n, freq="D")


def test_positions_state_machine_enters_and_exits_once():
    i = _idx(6)
    entries = pd.Series([True, True, False, False, False, False], index=i)  # 2nd entry ignored while long
    exits = pd.Series([False, False, False, True, False, True], index=i)    # 2nd exit ignored while flat
    pos = engine._positions(entries, exits)
    assert list(pos) == [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]


def test_positions_cannot_enter_when_already_long():
    i = _idx(4)
    entries = pd.Series([True, True, True, True], index=i)
    exits = pd.Series([False, False, False, False], index=i)
    pos = engine._positions(entries, exits)
    # Enters once on bar 0 and stays long; never doubles up.
    assert set(pos.unique()) <= {0.0, 1.0}
    assert list(pos) == [1.0, 1.0, 1.0, 1.0]


def test_no_lookahead_signal_on_final_bar_earns_nothing():
    """An entry on the last bar has no next bar to act on → zero PnL.

    This is the core no-look-ahead guarantee: positions are shifted one bar, so a
    signal can never capture the same bar's return.
    """
    i = _idx(5)
    close = pd.Series([100.0, 101.0, 102.0, 103.0, 130.0], index=i)  # big jump on last bar
    entries = pd.Series([False, False, False, False, True], index=i)
    exits = pd.Series([False, False, False, False, False], index=i)
    res = engine._simulate(close, entries, exits, fees=0.0, slippage=0.0, init_cash=10_000)
    # Entry on the final bar acts "next bar" which doesn't exist → no equity change.
    assert res["stats"]["total_return_pct"] == pytest.approx(0.0)


def test_next_bar_fill_captures_only_post_entry_returns():
    """Entry signal on bar 1 → position effective bar 2 → earns bar2..end moves only."""
    i = _idx(5)
    close = pd.Series([100.0, 100.0, 110.0, 121.0, 121.0], index=i)
    entries = pd.Series([False, True, False, False, False], index=i)
    exits = pd.Series([False, False, False, False, False], index=i)
    res = engine._simulate(close, entries, exits, fees=0.0, slippage=0.0, init_cash=10_000)
    # pos effective from bar 2: returns are +10% (bar2) then +10% (bar3) = 1.1*1.1 - 1 = 21%.
    assert res["stats"]["total_return_pct"] == pytest.approx(21.0, abs=1e-6)


def test_costs_reduce_returns_versus_frictionless():
    i = _idx(5)
    close = pd.Series([100.0, 100.0, 110.0, 110.0, 110.0], index=i)
    entries = pd.Series([False, True, False, False, False], index=i)
    exits = pd.Series([False, False, False, True, False], index=i)
    free = engine._simulate(close, entries, exits, 0.0, 0.0, 10_000)
    costly = engine._simulate(close, entries, exits, 0.001, 0.001, 10_000)
    assert costly["stats"]["total_return_pct"] < free["stats"]["total_return_pct"]


def test_trades_accounting_winrate_and_count():
    i = _idx(6)
    close = pd.Series([100.0, 100.0, 120.0, 120.0, 120.0, 90.0], index=i)
    pos = pd.Series([0.0, 1.0, 1.0, 0.0, 1.0, 1.0], index=i)  # win then open loser
    trades = engine._trades(close, pos, cost=0.0)
    assert len(trades) == 2
    assert trades[0] == pytest.approx(0.20)   # 100 -> 120
    assert trades[1] == pytest.approx(-0.25)  # 120 -> 90 (forced close on last bar)


def test_open_position_at_end_is_closed_on_last_bar():
    i = _idx(4)
    close = pd.Series([100.0, 110.0, 120.0, 130.0], index=i)
    pos = pd.Series([0.0, 1.0, 1.0, 1.0], index=i)  # still long at the end
    trades = engine._trades(close, pos, cost=0.0)
    assert len(trades) == 1
    assert trades[0] == pytest.approx(130.0 / 110.0 - 1)


def test_verdict_requires_edge_robustness_and_sample_size():
    good_full = {"total_return_pct": 50.0, "num_trades": 30}
    good_oos = {"sharpe": 1.2, "profit_factor": 1.5}
    assert engine._verdict(good_full, good_oos, bh=20.0).startswith("TRADEABLE EDGE")

    # Too few trades → not validated.
    assert "too few trades" in engine._verdict(
        {"total_return_pct": 50.0, "num_trades": 5}, good_oos, bh=20.0)
    # Underperforms buy & hold → not validated.
    assert "underperforms buy & hold" in engine._verdict(
        {"total_return_pct": 10.0, "num_trades": 30}, good_oos, bh=20.0)
    # Weak out-of-sample → not validated.
    assert "likely overfit" in engine._verdict(
        good_full, {"sharpe": 0.1, "profit_factor": 1.0}, bh=20.0)


def test_no_finite_blowups_on_flat_strategy():
    """A strategy that never trades must produce finite, zero-ish stats (no NaN/inf)."""
    i = _idx(10)
    close = pd.Series(np.linspace(100, 110, 10), index=i)
    flat = pd.Series([False] * 10, index=i)
    res = engine._simulate(close, flat, flat, 0.0005, 0.0005, 10_000)
    for k, v in res["stats"].items():
        assert np.isfinite(v), f"{k} not finite: {v}"
    assert res["stats"]["num_trades"] == 0
