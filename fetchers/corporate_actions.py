"""Comparable share bases from a sourced, bounded corporate-action ledger.

Raw observations are never overwritten. No split is inferred from a price jump.
Unreviewed issuers/windows have no published investment-performance series.
"""
import calendar
import datetime as dt
import json
from pathlib import Path

LEDGER_PATH = Path(__file__).resolve().parent.parent / 'data/corporate_actions.json'


def load_ledger():
    return json.loads(LEDGER_PATH.read_text())


def month_end(label):
    year, month = map(int, label.split('-'))
    return dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def performance_series(symbol, history, ledger=None):
    ledger = ledger or load_ledger()
    issuer = ledger['issuers'].get(symbol)
    if not issuer:
        return None
    labels, values = history.get('labels', []), history.get('values', [])
    dates = history.get('dates') or []
    if len(labels) != len(values) or len(dates) != len(values):
        return None
    points = [(lab, date, value) for lab, date, value in zip(labels, dates, values)
              if issuer['from'] <= date <= ledger['reviewed_through'] and value is not None and value > 0]
    if len(points) < 2:
        return None
    end = points[-1][1]
    adjusted = []
    for label, date, value in points:
        factor = 1
        for event in issuer['events']:
            if date < event['date'] <= end:
                factor *= event['factor']
        adjusted.append(round(value / factor, 8))
    return {'labels': [p[0] for p in points], 'dates': [p[1] for p in points],
            'values': adjusted, 'basis': 'documented-share-actions-adjusted-price',
            'reviewed_through': ledger['reviewed_through'], 'sources': issuer['sources'],
            'events': [e for e in issuer['events'] if points[0][1] < e['date'] <= end]}


def attach_performance(histories, ledger=None):
    ledger = ledger or load_ledger()
    for symbol, history in histories.items():
        history['performance'] = performance_series(symbol, history, ledger)
    return histories


def dividend_basis(symbol, announcement_date, cutoff, ledger=None):
    """Face value at declaration and later share-count factor, or no verified basis."""
    ledger = ledger or load_ledger()
    issuer = ledger['issuers'].get(symbol)
    if (not issuer or not announcement_date or announcement_date < issuer['from']
            or cutoff > ledger['reviewed_on']):
        return None
    face, factor = issuer['initial_face'], 1
    for event in sorted(issuer['events'], key=lambda e: e['date']):
        if event['date'] <= announcement_date:
            face = event['face_after']
        elif event['date'] <= cutoff:
            factor *= event['factor']
    return face, factor
