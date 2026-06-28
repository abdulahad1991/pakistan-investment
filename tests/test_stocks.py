"""Unit tests for the PSX stocks fetcher parsers.

Pure-string parsers run against real captured fixtures — no network.
"""
from pathlib import Path

from fetchers.stocks import parse_market_watch, parse_company, parse_eod_monthly

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name):
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


def test_market_watch_bulk_feed():
    data = parse_market_watch(_read("psx_market_watch.html"))

    # One response should carry the whole actively-traded market.
    assert isinstance(data, dict)
    assert len(data) > 100
    assert len(data) == 488  # exact symbol count in this fixture

    # OGDC present with a sane CURRENT (last) price.
    assert "OGDC" in data
    ogdc = data["OGDC"]
    assert 330 <= ogdc["price"] <= 345
    assert ogdc["price"] == 339.96
    assert ogdc["ldcp"] == 338.17
    assert ogdc["change"] == 1.79
    assert ogdc["pct"] == 0.53
    assert ogdc["volume"] == 3779720

    # Well-known blue chips are all present.
    for sym in ("LUCK", "HBL", "MEBL"):
        assert sym in data

    # Negative-change row parses with the correct sign.
    ssgc = data["SSGC"]
    assert ssgc["price"] == 32.04
    assert ssgc["change"] == -0.9
    assert ssgc["pct"] == -2.73

    # Delisted ENGRO is absent from market-watch — the natural delisted filter.
    assert "ENGRO" not in data


def test_company_headline_fundamentals():
    co = parse_company(_read("psx_company_OGDC.html"))

    assert co["pe_ttm"] == 8.70
    assert co["eps"] == 39.50
    assert co["wk52_low"] == 216.75
    assert co["wk52_high"] == 340.75
    assert co["as_of"] == "Wed, Jun 24, 2026 3:49 PM"

def test_parse_eod_monthly_uses_close_index3():
    # EOD rows are [ts, open, vol, CLOSE]; monthly series must end on the close.
    series = parse_eod_monthly(_read("psx_kse100_eod.json"))
    assert series["labels"][-1] == "2026-06"
    # June 2026 last close (not the 179571.26 open)
    assert abs(series["values"][-1] - 178115.36) < 0.5
    assert len(series["labels"]) == len(series["values"]) >= 2
