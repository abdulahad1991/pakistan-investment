"""Unit tests for the PSX dividends fetcher parser.

Pure-string parser run against a real captured PSX payouts fixture — no network.
"""
from pathlib import Path

from fetchers.dividends import parse_payouts

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name):
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


def test_ogdc_latest_cash_dividend():
    out = parse_payouts(_read("psx_payouts_OGDC.html"), "OGDC")

    # Most recent (D) cash row: 32.50%(iii) (D) at Rs 10 par => Rs 3.25/share.
    assert out["latest_pct"] == 32.5
    assert out["latest_cash"] == 3.25
    assert out["period"] == "31/03/2026(IIIQ)"
    assert out["announce"] == "April 29, 2026 3:56 PM"
    assert out["book_closure"] == "12/05/2026 - 13/05/2026"
    assert out["face_value"] == 10
    assert out["symbol"] == "OGDC"

    # TTM cash = (D) rows announced in the trailing 12 months (anchor Apr 29,
    # 2026; cutoff Apr 29, 2025). Includes 32.50 + 42.50 + 35 + 50 + 30 % of
    # Rs 10 par = 3.25 + 4.25 + 3.50 + 5.00 + 3.00 = 19.00. The Feb 28, 2025
    # 40.50% row falls just outside the window and is excluded.
    assert out["ttm_cash"] == 19.0


def test_luck_par_override():
    # Lucky Cement is Rs 2 par (subdivided), so 200% => Rs 4.00, NOT Rs 20.
    html = (
        "<table><tbody>"
        "<tr>"
        "<td>March 10, 2026 1:00 PM</td>"
        "<td>30/06/2025(YR)</td>"
        "<td> 200%(F) (D) </td>"
        "<td>01/04/2026  - 02/04/2026 </td>"
        "</tr>"
        "</tbody></table>"
    )
    out = parse_payouts(html, "LUCK")
    assert out["face_value"] == 2
    assert out["latest_pct"] == 200.0
    assert out["latest_cash"] == 4.0
