"""Expose collection failures in the Actions summary without blocking good data."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data = json.loads((ROOT / 'data.json').read_text())
    rows = ['## Source collection health', '',
            '| Source | Status | Observation date |', '| --- | --- | --- |']
    for name, health in sorted(data.get('data_health', {}).items()):
        status = ('Collection failed' if not health.get('ok') else
                  'Observation delayed' if health.get('stale') else 'Available')
        when = str(health.get('as_of') or 'Not published').replace('|', '/')
        rows.append(f'| {name} | {status} | {when} |')
        if status != 'Available':
            print(f'::warning title=Source needs attention::{name}: {status}; stored observation {when}')
    output = '\n'.join(rows) + '\n'
    print(output)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(output)


if __name__ == '__main__':
    main()
