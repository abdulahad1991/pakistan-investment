"""forex parser must pull the interbank USD/PKR spot (first in-band decimal,
NOT a later bid/offer/forward column) and its date from a real captured SBP
Mark-to-Market page (tests/fixtures/sbp_m2m.html)."""
from pathlib import Path

import pytest

from fetchers.forex import parse_forex

FIX = Path(__file__).parent / "fixtures" / "sbp_m2m.html"
# SBP redesigned the page (captured 2026-07-05): the M2M rate moved into a
# "USD/PKR Rates" card ("As on 03- Jul - 2026" / "M2M Revaluation Rate" /
# 278.121 — now 3 decimals), and the old first-in-band 4-decimal scan landed
# on the BID instead while the 'Mon DD, YYYY' date vanished entirely.
FIX_2026_07 = Path(__file__).parent / "fixtures" / "sbp_m2m_2026-07.html"


def test_parses_interbank_spot_and_date():
    html = FIX.read_text(encoding="utf-8", errors="replace")
    out = parse_forex(html)
    # The M2M revaluation spot — the FIRST 2xx.xxxx figure, not the 277.9214
    # bid or 278.3465 offer that follow it.
    assert out["interbank"] == 278.2022
    # The data's own date as printed on the page.
    assert out["as_of"] == "Jun 23, 2026"


def test_parses_redesigned_2026_07_page():
    html = FIX_2026_07.read_text(encoding="utf-8", errors="replace")
    out = parse_forex(html)
    # The labelled M2M Revaluation Rate — NOT the 277.8345 BID / 278.2596
    # Offer that follow it in the Weighted Average block.
    assert out["interbank"] == 278.121
    # 'As on 03- Jul - 2026' normalised to the 'Mon DD, YYYY' shape that
    # build_data._to_date already understands.
    assert out["as_of"] == "Jul 03, 2026"


def test_value_is_in_sanity_band():
    html = FIX.read_text(encoding="utf-8", errors="replace")
    out = parse_forex(html)
    assert 200 <= out["interbank"] <= 400


def test_raises_when_no_in_band_figure():
    with pytest.raises(ValueError):
        parse_forex("<html><body>no rates here, just 12.34</body></html>")
