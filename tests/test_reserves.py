"""SBP FX reserves parser — against a real captured ferm.asp response
(tests/fixtures/sbp_reserves.html).

The page reports US$ MILLIONS; the parser must convert to BILLIONS and read the
week-ended date off the Foreign Exchange Reserves row.
"""
from pathlib import Path

import pytest

from fetchers.reserves import parse_reserves

FIX = Path(__file__).parent / "fixtures" / "sbp_reserves.html"


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
