"""Macro parser — provisional GDP growth must be pulled from the real captured
PBS national-accounts page (tests/fixtures/pbs_national_accounts.html), plus the
curated IMF status constant sanity-check."""
from pathlib import Path

from fetchers.macro import parse_gdp, IMF_STATUS

FIX = Path(__file__).parent / "fixtures" / "pbs_national_accounts.html"


def test_parses_provisional_gdp_growth_and_fiscal_year():
    html = FIX.read_text(encoding="utf-8")
    fy, growth = parse_gdp(html)
    assert fy == "2025-26"
    assert growth == 3.70


def test_imf_status_mentions_rsf():
    # Resilience & Sustainability Facility must be present in the programme text.
    assert "RSF" in IMF_STATUS["last_review"]
    assert "Resilience & Sustainability Facility" in IMF_STATUS["programme"]


def test_raises_if_gdp_sentence_absent():
    import pytest
    with pytest.raises(ValueError):
        parse_gdp("<html><body>no national accounts here</body></html>")
