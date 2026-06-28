"""CDNS savings parser must read the headline NSS profit rates out of the
single-line 'Latest profit rates:' ticker banner (there is NO <table>) from a
real captured savings.gov.pk response (tests/fixtures/cdns_rates.html):

  - the source's misspelled 'Bahbood' maps to 'Behbood Savings Certificate'
  - SSC is tiered: 'Special Savings Certificate' (first-5) vs '... 6th'
  - 'Savings Account' must NOT be confused with 'Special/Islamic Savings Account'
  - the banner's leading date is the data's own effective date.
"""
from pathlib import Path

import pytest

from fetchers.savings import parse_savings

FIX = Path(__file__).parent / "fixtures" / "cdns_rates.html"


def test_parses_savings_banner():
    html = FIX.read_text(encoding="utf-8")
    result = parse_savings(html)
    assert result["effective"] == "10-06-2026"
    assert result["schemes"] == {
        "Special Savings Certificate": 12.4,
        "Special Savings Certificate 6th": 13.6,
        "Regular Income Certificate": 11.82,
        "Behbood Savings Certificate": 13.2,
        "Defence Savings Certificate": 10.44,
        "Savings Account": 10.0,
    }


def test_all_rates_in_sanity_band():
    from fetchers.base import in_band
    html = FIX.read_text(encoding="utf-8")
    rates = parse_savings(html)["schemes"]
    assert rates and all(in_band(v, 3, 25) for v in rates.values())


def test_raises_if_banner_absent():
    with pytest.raises(ValueError):
        parse_savings("<html><body>no profit rates banner here</body></html>")
