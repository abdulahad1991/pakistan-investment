#!/usr/bin/env python3
"""DEPRECATED — superseded by the fetchers/ package + build_data.py.

The old monolith fetched every source inline (yfinance for PSX, fragile regex
scrapes) and silently froze stale values via a blanket try/except — inflation
was never even fetched. It has been replaced by single-responsibility fetchers
(fetchers/*.py), each with a fixture-tested parser, that write provenance-wrapped
partitions merged by build_data.py with staleness flags.

This shim stays only so `python fetch_data.py` still works and CANNOT clobber
data.json with the old yfinance data — it just delegates to the new pipeline.
Use `python run_fetchers.py [open|close|history|all]` directly instead.
"""
import sys

if __name__ == "__main__":
    print("fetch_data.py is deprecated — delegating to run_fetchers.py (all).")
    import run_fetchers
    run_fetchers.main(sys.argv[1] if len(sys.argv) > 1 else "all")
