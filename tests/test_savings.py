"""CDNS savings parser must read the headline NSS profit rates out of the
single-line 'Latest profit rates:' ticker banner (there is NO <table>) from a
real captured savings.gov.pk response (tests/fixtures/cdns_rates.html):

  - the source's misspelled 'Bahbood' maps to 'Behbood Savings Certificate'
  - SSC is tiered: 'Special Savings Certificate' (first-5) vs '... 6th'
  - 'Savings Account' must NOT be confused with 'Special/Islamic Savings Account'
  - the banner's leading date is the data's own effective date.
"""
from pathlib import Path
import datetime
import hashlib
import json

import pytest

from fetchers.savings import parse_savings, reviewed_savings, REVIEWED_PATH

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


def reviewed_fixture():
    reviewed = json.loads(REVIEWED_PATH.read_text())
    documents = {}
    for n, document in enumerate(reviewed['documents']):
        content = f'reviewed fixture document {n}'.encode()
        document['sha256'] = hashlib.sha256(content).hexdigest()
        documents[document['url']] = content
    html = (FIX.parent / 'cdns_notice_2026_09.html').read_text()
    return html, reviewed, documents


def test_reviewed_notice_keeps_ssc_coupon_tiers_separate_from_average():
    html, reviewed, documents = reviewed_fixture()
    out = reviewed_savings(html, reviewed, documents, datetime.date(2026, 9, 28))
    assert out['effective'] == '04-09-2026'
    assert out['schemes']['Special Savings Certificate'] == 10.9
    assert out['schemes']['Special Savings Certificate 6th'] == 12
    assert out['schemes']['Savings Account'] == 10


@pytest.mark.parametrize('change', ['date', 'document', 'link', 'account'])
def test_source_changes_require_a_new_review(change):
    html, reviewed, documents = reviewed_fixture()
    if change == 'date':
        html = html.replace('04-09-2026', '05-10-2026')
    elif change == 'document':
        documents[reviewed['documents'][0]['url']] = b'updated rates'
    elif change == 'link':
        html = html.replace(reviewed['documents'][0]['url'], '/new-notice.jpeg')
    else:
        html = html.replace('10.00%', '9.50%')
    with pytest.raises(ValueError):
        reviewed_savings(html, reviewed, documents, datetime.date(2026, 10, 6))


def test_future_schedule_is_not_presented_as_effective():
    html, reviewed, documents = reviewed_fixture()
    with pytest.raises(ValueError):
        reviewed_savings(html, reviewed, documents, datetime.date(2026, 9, 3))
