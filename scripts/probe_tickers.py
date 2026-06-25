#!/usr/bin/env python3
"""Probe every Yahoo symbol in psx_universe.json; report which resolve.
yfinance is CI-only; install on demand so this runs locally too."""
import json, subprocess, sys
from pathlib import Path

def _install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

try:
    import yfinance as yf
except ImportError:
    _install("yfinance"); import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
uni = json.loads((ROOT / "scripts/psx_universe.json").read_text())

bad = []
for sector, rows in uni.items():
    for r in rows:
        sym = r["yahoo"]
        try:
            h = yf.Ticker(sym).history(period="1mo")
            status = "OK" if not h.empty else "EMPTY"
        except Exception as e:  # noqa
            status = f"ERROR:{type(e).__name__}"
        if status != "OK":
            bad.append((sector, sym, status))
        print(f"{status:14s} {sym:12s} {r['name']}")

print(f"\n{len(bad)} symbol(s) need attention:")
for sector, sym, status in bad:
    print(f"  [{sector}] {sym} -> {status}")
