"""Unit tests for the PSX dividends fetcher parser.

Pure-string parser run against a real captured PSX payouts fixture — no network.
"""
from pathlib import Path

from fetchers.dividends import parse_payouts

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name):
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


def test_ogdc_latest_cash_dividend():
    out = parse_payouts(_read("psx_payouts_OGDC.html"), "OGDC", as_of='2026-04-29')

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
    out = parse_payouts(html, "LUCK", as_of='2026-03-10')
    assert out["face_value"] == 2
    assert out["latest_pct"] == 200.0
    assert out["latest_cash"] == 4.0


def payout(date, percent, action='D'):
    return f'<tr><td>{date}</td><td>period</td><td>{percent}% ({action})</td><td>book</td></tr>'


def test_snapshot_window_expires_and_excludes_future_announcements():
    html = payout('September 7, 2025', 100) + payout('September 8, 2026', 100)
    out = parse_payouts(html, 'SYS', as_of='2026-09-07')
    assert out['ttm_cash'] == 0
    assert out['cash_rows'] == []
    assert not out['basis_verified']


def test_bafl_old_and_new_share_dividends_are_comparable():
    html = payout('February 16, 2026', 30) + payout('July 30, 2026', 30)
    out = parse_payouts(html, 'BAFL', as_of='2026-09-07')
    assert out['basis_verified']
    assert out['ttm_cash'] == 3.0  # old: 30% × 10 / 2; new: 30% × 5


def test_pre_split_sys_cash_is_adjusted_to_new_share_count():
    out = parse_payouts(payout('April 1, 2025', 60), 'SYS', as_of='2025-09-07')
    assert out['ttm_cash'] == 1.2  # 60% × 10 / 5
    assert out['basis_verified']


def test_unknown_and_unreviewed_future_share_bases_are_withheld():
    assert not parse_payouts(payout('April 1, 2026', 60), 'UNKNOWN', as_of='2026-09-07')['basis_verified']
    assert not parse_payouts(payout('April 1, 2026', 60), 'SYS', as_of='2026-09-08')['basis_verified']


def test_mixed_action_row_is_not_claimed_verified():
    html = payout('April 1, 2026', 60).replace('60% (D)', '60% (B) 20% (D)')
    assert not parse_payouts(html, 'SYS', as_of='2026-09-07')['basis_verified']
