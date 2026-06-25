import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

def test_universe_wellformed():
    uni = json.loads((ROOT / "scripts/psx_universe.json").read_text())
    assert isinstance(uni, dict)
    # the four content sectors must exist with >= 5 names each
    for sec in ["Automobile", "Technology", "FMCG", "Textile"]:
        assert sec in uni, f"missing sector {sec}"
        assert len(uni[sec]) >= 5, f"{sec} has too few names"
    # every entry has the three required keys and a .KA yahoo symbol
    seen = set()
    for sec, rows in uni.items():
        for r in rows:
            assert {"ticker", "name", "yahoo"} <= r.keys(), r
            assert r["yahoo"].endswith(".KA"), r
            assert r["ticker"] not in seen, f"duplicate ticker {r['ticker']}"
            seen.add(r["ticker"])
    assert len(seen) >= 80, "universe should be comprehensive (>= 80 names)"


def test_ensure_seeds_real_function():
    from stock_universe import ensure_seeds, load_universe
    uni = load_universe()
    tickers = {r["ticker"] for rows in uni.values() for r in rows}
    yahoos = {r["yahoo"] for rows in uni.values() for r in rows}
    data = {"stocks": []}
    tmap = ensure_seeds(data, uni)
    assert {s["ticker"] for s in data["stocks"]} == tickers
    assert set(tmap.keys()) == yahoos and set(tmap.values()) == tickers
    # idempotent: a second call adds nothing
    before = len(data["stocks"])
    ensure_seeds(data, uni)
    assert len(data["stocks"]) == before
    # existing live row keeps its values but gets sector/name normalised
    data2 = {"stocks": [{"ticker": "FFC", "name": "old", "sector": "old",
                         "price": 555.6, "chg1y": 45.7, "hi52": 0, "lo52": 0,
                         "div": 0, "yield": 0, "pe": 0}]}
    ensure_seeds(data2, uni)
    ffc = next(s for s in data2["stocks"] if s["ticker"] == "FFC")
    assert ffc["price"] == 555.6            # live value preserved
    assert ffc["sector"] == "Fertilizer"   # normalised from universe
    assert ffc["name"] == "Fauji Fertilizer"
