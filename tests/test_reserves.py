"""SBP FX reserves parser — against a real captured ferm.asp response
(tests/fixtures/sbp_reserves.html).

The page reports US$ MILLIONS; the parser must convert to BILLIONS and read the
week-ended date off the Foreign Exchange Reserves row.
"""
from pathlib import Path

import pytest

from fetchers.reserves import parse_reserves

FIX = Path(__file__).parent / "fixtures" / "sbp_reserves.html"
# SBP redesign (2026-07): ferm.asp is now an empty shell; reserves live in the
# "Economic Data snapshot" on m2m-current.asp — "Liquid Foreign Exchange
# Reserves (USD million) As on 24- June - 2026", curly apostrophes in
# "SBP's / Bank's" as literal U+2019 characters (not &rsquo; entities).
FIX_2026_07 = Path(__file__).parent / "fixtures" / "sbp_m2m_2026-07.html"


def test_parses_redesigned_2026_07_snapshot():
    d = parse_reserves(FIX_2026_07.read_text(encoding="utf-8", errors="replace"))
    # 16,527.2 / 5,517.4 / 22,044.6 US$ millions -> billions (2dp)
    assert d["sbp_bn"] == 16.53
    assert d["banks_bn"] == 5.52
    assert d["total_bn"] == 22.04
    # the card's own 'As on' date, normalised to 'Month DD, YYYY'
    assert d["as_of"] == "June 24, 2026"


def test_homepage_recrawl_yields_same_reserves():
    # Failover tier: the same reserves card is server-rendered on the SBP
    # homepage, so the recrawl parses identically to the primary M2M page.
    home = Path(__file__).parent / "fixtures" / "sbp_home_snapshot_2026-07.html"
    d = parse_reserves(home.read_text(encoding="utf-8", errors="replace"))
    assert d["sbp_bn"] == 16.53
    assert d["total_bn"] == 22.04
    assert d["as_of"] == "June 24, 2026"


def test_parses_sbp_banks_total_and_week_ended_date():
    d = parse_reserves(FIX.read_text(encoding="utf-8"))
    # 17,221.0 / 5,520.7 / 22,741.7 US$ millions -> billions (2dp)
    assert d["sbp_bn"] == 17.22
    assert d["banks_bn"] == 5.52
    assert d["total_bn"] == 22.74
    # SBP-held + banks add up to the total (within rounding)
    assert abs((d["sbp_bn"] + d["banks_bn"]) - d["total_bn"]) < 0.02
    # week-ended date from the Foreign Exchange Reserves 'Date Updated' cell
    assert d["as_of"] == "June 18, 2026"


def test_raises_when_table_absent():
    with pytest.raises(ValueError):
        parse_reserves("<html><body>no reserves here</body></html>")
