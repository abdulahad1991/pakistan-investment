"""crawl_first — the failover primitive shared by forex/policy/reserves.

Tries an ordered list of (label, thunk) sources and returns the FIRST that
yields a valid partition, tagging it with provenance (`via`, and on a fallback,
`failover` + `primary_errors`). Raises AllSourcesFailed only when every source
fails — that's the signal for run() to carry the prior value forward ok=False.
"""
import pytest

from fetchers.base import crawl_first, AllSourcesFailed, partition


def _ok(name, value, source):
    return lambda: partition(name, value, None, source)


def _boom(msg):
    def _t():
        raise ValueError(msg)
    return _t


def test_primary_wins_and_is_tagged():
    out = crawl_first("forex", [
        ("sbp-m2m", _ok("forex", {"interbank": 278.1}, "SBP")),
        ("er-api", _ok("forex", {"interbank": 279.0}, "er-api")),
    ])
    assert out["value"] == {"interbank": 278.1}
    assert out["via"] == "sbp-m2m"
    # Primary success is NOT a failover.
    assert not out.get("failover")
    assert "primary_errors" not in out


def test_falls_over_to_second_source_when_primary_raises():
    out = crawl_first("forex", [
        ("sbp-m2m", _boom("page moved")),
        ("sbp-home", _ok("forex", {"interbank": 278.1}, "SBP home")),
        ("er-api", _ok("forex", {"interbank": 279.0}, "er-api")),
    ])
    # Second source (first survivor) wins — NOT the third.
    assert out["value"] == {"interbank": 278.1}
    assert out["via"] == "sbp-home"
    assert out["failover"] is True
    # The dead primary's error is preserved for the health block.
    assert any("page moved" in e for e in out["primary_errors"])


def test_skips_malformed_partition_and_continues():
    out = crawl_first("x", [
        ("bad", lambda: {"no_value_key": 1}),
        ("good", _ok("x", 42, "src")),
    ])
    assert out["value"] == 42
    assert out["via"] == "good"
    assert out["failover"] is True


def test_raises_when_all_sources_fail():
    with pytest.raises(AllSourcesFailed) as ei:
        crawl_first("forex", [
            ("sbp-m2m", _boom("down")),
            ("er-api", _boom("timeout")),
        ])
    # The aggregate error names every attempt so run()'s last_error is useful.
    msg = str(ei.value)
    assert "sbp-m2m" in msg and "er-api" in msg
    assert ei.value.name == "forex"
    assert len(ei.value.errors) == 2
