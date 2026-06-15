"""Tests for the long-term ledger's pure performance/report logic (no I/O).

Run:  .venv/bin/python -m pytest tools/test_lt_ledger.py -q
"""
from __future__ import annotations

import pytest

import lt_ledger as L


def test_relative_performance_beats_benchmark():
    perf = L.relative_performance(entry_price=100, price=130, bench_entry=400, bench_price=440)
    assert perf["return_pct"] == pytest.approx(30.0)
    assert perf["benchmark_return_pct"] == pytest.approx(10.0)
    assert perf["excess_pct"] == pytest.approx(20.0)
    assert perf["beating_benchmark"] is True


def test_relative_performance_lags_benchmark():
    perf = L.relative_performance(entry_price=100, price=105, bench_entry=400, bench_price=440)
    assert perf["excess_pct"] == pytest.approx(-5.0)
    assert perf["beating_benchmark"] is False


def test_add_checkpoint_updates_indicators():
    rec = {"entry_price": 100, "benchmark_price_at_entry": 400, "checkpoints": [],
           "thesis_indicators": [{"metric": "rev_growth", "baseline": "40", "target": ">25", "latest": None}]}
    cp = L.add_checkpoint(rec, price=120, bench_price=420, indicator_updates={"rev_growth": "32"})
    assert cp["excess_pct"] == pytest.approx(20.0 - 5.0)
    assert rec["thesis_indicators"][0]["latest"] == "32"
    assert len(rec["checkpoints"]) == 1


def test_report_aggregates_latest_checkpoint_vs_qqq():
    entries = [
        {"ticker": "A", "verdict": "BUY NOW", "checkpoints": [
            {"excess_pct": 12.0, "beating_benchmark": True, "return_pct": 22, "benchmark_return_pct": 10}]},
        {"ticker": "B", "verdict": "WATCH", "checkpoints": [
            {"excess_pct": -8.0, "beating_benchmark": False, "return_pct": 2, "benchmark_return_pct": 10}]},
        {"ticker": "C", "verdict": "BUY NOW", "checkpoints": []},  # not yet checkpointed
    ]
    rep = L.report(entries)
    assert rep["total_logged"] == 3
    assert rep["checkpointed"] == 2
    assert rep["beating_qqq"] == "1/2"
    assert rep["avg_excess_vs_qqq_pct"] == pytest.approx(2.0)
    assert rep["per_ticker"][0]["ticker"] == "A"  # sorted by excess desc


def test_parse_indicator_spec():
    ind = L._parse_indicator("datacenter_rev_growth:baseline=40:target=>25")
    assert ind["metric"] == "datacenter_rev_growth"
    assert ind["baseline"] == "40"
    assert ind["target"] == ">25"
    assert ind["latest"] is None
