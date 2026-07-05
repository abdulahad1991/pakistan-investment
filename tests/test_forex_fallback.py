"""forex failover: the non-SBP fallback parser (open.er-api.com) and the SBP
homepage recrawl must both yield the same USD/PKR the primary M2M page does."""
from pathlib import Path

import pytest

from fetchers.forex import parse_forex, parse_erapi

FIX = Path(__file__).parent / "fixtures"


def test_erapi_json_parses_usd_pkr_and_date():
    out = parse_erapi((FIX / "erapi_usd.json").read_text(encoding="utf-8"))
    # rates.PKR from the real captured response.
    assert out["interbank"] == 278.0378
    # 'Sun, 05 Jul 2026 00:02:31 +0000' -> the 'Mon DD, YYYY' shape _to_date reads.
    assert out["as_of"] == "Jul 05, 2026"


def test_erapi_rejects_wrong_base_or_missing_pkr():
    with pytest.raises(ValueError):
        parse_erapi('{"result":"success","base_code":"EUR","rates":{"PKR":278.0}}')
    with pytest.raises(ValueError):
        parse_erapi('{"result":"success","base_code":"USD","rates":{"GBP":0.8}}')
    with pytest.raises(ValueError):
        parse_erapi('{"result":"error","error-type":"unsupported-code"}')


def test_erapi_rejects_non_object_json():
    # Valid JSON that isn't an object (null / array / string / number) must
    # raise ValueError per the docstring contract — NOT AttributeError from
    # calling .get() on a non-dict (e.g. a rate-limit body or proxy wrapper).
    for bad in ("null", "[1,2,3]", '"just a string"', "278.04"):
        with pytest.raises(ValueError):
            parse_erapi(bad)


def test_sbp_homepage_recrawl_parses_same_as_m2m():
    # The identical Economic Data snapshot is server-rendered on the SBP
    # homepage, so the recrawl tier uses the very same parser.
    html = (FIX / "sbp_home_snapshot_2026-07.html").read_text(
        encoding="utf-8", errors="replace")
    out = parse_forex(html)
    assert out["interbank"] == 278.121
    assert out["as_of"] == "Jul 03, 2026"
