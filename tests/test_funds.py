"""MUFAP funds parser — pinned against a real captured Performance Summary page
(tests/fixtures/mufap_nav.html).

The load-bearing assertions: the 1-year figure comes from the '365 Days' column
located BY HEADER NAME, and each fund carries the correct return_type read from
its MUFAP category tag — INCOME funds '(Annualized Return)' vs EQUITY/STOCK funds
'(Absolute Return)'. The old site mislabelled equity absolute returns as
annualized; these tests lock that distinction.
"""
from pathlib import Path

import pytest

from fetchers.funds import parse_funds

FIX = Path(__file__).parent / "fixtures" / "mufap_nav.html"


def _load():
    out = parse_funds(FIX.read_text(encoding="utf-8"))
    by_name = {f["name"]: f for f in out["funds"]}
    return out, by_name


def test_page_level_as_of_is_report_date():
    out, _ = _load()
    # The only single page-level stamp is "Report Date: Jun 28, 2026".
    assert out["as_of"] == "2026-06-28"


def test_at_least_three_funds_parsed():
    out, _ = _load()
    assert len(out["funds"]) >= 3


def test_miif_anchor_nav_1y_and_annualized():
    _, by = _load()
    miif = by["Meezan Islamic Income Fund"]
    # exact pinned values from the fixture
    assert miif["nav"] == 51.8643
    assert miif["ret_1y"] == 8.46
    # sanity bands from the independently-verified anchor
    assert 50 <= miif["nav"] <= 53
    assert 7 <= miif["ret_1y"] <= 10
    # income fund => annualized
    assert miif["return_type"] == "annualized"


def test_equity_stock_fund_is_absolute_not_annualized():
    _, by = _load()
    stock = by["NBP Islamic Stock Fund"]
    assert stock["nav"] == 26.1405
    assert stock["ret_1y"] == 37.17
    # equity/stock fund => ABSOLUTE (the bug the old site got wrong)
    assert stock["return_type"] == "absolute"


def test_other_funds_pinned_with_correct_return_types():
    _, by = _load()
    almeezan = by["Al Meezan Mutual Fund"]
    assert almeezan["nav"] == 50.6802
    assert almeezan["ret_1y"] == 30.15
    assert almeezan["return_type"] == "absolute"  # equity

    savings = by["NBP Savings Fund"]
    assert savings["nav"] == 9.9313
    assert savings["ret_1y"] == 13.11
    assert savings["return_type"] == "annualized"  # income

    js = by["JS Islamic Fund"]
    assert js["nav"] == 257.37
    assert js["ret_1y"] == 22.28
    assert js["return_type"] == "absolute"  # equity


def test_both_return_types_present():
    out, _ = _load()
    types = {f["return_type"] for f in out["funds"]}
    assert "annualized" in types
    assert "absolute" in types


def test_raises_when_no_table():
    with pytest.raises(ValueError):
        parse_funds("<html><body>no thead, no funds here</body></html>")
