#!/usr/bin/env python3
"""Shared PSX stock universe helpers.

Importing this module does NOT touch the network, so it is safe to unit-test
(unlike fetch_data.py, whose top level scrapes). fetch_data.py calls
ensure_seeds() to widen data["stocks"] to the full universe before scraping.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNI_PATH = ROOT / "scripts" / "psx_universe.json"


def load_universe(path=UNI_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ensure_seeds(data, universe=None):
    """Ensure data['stocks'] has a seed dict for every universe ticker.

    Mutates `data` in place: appends a zero-seed row for any missing ticker
    and normalises the sector label and company name on existing rows.
    Returns the yahoo->short ticker map for the scrape loop.
    """
    if universe is None:
        universe = load_universe()
    stocks = data.setdefault("stocks", [])
    by_ticker = {s["ticker"]: s for s in stocks}
    tickers = {}
    for sector, rows in universe.items():
        for r in rows:
            tickers[r["yahoo"]] = r["ticker"]
            if r["ticker"] in by_ticker:
                by_ticker[r["ticker"]]["sector"] = sector
                by_ticker[r["ticker"]]["name"] = r["name"]
            else:
                seed = {"ticker": r["ticker"], "name": r["name"], "sector": sector,
                        "price": 0, "chg1y": 0, "hi52": 0, "lo52": 0,
                        "div": 0, "yield": 0, "pe": 0}
                stocks.append(seed)
                by_ticker[r["ticker"]] = seed
    return tickers
