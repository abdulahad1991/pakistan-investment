"""forex parser must pull the interbank USD/PKR spot (first in-band decimal,
NOT a later bid/offer/forward column) and its date from a real captured SBP
Mark-to-Market page (tests/fixtures/sbp_m2m.html)."""
from pathlib import Path

import pytest

from fetchers.forex import parse_forex

FIX = Path(__file__).parent / "fixtures" / "sbp_m2m.html"


def test_parses_interbank_spot_and_date():
    html = FIX.read_text(encoding="utf-8", errors="replace")
    out = parse_forex(html)
    # The M2M revaluation spot — the FIRST 2xx.xxxx figure, not the 277.9214
    # bid or 278.3465 offer that follow it.
    assert out["interbank"] == 278.2022
    # The data's own date as printed on the page.
    assert out["as_of"] == "Jun 23, 2026"


def test_value_is_in_sanity_band():
    html = FIX.read_text(encoding="utf-8", errors="replace")
    out = parse_forex(html)
    assert 200 <= out["interbank"] <= 400


def test_raises_when_no_in_band_figure():
    with pytest.raises(ValueError):
        parse_forex("<html><body>no rates here, just 12.34</body></html>")
