"""SBP policy-rate parser must read the corridor box (rate/floor/ceiling) from a
real captured SBP response (tests/fixtures/sbp_ecodata.html) — and NOT confuse
the policy rate with the page's weighted-average overnight repo rate (11.67%)."""
from pathlib import Path

from fetchers.policy import parse_policy

FIX = Path(__file__).parent / "fixtures" / "sbp_ecodata.html"


def test_parses_policy_rate_corridor():
    html = FIX.read_text(encoding="utf-8")
    result = parse_policy(html)
    assert result == {"rate": 11.5, "floor": 10.5, "ceiling": 12.5}


def test_rate_is_between_floor_and_ceiling():
    html = FIX.read_text(encoding="utf-8")
    r = parse_policy(html)
    assert r["floor"] < r["rate"] < r["ceiling"]


def test_raises_if_box_absent():
    import pytest
    with pytest.raises(ValueError):
        parse_policy("<html><body>no rate box here</body></html>")
