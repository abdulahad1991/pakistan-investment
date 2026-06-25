import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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
