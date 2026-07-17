#!/usr/bin/env python3
"""Orchestrate the per-category fetchers, then merge into data.json.

Usage:  python run_fetchers.py [group]

Groups (cadence-aware so we don't hammer slow/monthly sources):
  open    — fast intraday refresh (market open): prices, fx, gold, kse
  close   — full refresh (market close): everything, incl. per-stock
            fundamentals + dividends + monthly/event sources
  weekend — Sat/Sun refresh: only sources that move while PSX is shut
            (gold — Sarafa fixes a rate on Saturday — and open-market fx)
  all     — run every fetcher (default; used for manual/backfill runs)

Each fetcher runs through base.run(), which writes its partition with graceful
fallback (a failure keeps the prior value, flagged ok=False). build_data.merge()
then overlays the partitions onto the curated data.json. One fetcher failing
never blocks the others or the merge — that isolation is the whole point of the
split.
"""
import sys
import json
from pathlib import Path

from fetchers.base import run, ROOT
from fetchers import (cpi, reserves, policy, savings, forex, funds, gold, kse,
                      stocks, dividends, macro, petrol)
import build_data


def _displayed_symbols():
    """PSX tickers the site actually displays (drives stock + dividend enrich)."""
    try:
        data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
        return [s["ticker"] for s in data.get("stocks", []) if s.get("ticker")]
    except Exception:  # noqa: BLE001
        return None


# name -> (module, thunk). Module.NAME is the partition filename.
def _registry():
    syms = _displayed_symbols()
    return {
        cpi.NAME:       (cpi,       lambda: cpi.fetch()),
        reserves.NAME:  (reserves,  lambda: reserves.fetch()),
        policy.NAME:    (policy,    lambda: policy.fetch()),
        savings.NAME:   (savings,   lambda: savings.fetch()),
        forex.NAME:     (forex,     lambda: forex.fetch()),
        funds.NAME:     (funds,     lambda: funds.fetch()),
        gold.NAME:      (gold,      lambda: gold.fetch()),
        kse.NAME:       (kse,       lambda: kse.fetch()),
        macro.NAME:     (macro,     lambda: macro.fetch()),
        petrol.NAME:    (petrol,    lambda: petrol.fetch()),
        # stocks: open run = prices + a few headline fundamentals (fast);
        #         close run = prices + fundamentals for the whole universe.
        stocks.NAME:    (stocks,    lambda: stocks.fetch()),
        dividends.NAME: (dividends, lambda: dividends.fetch(symbols=syms)),
    }


GROUPS = {
    "open":    [forex.NAME, gold.NAME, kse.NAME, stocks.NAME, petrol.NAME],
    "close":   [forex.NAME, gold.NAME, kse.NAME, stocks.NAME, dividends.NAME,
                funds.NAME, reserves.NAME, cpi.NAME, policy.NAME, savings.NAME,
                macro.NAME, petrol.NAME],
    # Fuel is govt-set daily and PSX-independent, so it refreshes on weekends too.
    "weekend": [forex.NAME, gold.NAME, petrol.NAME],
}


def main(group="all"):
    # 'history' rebuilds data/stock_history.json (weekly; feeds the dividend
    # page + backtester). Heavy per-symbol EOD pull — kept off the daily path.
    if group == "history":
        syms = _displayed_symbols() or []
        print(f"== stock history: {len(syms)} symbols ==")
        stocks.fetch_history(syms)
        print("== done ==")
        return

    reg = _registry()
    syms = _displayed_symbols()
    # On the close run, enrich fundamentals for the whole displayed universe.
    if group in ("close", "all") and syms:
        reg[stocks.NAME] = (stocks, lambda: stocks.fetch(enrich=syms))

    names = GROUPS.get(group, list(reg))
    print(f"== fetchers: group '{group}' ({len(names)} sources) ==")
    for name in names:
        mod, thunk = reg[name]
        run(name, thunk)

    print("== merge ==")
    build_data.merge()
    print("== done ==")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
