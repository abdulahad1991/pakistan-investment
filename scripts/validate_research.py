#!/usr/bin/env python3
"""Offline publication guard for the reviewed calculations and public sources."""
import json
import math
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fetchers.corporate_actions import performance_series


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links, self.duplicates = set(), [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if 'id' in attr:
            if attr['id'] in self.ids:
                self.duplicates.append(attr['id'])
            self.ids.add(attr['id'])
        if tag == 'a' and attr.get('href'):
            self.links.append(attr['href'])
        if tag in ('script', 'img', 'link'):
            target = attr.get('src') if tag != 'link' else attr.get('href')
            if target:
                self.links.append(target)


def validate():
    errors = []
    data = json.loads((ROOT / 'data.json').read_text())
    histories = json.loads((ROOT / 'data/stock_history.json').read_text())
    for symbol, h in histories.items():
        if h.get('performance') != performance_series(symbol, h):
            errors.append(f'{symbol}: performance disagrees with reviewed action ledger')
    for fund in data.get('mutual_funds', []):
        if {'ret_3y', 'ret_5y', 'recommended'} & fund.keys():
            errors.append(f'{fund["name"]}: seeded fund returns or rankings remain')
        if not fund.get('available') and (fund.get('nav') is not None or fund.get('ret_1y') is not None):
            errors.append(f'{fund["name"]}: unavailable observation still has comparison values')
    if data.get('gold', {}).get('history') or data.get('gold', {}).get('chg1y_pct') is not None:
        errors.append('Unsupported gold performance fields remain')

    snapshot = json.loads((ROOT / 'data/research/dividend-snapshot.json').read_text())
    for s in snapshot['data']['stocks']:
        cash = snapshot['payouts']['value'][s['ticker']]['cash_rows']
        expected = sum(row['cash'] for row in cash)
        if not all(row['basis_verified'] for row in cash):
            errors.append(f'{s["ticker"]}: snapshot includes an unchecked share basis')
        if not math.isclose(s['div'], expected, abs_tol=.0001):
            errors.append(f'{s["ticker"]}: published dividend differs from source-row sum')
        if not math.isclose(s['yield'], round(expected / s['price'] * 100, 2), abs_tol=.001):
            errors.append(f'{s["ticker"]}: yield does not reconcile to displayed inputs')

    paths = sorted([*ROOT.glob('*.html'), *ROOT.glob('guides/*.html'), *ROOT.glob('blog/*.html')])
    pages = {p: Page(p.read_text()) for p in paths}
    for path, page in pages.items():
        if page.duplicates:
            errors.append(f'{path.relative_to(ROOT)}: duplicate IDs {page.duplicates}')
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme and parts.scheme not in ('http', 'https'):
                continue
            if parts.netloc and parts.netloc not in ('pakinvestlysis.com', 'www.pakinvestlysis.com'):
                continue
            target = (ROOT / unquote(parts.path).lstrip('/') if parts.path.startswith('/')
                      else path.parent / unquote(parts.path)) if parts.path else path
            target = target.resolve()
            if target.is_dir():
                target /= 'index.html'
            if not target.exists():
                errors.append(f'{path.relative_to(ROOT)}: missing local target {link}')
            elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
                errors.append(f'{path.relative_to(ROOT)}: missing anchor {link}')
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'Research integrity passed: {len(histories)} raw histories, reviewed yields, fund exclusions and {len(pages)} linked pages.')
    return 0


if __name__ == '__main__':
    raise SystemExit(validate())
