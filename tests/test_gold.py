"""gold.py parser must extract the 24 Karat per-tola rate from a real captured
gold.pk response (tests/fixtures/goldpk.html) and ignore the 10g / per-gram /
per-ounce / city / silver figures that share the page."""
from pathlib import Path

import pytest

from fetchers.base import in_band
from fetchers.gold import parse_gold

FIX = Path(__file__).parent / "fixtures" / "goldpk.html"


def test_parses_24k_per_tola_rate():
    html = FIX.read_text(encoding="utf-8")
    out = parse_gold(html)
    # 24 Karat gold, 1 tola, exactly as fixed by Karachi Sarafa on the page.
    assert out == {"tola_24k": 434500}
    assert isinstance(out["tola_24k"], int)


def test_value_is_within_sanity_band():
    html = FIX.read_text(encoding="utf-8")
    out = parse_gold(html)
    assert in_band(out["tola_24k"], 100_000, 2_000_000)


def test_did_not_pick_10g_or_per_gram_or_ounce():
    html = FIX.read_text(encoding="utf-8")
    tola = parse_gold(html)["tola_24k"]
    # guard against grabbing the wrong figure off the same page
    assert tola != 372520  # 10-gram 24K
    assert tola != 37252   # per-gram 24K
    assert tola != 1158670  # per-ounce 24K


def test_raises_when_rate_absent():
    with pytest.raises(ValueError):
        parse_gold("<html><body>no gold rate here</body></html>")
