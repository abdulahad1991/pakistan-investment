"""Regression checks for misleading investment returns and stale observations."""
import copy
import datetime as dt
import json
from pathlib import Path

import pytest
import build_data
from fetchers.corporate_actions import attach_performance, performance_series
from fetchers.cpi import choose_latest
from fetchers.funds import parse_funds
from scripts.build_case_studies import calculations
from scripts.build_dividends import table_html, cards_html
from scripts.prerender import fund_snapshot

ROOT = Path(__file__).resolve().parent.parent


def test_documented_split_removes_false_price_crash_without_overwriting_raw():
    history = {'labels': ['2025-05', '2025-06'], 'dates': ['2025-05-27', '2025-06-30'], 'values': [539.94, 107]}
    original = copy.deepcopy(history)
    p = performance_series('SYS', history)
    assert p['values'] == [107.988, 107]
    assert p['values'][-1] / p['values'][0] - 1 == pytest.approx(-0.0091491647)
    assert history == original


def test_bonus_means_existing_share_plus_eight_new_shares():
    p = performance_series('MARI', {'labels': ['2024-08', '2024-09'], 'dates': ['2024-08-30', '2024-09-30'], 'values': [900, 100]})
    assert p['values'] == [100, 100]


def test_no_inference_from_price_jump_or_unknown_observation_date():
    raw = {'labels': ['2025-05', '2025-06'], 'values': [500, 100]}
    assert performance_series('SYS', raw) is None
    assert attach_performance({'UNKNOWN': raw})['UNKNOWN']['performance'] is None


def test_future_observations_cannot_extend_reviewed_window():
    h = {'labels': ['2025-05', '2025-06', '2026-10'], 'dates': ['2025-05-27', '2025-06-30', '2026-10-30'], 'values': [539.94, 107, 1]}
    assert performance_series('SYS', h)['labels'] == ['2025-05', '2025-06']


def test_same_month_action_uses_actual_observation_date():
    # The April observation is before the April 20 split, even though a
    # fabricated month-end date would put it after the event.
    h = {'labels': ['2026-04', '2026-05'], 'dates': ['2026-04-17', '2026-05-29'], 'values': [100, 50]}
    assert performance_series('BAFL', h)['values'] == [50, 50]


@pytest.mark.parametrize('partition', [None, {'ok': False}, {'ok': True}])
def test_merge_removes_stale_seeded_fund_performance(tmp_path, monkeypatch, partition):
    path = tmp_path / 'data.json'
    path.write_text(json.dumps({'mutual_funds': [{'name': 'Fund', 'ret_1y': 25, 'nav': 110, 'ret_3y': 99, 'ret_5y': 200, 'recommended': True}]}))
    parts = {}
    if partition is not None:
        parts['funds'] = {**partition, 'as_of': dt.date.today().isoformat(), 'value': {'Fund': {'ret_1y': 25, 'nav': 110, 'as_of': '2024-01-01'}}}
    monkeypatch.setattr(build_data, 'DATA_JSON', path)
    monkeypatch.setattr(build_data, '_load_partitions', lambda: parts)
    f = build_data.merge()['mutual_funds'][0]
    assert f['available'] is False
    assert f['ret_1y'] is None and f['nav'] is None
    assert not {'ret_3y', 'ret_5y', 'recommended'} & f.keys()


def test_report_date_does_not_replace_row_validity_date():
    html = (ROOT / 'tests/fixtures/mufap_nav.html').read_text()
    p = parse_funds(html.replace('Report Date:  Jun 28, 2026', 'Report Date: Sep 7, 2026'))
    assert p['as_of'] == '2026-09-07'
    assert all(f['as_of'] < p['as_of'] for f in p['funds'])


def test_prerender_rechecks_age_even_when_old_build_says_available():
    d = {'data_health': {'funds': {'ok': True, 'stale': False}}, 'mutual_funds': [
        {'name': 'Fund', 'available': True, 'as_of': '2026-07-24', 'ret_1y': 99, 'nav': 100}]}
    text = fund_snapshot(d, today=dt.date(2026, 9, 7))
    assert 'comparison unavailable' in text
    assert '99%' not in text


def test_fresh_fund_snapshot_can_resume():
    d = {'data_health': {'funds': {'ok': True, 'stale': False}}, 'mutual_funds': [
        {'name': 'Fund', 'available': True, 'as_of': '2026-09-04', 'ret_1y': 8, 'nav': 100, 'return_type': 'annualized'}]}
    assert '8%' in fund_snapshot(d, today=dt.date(2026, 9, 7))


def test_staleness_rejects_future_and_expires_undated_collections():
    today = dt.date(2026, 9, 7)
    assert build_data._staleness({'ok': True, 'as_of': '2026-09-08'}, today)[0]
    assert build_data._staleness({'ok': True, 'fetched_at': '2026-07-01T12:00:00Z'}, today)[0]
    assert build_data._staleness({'ok': True, 'cadence': 'monthly', 'as_of': '2026-07'}, today)[0]


def test_cpi_reviewed_release_prevents_month_regression_but_allows_new_data():
    reviewed = json.loads((ROOT / 'data/research/cpi-verified.json').read_text())
    assert choose_latest({'as_of': '2026-07', 'value': 9.2}, reviewed)['value'] == 11.1
    assert choose_latest({'as_of': '2026-09', 'value': 10.0}, reviewed)['value'] == 10.0


def test_completed_cases_reconcile_cash_and_share_units():
    out = calculations(json.loads((ROOT / 'data/research/case-inputs.json').read_text()))
    assert out['sys']['adjusted_final'] == pytest.approx(99085.0835278)
    assert out['bafl']['eps_adjusted'] == 8.985
    assert out['bafl']['dividend_adjusted'] == 5.25
    assert out['ssc']['coupons'] == [5600] * 5 + [6300]
    assert out['ssc']['total_profit'] == 34300
    assert out['fund']['units'] == 980
    assert out['fund']['values'] == [88200, 98000, 107800]


def test_dividend_table_preserves_paisa_and_chart_uses_its_actual_endpoint():
    row = {'name': 'Test', 'ticker': 'SYS', 'price': 999, 'div': 5.75, 'yield': .58}
    history = {'SYS': {'performance': {'values': [100, 110], 'labels': ['2025-01', '2025-02']}}}
    assert '5.75' in table_html([row], history)
    card = cards_html([row], history)
    assert '+10.0%' in card
    assert '2025-01 to 2025-02' in card
    assert '999' not in card
