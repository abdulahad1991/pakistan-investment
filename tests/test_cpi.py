"""CPI parser must pick the headline series and compute YoY — against a real
captured PBS SDMX response (tests/fixtures/pbs_cpi.xml)."""
from pathlib import Path

from fetchers.cpi import parse_cpi

FIX = Path(__file__).parent / "fixtures" / "pbs_cpi.xml"


def test_parses_headline_general_cpi_not_a_subindex_or_weight():
    xml = FIX.read_text(encoding="utf-8")
    yoy, as_of, ix_now, ix_prev = parse_cpi(xml)
    # latest month in the captured fixture is May 2026
    assert as_of == "2026-05"
    # headline General CPI index PCPI_IX, NOT a weight (~4.9) or sub-index
    assert abs(ix_now - 294.3417) < 0.01
    # year-ago anchor and the computed headline YoY
    assert abs(ix_prev - 263.6017) < 0.01
    assert yoy == 11.7


def test_raises_if_headline_series_absent():
    import pytest
    with pytest.raises(ValueError):
        parse_cpi("<root>no series here</root>")
