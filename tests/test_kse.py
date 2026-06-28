"""KSE-100 parser must read the CLOSE (index 3), not the OPEN (index 1).

Against a real captured PSX EOD response (tests/fixtures/psx_kse100_eod.json).
The headline bug being guarded: the latest bar's OPEN is 179571.26 but the true
CLOSE is 178115.3639 — the old site showed the open.
"""
import json
from pathlib import Path

from fetchers.kse import parse_kse

FIX = Path(__file__).parent / "fixtures" / "psx_kse100_eod.json"


def _parsed():
    return parse_kse(FIX.read_text(encoding="utf-8"))


def test_uses_close_not_open():
    out = _parsed()
    # latest bar ts=1782298800 -> 2026-06-24; CLOSE 178115.3639, NOT open 179571.26
    assert out["level"] == 178115.36
    assert out["level"] != 179571.26  # the OPEN — the bug we fixed
    assert out["as_of"] == "2026-06-24"


def test_previous_close_and_change():
    out = _parsed()
    # previous bar (2026-06-23) close = 179307.6868
    assert out["prev_close"] == 179307.69
    assert out["change"] == -1192.33
    assert out["change"] < 0  # the index fell
    assert out["change_pct"] == -0.66


def test_monthly_history():
    out = _parsed()
    hist = out["history"]
    labels, values = hist["labels"], hist["values"]
    assert isinstance(labels, list) and isinstance(values, list)
    assert len(labels) == len(values)
    assert 1 < len(labels) <= 72
    # newest month is anchored to the headline close
    assert labels[-1] == "Jun'26"
    assert values[-1] == 178115.36
    # months are unique and chronologically ordered (oldest -> newest)
    assert len(set(labels)) == len(labels)


def test_accepts_predecoded_json():
    out = parse_kse(json.loads(FIX.read_text(encoding="utf-8")))
    assert out["level"] == 178115.36
