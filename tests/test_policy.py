"""SBP policy-rate parser must read the corridor box (rate/floor/ceiling) from a
real captured SBP response (tests/fixtures/sbp_ecodata.html) — and NOT confuse
the policy rate with the page's weighted-average overnight repo rate (11.67%)."""
from pathlib import Path

from fetchers.policy import parse_policy

FIX = Path(__file__).parent / "fixtures" / "sbp_ecodata.html"
# SBP redesign (2026-07): the legacy ecodata box is gone; the corridor now
# lives in the "Economic Data snapshot" served on m2m-current.asp, with the
# ceiling/floor labels re-worded ("... (Repo) Ceiling Rate 12.50% p.a.").
FIX_2026_07 = Path(__file__).parent / "fixtures" / "sbp_m2m_2026-07.html"


def test_parses_policy_rate_corridor():
    html = FIX.read_text(encoding="utf-8")
    result = parse_policy(html)
    assert result == {"rate": 11.5, "floor": 10.5, "ceiling": 12.5}


def test_parses_redesigned_2026_07_snapshot():
    html = FIX_2026_07.read_text(encoding="utf-8", errors="replace")
    result = parse_policy(html)
    # Must NOT confuse the corridor with the snapshot's weighted-average
    # overnight repo rate (11.25%) or the KIBOR tenors right after it.
    assert result == {"rate": 11.5, "floor": 10.5, "ceiling": 12.5}


def test_homepage_recrawl_yields_same_corridor():
    # Failover tier: the same snapshot is server-rendered on the SBP homepage,
    # so the recrawl parses identically to the primary M2M page.
    home = Path(__file__).parent / "fixtures" / "sbp_home_snapshot_2026-07.html"
    result = parse_policy(home.read_text(encoding="utf-8", errors="replace"))
    assert result == {"rate": 11.5, "floor": 10.5, "ceiling": 12.5}


def test_rate_is_between_floor_and_ceiling():
    html = FIX.read_text(encoding="utf-8")
    r = parse_policy(html)
    assert r["floor"] < r["rate"] < r["ceiling"]


def test_raises_if_box_absent():
    import pytest
    with pytest.raises(ValueError):
        parse_policy("<html><body>no rate box here</body></html>")
