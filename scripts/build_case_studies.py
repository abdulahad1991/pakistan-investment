#!/usr/bin/env python3
"""Reproduce dated editorial calculations and their public CSV downloads.

Inputs are deliberately fixed and cited. Re-running the data pipeline cannot
turn a hypothetical scenario into an observed result or advance a review date.
"""
import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / 'data/research/case-inputs.json'


def calculations(d):
    s, b, c, f = (d[k] for k in ('sys', 'bafl', 'ssc', 'fund'))
    before_units = s['amount'] / s['before_price']
    raw = before_units * s['after_price']
    adjusted = raw * s['share_factor']
    coupons = [c['principal'] * rate / 100 / 2 for rate in c['annual_rates_percent']]
    units = f['contribution'] * (1 - f['assumed_load_percent_of_contribution'] / 100) / f['initial_nav']
    return {
        'sys': {'before_units': before_units, 'after_units': before_units * s['share_factor'],
                'raw_final': raw, 'adjusted_final': adjusted,
                'raw_return': (raw / s['amount'] - 1) * 100,
                'adjusted_return': (adjusted / s['amount'] - 1) * 100},
        'bafl': {'eps_adjusted': b['fy2025_eps_old_share'] / b['split_factor'],
                 'dividend_adjusted': b['fy2025_dividend_old_share'] / b['split_factor'],
                 'fy_payout': b['fy2025_dividend_old_share'] / b['fy2025_eps_old_share'] * 100,
                 'hy_growth': (b['hy2026_eps'] / b['hy2025_eps_restated'] - 1) * 100,
                 'hy_payout': b['hy2026_dividend'] / b['hy2026_eps'] * 100},
        'ssc': {'coupons': coupons, 'total_profit': sum(coupons)},
        'fund': {'units': units, 'break_even_nav': f['contribution'] / units,
                 'values': [units * nav for nav in f['ending_nav_scenarios']]},
    }


def write_csv(name, header, rows):
    target = ROOT / 'data/research' / name
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(header)
    writer.writerows([[format(value, '.10g') if isinstance(value, float) else value
                      for value in row] for row in rows])
    target.write_text(stream.getvalue(), encoding='utf-8')


def table(headers, rows):
    return ('<div class="research-table"><table><thead><tr>' +
            ''.join(f'<th scope="col">{h}</th>' for h in headers) +
            '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows) +
            '</tbody></table></div>')


def publish(file, anchor, title, body, download):
    page = ROOT / file
    html = page.read_text()
    section = (f'<section class="research-case" id="{anchor}">'
               '<p class="research-meta">Original calculation · Reviewed 7 September 2026 · Abdul Ahad, publisher</p>'
               f'<h2>{title}</h2>{body}'
               f'<p><a href="/data/research/{download}" download>Download the calculation (CSV)</a> · '
               '<a href="/data/research/case-inputs.json">Dated inputs and sources (JSON)</a></p></section>')
    start, end = f'<!-- CASE_{anchor}_START -->', f'<!-- CASE_{anchor}_END -->'
    replacement = start + section + end
    if start in html:
        html = re.sub(re.escape(start) + '.*?' + re.escape(end), lambda _: replacement, html, flags=re.S)
    else:
        target = '<h2>Worked mechanics</h2>' if file == 'backtester.html' else '<h2 id="s1">'
        if target not in html:
            raise ValueError(f'case insertion target missing in {file}')
        html = html.replace(target, replacement + '\n\n      ' + target, 1)
    if '/assets/research.css' not in html:
        html = html.replace('</head>', '<link rel="stylesheet" href="/assets/research.css">\n</head>')
    page.write_text(html)


def build():
    d = json.loads(INPUT.read_text()); out = calculations(d)
    s, r = d['sys'], out['sys']
    write_csv('sys-share-split.csv', ['measure', 'value', 'basis_or_source'], [
        ['start_date', s['before_date'], s['prices_source']], ['start_price_pkr', s['before_price'], s['prices_source']],
        ['end_date', s['after_date'], s['prices_source']], ['end_price_pkr', s['after_price'], s['prices_source']],
        ['share_factor', s['share_factor'], s['action_source']], ['starting_amount_pkr', s['amount'], 'assumed amount; fractional units allowed'],
        *[[k, v, 'site calculation; excludes cash dividends, costs and tax'] for k, v in r.items()]])
    body = (f'<p>Systems Limited resumed trading on a five-for-one share basis on 2 June 2025. '
            f'The <a href="{s["action_source"]}">PSX notice</a> and <a href="{s["credit_source"]}">credit confirmation</a> '
            'establish the event; a large price drop alone would not establish a split.</p>'
            f'<p>Our downloaded <a href="{s["prices_source"]}">PSX end-of-day series</a> records PKR 539.94 '
            'on 27 May and PKR 107.00 on 30 June 2025, the final observations present for those months. '
            'The input dates are retained so the missing trading days are visible. Apply a hypothetical PKR 100,000 '
            'and allow fractional shares to isolate the adjustment.</p>')
    body += table(['Calculation', 'Share quantity at end', 'Ending value', 'Price return'], [
        ['Keeping the old share count (incorrect)', f'{r["before_units"]:.6f}', f'PKR {r["raw_final"]:,.2f}', f'{r["raw_return"]:.2f}%'],
        ['Applying the documented 5× share count', f'{r["after_units"]:.6f}', f'PKR {r["adjusted_final"]:,.2f}', f'{r["adjusted_return"]:.2f}%']])
    body += ('<p class="research-result">The apparent 80.18% loss becomes a 0.91% price decline after matching the share bases.</p>'
             '<p>The reproducible formula is 100,000 ÷ 539.94 × 5 × 107. Equivalently, divide the starting price by five '
             'and retain a constant number of adjusted units. Do not do both adjustments. This is price arithmetic over '
             'two recorded dates; it excludes cash dividends, dealing costs, taxes and whole-share rounding. The backtester '
             'now follows the second method over its documented windows.</p>')
    publish('backtester.html', 'split-case-study', 'Case study: a share split is not an 80% investment loss', body, 'sys-share-split.csv')

    b, r = d['bafl'], out['bafl']
    write_csv('bafl-per-share-reconciliation.csv', ['measure', 'value', 'period_or_source'], [
        *[[k, b[k], b['fy_source']] for k in ('fy2025_eps_old_share', 'fy2025_dividend_old_share')],
        ['split_factor', b['split_factor'], b['action_source']],
        *[[k, b[k], b['hy_source']] for k in ('hy2025_eps_restated', 'hy2026_eps', 'hy2026_dividend')],
        *[[k, v, 'site calculation from the cited rounded inputs'] for k, v in r.items()]])
    body = (f'<p>Bank Alfalah’s <a href="{b["fy_source"]}">FY2025 results release</a> reports EPS of PKR 17.97 '
            'and full-year cash dividends of PKR 10.50 per old share. Its '
            f'<a href="{b["action_source"]}">PSX split notice</a> sets 20 April 2026 as the resumption date '
            'for two new shares per old share, with face value changing from PKR 10 to PKR 5.</p>')
    body += table(['FY2025 input', 'Per old share', 'Equivalent per new share'], [
        ['Earnings', 'PKR 17.97', f'PKR {r["eps_adjusted"]:.3f}'],
        ['Full-year cash dividend', 'PKR 10.50', f'PKR {r["dividend_adjusted"]:.2f}'],
        ['Dividend ÷ EPS', f'{r["fy_payout"]:.2f}%', f'{r["fy_payout"]:.2f}%']])
    body += ('<p>A holder of 1,000 old shares becomes a holder of 2,000 new shares. The same historical gross dividend '
             'is PKR 10,500 on either representation: 1,000 × 10.50 or 2,000 × 5.25. The split changes units, '
             'while the payout ratio stays unchanged. Mixing the old EPS with a new-share price would understate '
             'the price/earnings multiple by half.</p>'
             f'<p>The <a href="{b["hy_source"]}">half-year 2026 release</a> provides a matched comparison: '
             f'EPS of 6.76 versus restated 4.84 for the prior half-year. Our calculation, (6.76 ÷ 4.84 − 1) × 100, '
             f'is {r["hy_growth"]:.2f}%. The half-year dividend of 3.00 divided by 6.76 gives a {r["hy_payout"]:.2f}% payout ratio. '
             'Small differences from reported growth can arise because these displayed EPS inputs are rounded.</p>'
             '<p class="research-result">Use a consistent share basis and the same reporting period before interpreting growth or a valuation multiple.</p>'
             '<p>This reconciliation is complete for the stated inputs. It does not estimate fair value. The issuer attributes '
             'much of the half-year profit increase to capital gains; annualizing that half-year EPS would embed a separate '
             'repeatability assumption. The teaching model below shows the additional balance-sheet, income and valuation '
             'checks needed before a forecast could be supported.</p>')
    publish('blog/how-to-value-bank-stocks-pakistan.html', 'bafl-case-study', 'Completed case: Bank Alfalah’s per-share reconciliation', body, 'bafl-per-share-reconciliation.csv')

    c, r = d['ssc'], out['ssc']; running = 0; rows = []; csv_rows = []
    for n, (rate, coupon) in enumerate(zip(c['annual_rates_percent'], r['coupons']), 1):
        running += coupon
        rows.append([n * 6, f'{rate:.2f}%', f'PKR {coupon:,.0f}', f'PKR {running:,.0f}'])
        csv_rows.append([n * 6, rate, coupon, running, c['principal'] if n == 6 else 0, c['source']])
    write_csv('ssc-cash-flows.csv', ['month', 'annual_rate_percent', 'gross_coupon_pkr', 'cumulative_profit_pkr', 'principal_returned_at_maturity_pkr', 'source'], csv_rows)
    body = (f'<p>This completed cash-flow calculation uses the <a href="{c["source"]}">CDNS Special Savings Certificates schedule</a> '
            'effective 18 July 2026: 11.20% annually for the first five six-month periods and 12.60% for the sixth. '
            'Assume a qualifying PKR 100,000 purchase under that schedule. Coupons are withdrawn, with no reinvestment; '
            'all amounts below are gross before tax or any applicable Zakat. These are calculated future cash flows, '
            'not a report of an investment we held.</p>')
    body += table(['Month completed', 'Annual rate', 'Six-month coupon', 'Cumulative profit'], rows)
    # Keep the encashment explanation separate from the coupon schedule.
    body += (f'<p class="research-result">Six coupons total PKR {r["total_profit"]:,.0f}; principal of PKR 100,000 '
             'is returned separately at maturity. Total gross cash received over three years is PKR 134,300.</p>'
             '<p>Each coupon equals 100,000 × annual rate ÷ 2. Multiplying 11.20% by three years would give '
             'PKR 33,600 and miss PKR 700 from the higher final coupon. The 34.3% cumulative cash profit '
             'is not a compounded annual return.</p>'
             '<p>At an exit before six months, gross profit is zero. After nine months, only one six-month '
             'period is complete, giving PKR 5,600; no extra three-month pro-rata profit is assumed. A previously '
             'withdrawn coupon is not paid again on encashment. CDNS states that SSC encashment has no service charge.</p>'
             '<p>For a matched six-month fund comparison, use the <a href="/guides/how-to-invest-mutual-funds-pakistan.html#fund-case-study">'
             'units-and-fees scenario</a>. Its outcome depends on an assumed future NAV; it is not interchangeable '
             'with this stated coupon schedule. Apply personal tax and access constraints before comparing net amounts.</p>')
    publish('guides/national-savings-vs-mutual-funds.html', 'ssc-case-study', 'Completed cash-flow case: PKR 100,000 in SSCs', body, 'ssc-cash-flows.csv')

    f, r = d['fund'], out['fund']
    write_csv('fund-units-and-fees.csv', ['ending_nav_assumption', 'units', 'ending_value_pkr', 'gain_on_gross_contribution_pkr', 'return_on_gross_contribution_percent'], [
        [nav, r['units'], value, value - f['contribution'], (value / f['contribution'] - 1) * 100]
        for nav, value in zip(f['ending_nav_scenarios'], r['values'])])
    body = ('<p>Use this completed scenario to audit an AMC illustration while fresh comparative returns are unavailable. '
            'Assume PKR 100,000 contributed, a load deducted as exactly 2% of that gross amount, initial NAV of 100, '
            'and redemption after six months. These are explicit arithmetic assumptions, not the terms or performance of a named fund.</p>'
            f'<p>The load is PKR 2,000. The remaining PKR 98,000 buys {r["units"]:,.0f} units. '
            'Assume no distributions, back-end charge or tax. Recurring fund expenses are already reflected in NAV '
            'and must not be deducted a second time.</p>')
    body += table(['Assumed final NAV', 'Units held', 'Redemption value', 'Gain / loss on PKR 100,000'], [
        [f'{nav:.2f}', f'{r["units"]:,.0f}', f'PKR {value:,.0f}', f'{(value / f["contribution"] - 1) * 100:+.2f}%']
        for nav, value in zip(f['ending_nav_scenarios'], r['values'])])
    body += (f'<p class="research-result">A 10% NAV increase produces a 7.80% gain on the contributed amount after this assumed load. '
             f'Break-even NAV is 100,000 ÷ 980 = {r["break_even_nav"]:.4f}.</p>'
             '<p>A flat NAV still leaves a PKR 2,000 loss because the investor paid the load. If the document instead '
             'defines the load as an addition to the offer price, the unit calculation changes; our deduction convention '
             'must not be copied into that product. Check the actual offer/redemption price, load waiver and valuation cut-off.</p>'
             '<p>The <a href="/guides/national-savings-vs-mutual-funds.html#ssc-case-study">SSC case</a> calculates '
             'PKR 5,600 gross profit for its first six-month period. The fund scenarios range from a PKR 11,800 loss '
             'to a PKR 7,800 gain. That range demonstrates sensitivity to NAV and fees, not which product will outperform. '
             'Tax, eligibility and access timing still need matched inputs.</p>')
    publish('guides/how-to-invest-mutual-funds-pakistan.html', 'fund-case-study', 'Completed scenario: units, loads and three NAV outcomes', body, 'fund-units-and-fees.csv')


if __name__ == '__main__':
    build()
    print('Built four dated case studies and calculation CSVs.')
