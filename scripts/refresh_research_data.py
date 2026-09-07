#!/usr/bin/env python3
"""Refresh public sources used in the reviewed research. Never posts to social apps."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fetchers import funds, stocks, dividends
from fetchers.base import run, http_get
from fetchers.corporate_actions import load_ledger, attach_performance
import build_data


def main():
    symbols = list(load_ledger()['issuers'])
    run(funds.NAME, funds.fetch)
    run(stocks.NAME, lambda: stocks.fetch(enrich=symbols))
    run(dividends.NAME, lambda: dividends.fetch(symbols=symbols))
    path = ROOT / 'data/stock_history.json'
    history = json.loads(path.read_text())
    for symbol in symbols:
        try:
            history[symbol] = stocks.parse_eod_monthly(http_get(stocks.EOD_URL.format(sym=symbol)))
            print('History refreshed:', symbol, flush=True)
        except Exception as error:
            print('History retained with its existing dates:', symbol, type(error).__name__, flush=True)
    path.write_text(json.dumps(attach_performance(history), ensure_ascii=False))
    build_data.merge()


if __name__ == '__main__':
    main()
