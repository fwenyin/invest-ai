"""Long-term decision ledger — grades buy-and-hold picks against QQQ over time.

The intraday ledger (`ledger.py`) scores in days. Long-term theses take years to
resolve in price, so two things are different here:

  1. The benchmark is QQQ, not cash. A growth/quality pick only earns its keep if
     it beats just owning the index — otherwise buy the index. Every checkpoint
     records the pick's return AND QQQ's return over the same window → EXCESS.
  2. We grade the *thesis*, not only the price. Each pick logs the leading
     indicators it rides on (revenue growth, margin, ROIC, …) with a baseline and
     a target; weekly checkpoints update them, so the thesis is falsified (or
     confirmed) in quarters instead of years.

CLI:
    python tools/lt_ledger.py log --ticker NVDA --verdict "ACCUMULATE ON DIPS" \
        --thesis "AI compute compounder" --fair-low 140 --fair-high 200 \
        --key-assumption "data-center rev keeps >30% CAGR" \
        --indicator "datacenter_rev_growth:baseline=40:target=>25"
    python tools/lt_ledger.py checkpoint --id <id>        # mark vs live QQQ
    python tools/lt_ledger.py report
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from common import ROOT, emit, err, ok

LT_LEDGER = ROOT / "portfolio" / "lt_ledger.json"
BENCHMARK = "QQQ"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict:
    if not LT_LEDGER.exists():
        return {"_comment": ("Long-term pick ledger. /weekly-longterm logs each conviction pick with "
                             "its entry price, fair value, key assumption, and thesis indicators; each "
                             "weekly run checkpoints price + QQQ + indicators. A pick must BEAT QQQ "
                             "(positive excess) to justify itself — else just own the index."),
                "benchmark": BENCHMARK, "entries": []}
    return json.loads(LT_LEDGER.read_text())


def _save(data: dict) -> None:
    LT_LEDGER.write_text(json.dumps(data, indent=2))


def _gen_id(ticker: str) -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-{ticker.upper()}"


def _parse_indicator(spec: str) -> dict:
    """'name:baseline=40:target=>25' → {metric, baseline, target, latest:None}."""
    parts = dict(p.split("=", 1) for p in spec.split(":") if "=" in p)
    metric = spec.split(":", 1)[0]
    return {"metric": metric, "baseline": parts.get("baseline"),
            "target": parts.get("target"), "latest": None}


def log_pick(pick: dict) -> dict:
    rec = {
        "id": _gen_id(pick["ticker"]),
        "logged_at": _now(),
        "ticker": pick["ticker"].upper(),
        "verdict": pick.get("verdict", "WATCH"),
        "thesis": pick.get("thesis", ""),
        "entry_price": float(pick["entry_price"]),
        "fair_value_low": pick.get("fair_value_low"),
        "fair_value_high": pick.get("fair_value_high"),
        "benchmark": BENCHMARK,
        "benchmark_price_at_entry": float(pick["benchmark_price_at_entry"]),
        "key_assumption": pick.get("key_assumption", ""),
        "thesis_indicators": pick.get("thesis_indicators", []),
        "checkpoints": [],
        "status": "open",
    }
    data = _load()
    data["entries"].append(rec)
    _save(data)
    return rec


def relative_performance(entry_price: float, price: float,
                         bench_entry: float, bench_price: float) -> dict:
    """Pure: pick vs benchmark return over the same window → excess."""
    ret = (price / entry_price - 1) * 100
    bench_ret = (bench_price / bench_entry - 1) * 100
    return {
        "return_pct": round(ret, 2),
        "benchmark_return_pct": round(bench_ret, 2),
        "excess_pct": round(ret - bench_ret, 2),
        "beating_benchmark": ret > bench_ret,
    }


def add_checkpoint(rec: dict, price: float, bench_price: float,
                   indicator_updates: dict | None = None) -> dict:
    perf = relative_performance(rec["entry_price"], price, rec["benchmark_price_at_entry"], bench_price)
    cp = {"date": _now(), "price": round(float(price), 2),
          "benchmark_price": round(float(bench_price), 2), **perf}
    if indicator_updates:
        for ind in rec.get("thesis_indicators", []):
            if ind["metric"] in indicator_updates:
                ind["latest"] = indicator_updates[ind["metric"]]
        cp["indicator_updates"] = indicator_updates
    rec["checkpoints"].append(cp)
    return cp


def report(entries: list[dict]) -> dict:
    """Aggregate: how many picks are beating QQQ, and by how much."""
    checked = [e for e in entries if e.get("checkpoints")]
    rows = []
    for e in checked:
        last = e["checkpoints"][-1]
        rows.append({"ticker": e["ticker"], "verdict": e["verdict"],
                     "excess_pct": last["excess_pct"], "beating_benchmark": last["beating_benchmark"],
                     "return_pct": last["return_pct"], "benchmark_return_pct": last["benchmark_return_pct"]})
    n = len(rows)
    beating = sum(r["beating_benchmark"] for r in rows)
    avg_excess = round(sum(r["excess_pct"] for r in rows) / n, 2) if n else 0.0
    return {
        "total_logged": len(entries),
        "checkpointed": n,
        "beating_qqq": f"{beating}/{n}",
        "avg_excess_vs_qqq_pct": avg_excess,
        "per_ticker": sorted(rows, key=lambda r: r["excess_pct"], reverse=True),
        "evidence_note": (
            "Long-term theses resolve over YEARS — these excess figures are interim, not a verdict. "
            "Track the thesis_indicators (do the leading metrics confirm the assumption?) for faster "
            "feedback. If, over a full cycle, the basket can't beat QQQ on average, the honest move is "
            "to just own QQQ. LLM hindsight contaminates any backtest of long-term picks; only these "
            "forward checkpoints are evidence."),
    }


# ── CLI ──────────────────────────────────────────────────────────────
def _live_price(ticker: str):
    import prices

    q = prices.quote(ticker)
    if not q.get("ok"):
        raise RuntimeError(f"could not fetch price for {ticker}: {q.get('error')}")
    return q["data"]["price"]


def _cmd_log(a) -> dict:
    try:
        entry_price = a.entry_price if a.entry_price is not None else _live_price(a.ticker)
        bench = a.benchmark_price if a.benchmark_price is not None else _live_price(BENCHMARK)
    except Exception as e:
        return err(str(e))
    inds = [_parse_indicator(s) for s in (a.indicator or [])]
    return ok(log_pick({
        "ticker": a.ticker, "verdict": a.verdict, "thesis": a.thesis,
        "entry_price": entry_price, "benchmark_price_at_entry": bench,
        "fair_value_low": a.fair_low, "fair_value_high": a.fair_high,
        "key_assumption": a.key_assumption, "thesis_indicators": inds,
    }))


def _cmd_checkpoint(a) -> dict:
    data = _load()
    targets = [e for e in data["entries"] if not a.id or e["id"] == a.id]
    if not targets:
        return err("no matching lt_ledger entries")
    try:
        bench = a.benchmark_price if a.benchmark_price is not None else _live_price(BENCHMARK)
        done = []
        for e in targets:
            px = a.price if a.price is not None else _live_price(e["ticker"])
            add_checkpoint(e, px, bench)
            done.append(e["id"])
    except Exception as e:
        return err(str(e))
    _save(data)
    return ok({"checkpointed": done, "report": report(data["entries"])})


def _cmd_report(_a) -> dict:
    return ok(report(_load()["entries"]))


def _cmd_list(_a) -> dict:
    return ok({"entries": _load()["entries"]})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Long-term pick ledger (benchmarked vs QQQ).")
    sub = p.add_subparsers(dest="cmd", required=True)

    lg = sub.add_parser("log")
    lg.add_argument("--ticker", required=True)
    lg.add_argument("--verdict", default="WATCH")
    lg.add_argument("--thesis", default="")
    lg.add_argument("--entry-price", dest="entry_price", type=float, default=None)
    lg.add_argument("--benchmark-price", dest="benchmark_price", type=float, default=None)
    lg.add_argument("--fair-low", dest="fair_low", type=float, default=None)
    lg.add_argument("--fair-high", dest="fair_high", type=float, default=None)
    lg.add_argument("--key-assumption", dest="key_assumption", default="")
    lg.add_argument("--indicator", action="append", help="name:baseline=..:target=.. (repeatable)")
    lg.set_defaults(func=_cmd_log)

    cp = sub.add_parser("checkpoint")
    cp.add_argument("--id", default=None)
    cp.add_argument("--price", type=float, default=None)
    cp.add_argument("--benchmark-price", dest="benchmark_price", type=float, default=None)
    cp.set_defaults(func=_cmd_checkpoint)

    sub.add_parser("report").set_defaults(func=_cmd_report)
    sub.add_parser("list").set_defaults(func=_cmd_list)

    args = p.parse_args()
    emit(args.func(args))
