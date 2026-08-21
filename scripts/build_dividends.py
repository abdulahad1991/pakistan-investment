#!/usr/bin/env python3
"""Render the dated PSX dividend-yield dataset from local source partitions.

One canonical page (no new URLs). Each run sorts the stored observations,
redraws the SVG charts, exposes source cutoffs, and bumps dateModified.
Pure string composition - no AI, no network.
"""
import json, re, html as _html, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://pakinvestlysis.com"
SLUG = "top-dividend-stocks-pakistan"
OG   = f"{SITE}/assets/og/blog-top-dividend-stocks-pakistan.png?v=3"
TOPN = 10


def fmt_pkr(n):
    n = float(n); neg = n < 0; whole = int(round(abs(n))); s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(?<=\d)(?=(\d\d)+$)", ",", head); s = f"{head},{tail}"
    return ("-" if neg else "") + s


def all_payers(data):
    rows = [s for s in data["stocks"]
            if s.get("price", 0) > 0 and s.get("yield", 0) > 0]
    rows.sort(key=lambda s: s["yield"], reverse=True)
    return rows


def top_rows(data, n=TOPN):
    return all_payers(data)[:n]


def _pts(values, w, h, pad=4):
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1
    n = len(values)
    step = (w - 2 * pad) / (n - 1) if n > 1 else 0
    pts = []
    for i, v in enumerate(values):
        x = pad + i * step
        y = h - pad - (v - lo) / rng * (h - 2 * pad)
        pts.append((round(x, 1), round(y, 1)))
    return pts


def sparkline(values, w=150, h=36, tip=None):
    if not values or len(values) < 2:
        return ""
    up = values[-1] >= values[0]
    col = "#0B755F" if up else "#C24132"
    pts = _pts(values, w, h)
    poly = " ".join(f"{x},{y}" for x, y in pts)
    title = f"<title>{_html.escape(tip)}</title>" if tip else ""
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="3-year price trend">{title}'
            f'<polyline fill="none" stroke="{col}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round" points="{poly}"/>'
            f'<circle cx="{pts[-1][0]}" cy="{pts[-1][1]}" r="2.6" fill="{col}"/></svg>')


def chart(values, labels=None, w=300, h=92, pad=6):
    if not values or len(values) < 2:
        return '<p class="tbl-note">History backfills on the next refresh.</p>'
    up = values[-1] >= values[0]
    col = "#0B755F" if up else "#C24132"
    fill = "rgba(11,117,95,.10)" if up else "rgba(194,65,50,.10)"
    pts = _pts(values, w, h, pad=pad)
    poly = " ".join(f"{x},{y}" for x, y in pts)
    area = f"{pad},{h-pad} " + poly + f" {w-pad},{h-pad}"
    dv = "|".join(f"{v:g}" for v in values)
    dl = "|".join(labels) if labels else ""
    return (f'<svg class="ix-chart" data-v="{dv}" data-l="{dl}" data-pad="{pad}" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
            f'role="img" aria-label="monthly close, hover for values">'
            f'<polygon fill="{fill}" points="{area}"/>'
            f'<polyline fill="none" stroke="{col}" stroke-width="2.2" '
            f'stroke-linejoin="round" stroke-linecap="round" points="{poly}"/>'
            f'<line class="hov-line" x1="0" y1="{pad}" x2="0" y2="{h-pad}" stroke="{col}" '
            f'stroke-width="1" stroke-dasharray="3 3" style="display:none"/>'
            f'<circle class="hov-dot" r="3.6" fill="{col}" stroke="#fff" stroke-width="1.4" style="display:none"/>'
            f'<circle cx="{pts[-1][0]}" cy="{pts[-1][1]}" r="3" fill="{col}"/></svg>')


def table_html(rows, hist):
    out = ['<table class="div-table"><thead><tr>'
           '<th>#</th><th>Company</th><th>Price</th><th>Div/share</th>'
           '<th>Yield</th><th>1Y</th><th>P/E</th><th>3-yr trend</th>'
           '</tr></thead><tbody>']
    for i, s in enumerate(rows, 1):
        chg = s.get("chg1y", 0); cls = "pos" if chg >= 0 else "neg"
        sign = "+" if chg >= 0 else ""
        vals = (hist.get(s["ticker"]) or {}).get("values", [])
        tip = (f'{s["ticker"]}: ₨{fmt_pkr(vals[0])} → ₨{fmt_pkr(vals[-1])} '
               f'(3-yr)') if vals else None
        out.append(
            f'<tr><td class="rk">{i}</td>'
            f'<td class="co"><b>{_html.escape(s["name"])}</b><span>{s["ticker"]}</span></td>'
            f'<td>&#8360; {fmt_pkr(s["price"])}</td>'
            f'<td>&#8360; {fmt_pkr(s.get("div", 0))}</td>'
            f'<td class="yld">{s.get("yield", 0):.2f}%</td>'
            f'<td class="{cls}">{sign}{chg:.1f}%</td>'
            f'<td>{s.get("pe", 0):.1f}</td>'
            f'<td>{sparkline(vals, tip=tip)}</td></tr>')
    out.append("</tbody></table>")
    return "".join(out)


def cards_html(rows, hist):
    out = []
    for s in rows:
        h = hist.get(s["ticker"]) or {}
        vals = h.get("values", []); labs = h.get("labels", [])
        start = vals[0] if vals else s["price"]
        chg = ((s["price"] - start) / start * 100) if start else 0
        cls = "pos" if chg >= 0 else "neg"; sign = "+" if chg >= 0 else ""
        out.append(
            f'<div class="hist-card"><div class="hc-top">'
            f'<div class="hc-name">{_html.escape(s["name"])}<span>{s["ticker"]}</span></div>'
            f'<div class="hc-yld">{s.get("yield",0):.1f}%<span>yield</span></div></div>'
            f'{chart(vals, labs)}'
            f'<div class="hc-foot"><span>&#8360; {fmt_pkr(start)}</span>'
            f'<span class="{cls}">{sign}{chg:.1f}% 3y</span>'
            f'<span>&#8360; {fmt_pkr(s["price"])}</span></div></div>')
    return "".join(out)


def glance_html(rows, total, data_date, payout_date):
    if not rows:
        return "<li>No positive trailing-yield observations are available in this snapshot.</li>"
    top = rows[0]
    avg = sum(s["yield"] for s in rows) / len(rows)
    over8 = sum(1 for s in rows if s["yield"] >= 8)
    return "".join([
        f"<li><strong>First sorted row:</strong> {_html.escape(top['name'])} "
        f"({top['ticker']}) at <strong>{top['yield']:.2f}%</strong> in the stored data.</li>",
        f"<li><strong>{total} observations</strong> have a positive trailing cash-dividend "
        f"value and price in the {data_date} snapshot.</li>",
        f"<li><strong>{over8} of the first 10 rows</strong> are at least 8%; their simple "
        f"average is <strong>{avg:.1f}%</strong>. Neither statistic is a portfolio return.</li>",
        f"<li>Prices are dated <strong>{data_date}</strong>; the stored payout feed includes "
        f"announcements through <strong>{payout_date or 'an unpublished cutoff'}</strong>.</li>",
        "<li>The sort uses one backward-looking field. It does not test payout coverage, "
        "liquidity, solvency, future distributions or total return.</li>",
    ])


def rail_glance(rows, data_date, total):
    if not rows:
        return f'<div class="gl-row"><div class="gl-n">{data_date}</div><div class="gl-l">Data snapshot</div></div>'
    top = rows[0]; over8 = sum(1 for s in rows if s["yield"] >= 8)
    cells = [(top["ticker"], "First row, not a pick"),
             (str(total), "Positive-yield rows"),
             (str(over8), "First 10 at 8%+"),
             (data_date, "Price snapshot")]
    return "".join(f'<div class="gl-row"><div class="gl-n">{_html.escape(n)}</div>'
                   f'<div class="gl-l">{_html.escape(l)}</div></div>' for n, l in cells)


FAQ = [
    ("What does the first row mean?",
     "Only that it has the largest stored trailing cash dividend divided by stored share price "
     "among observations passing the screen. It is not a quality score, forecast or recommendation."),
    ("Why can a trailing dividend yield be misleading?",
     "The numerator can include special or non-recurring cash payouts, while the denominator can "
     "fall sharply. The result says nothing by itself about future distributions or total return."),
    ("How is the screen reproduced?",
     "Sum cash dividends announced in the trailing period after converting declared percentages "
     "using the recorded face value, divide by the dated market price, and sort descending. Verify "
     "face value, announcements and price against each issuer's PSX records."),
    ("Is this page live?",
     "No. The page displays its stored price date and payout-announcement cutoff. It remains a "
     "dated snapshot until both source partitions are collected and the page is rebuilt."),
]


def faq_html():
    items, ld = [], []
    for q, a in FAQ:
        items.append(f'<details class="faq-item"><summary class="faq-question">'
                     f'{_html.escape(q)}</summary><div class="faq-answer">{_html.escape(a)}</div></details>')
        ld.append({"@type": "Question", "name": q,
                   "acceptedAnswer": {"@type": "Answer", "text": a}})
    return "".join(items), ld


def _snap_week(s):
    m = re.search(r'(?:Week of|Snapshot dated) ([0-9-]+)', s)
    return m.group(1) if m else None


def changelog(existing, data_date, rows):
    top = rows[0] if rows else None
    over8 = sum(1 for s in rows if s["yield"] >= 8)
    snap = (f'<div class="snap"><strong>Snapshot dated {data_date}.</strong> '
            f'First row after a descending trailing-yield sort: '
            f'{_html.escape(top["name"])} ({top["ticker"]}) at '
            f'{top["yield"]:.2f}%. {over8} of the first 10 rows are at least 8%.</div>') if top else ""
    snaps = re.findall(r'<div class="snap">.*?</div>', existing, re.S)
    snaps = [s for s in snaps if _snap_week(s) != data_date]
    return "".join(([snap] + snaps)[:8])


def _extract_changelog(html):
    m = re.search(r'<div class="changelog">(.*?)</div>\s*<h2', html, re.S)
    return m.group(1) if m else ""


def _extract_published(html):
    m = re.search(r'"datePublished":\s*"([^"]+)"', html); return m.group(1) if m else None


def build_jsonld(rows, published, today, canonical, h1):
    article = {"@context": "https://schema.org", "@type": "Article", "headline": h1,
               "datePublished": published, "dateModified": today,
               "author": {"@type": "Person", "name": "Abdul Ahad"},
               "publisher": {"@type": "Organization", "name": "Pakistan Investment Education"},
               "mainEntityOfPage": canonical}
    itemlist = {"@context": "https://schema.org", "@type": "ItemList",
                "name": "Dated PSX trailing dividend-yield screen", "itemListOrder": "Descending",
                "numberOfItems": len(rows),
                "itemListElement": [{"@type": "ListItem", "position": i,
                                     "name": f'{s["name"]} ({s["ticker"]})'}
                                    for i, s in enumerate(rows, 1)]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                  {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog/"},
                  {"@type": "ListItem", "position": 3, "name": h1, "item": canonical}]}
    return "\n".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>'
                     for b in (article, itemlist, crumbs))


def render(today):
    data = json.loads((ROOT / "data.json").read_text())
    partition_path = ROOT / "data" / "partitions" / "dividends.json"
    partition = json.loads(partition_path.read_text()) if partition_path.exists() else {}
    hp = ROOT / "data" / "stock_history.json"
    hist = json.loads(hp.read_text()) if hp.exists() else {}
    full = all_payers(data)
    rows = full[:TOPN]
    tmpl = (ROOT / "scripts/templates/dividends.html").read_text()

    page = ROOT / "blog" / f"{SLUG}.html"
    published, existing_cl = today, ""
    if page.exists():
        old = page.read_text()
        published = _extract_published(old) or today
        existing_cl = _extract_changelog(old)

    data_date = (data.get("updated") or today)[:10]
    payout_date = partition.get("latest_announce")
    market_health = (data.get("data_health") or {}).get("stocks") or {}
    payout_health = (data.get("data_health") or {}).get("dividends") or {}
    market_label = market_health.get("as_of") or data_date
    payout_label = payout_date or "not published in the partition"
    status_bits = [
        f"PSX price observation: {_html.escape(str(market_label))}.",
        f"Cash-dividend announcements included through: {_html.escape(str(payout_label))}.",
        f"Price collection status: {'successful' if market_health.get('ok') else 'failed or unavailable'}.",
        f"Payout collection status: {'successful' if payout_health.get('ok') else 'failed or unavailable'}.",
        "A failed refresh leaves the last stored observations in place; it does not make them current.",
    ]
    data_status = " ".join(status_bits)

    h1 = "PSX trailing dividend-yield dataset"
    top = rows[0] if rows else None
    tldr = (f"A dated mechanical sort, not a buy list. Prices are from {data_date}; "
            f"stored cash-dividend announcements run through {payout_label}. "
            f"{top['ticker']} is the first row, which means only that its stored trailing "
            f"yield is largest in this dataset.") if top else \
           f"A dated PSX dividend dataset as of {data_date}; no positive-yield rows are available."
    title = "PSX Dividend-Yield Dataset 2026: Dated Payout & Price Screen"
    meta_desc = (f"Dated PSX trailing dividend-yield dataset using prices from {data_date} "
                 f"and cash-dividend records through {payout_label}, with formula and source checks.")
    canonical = f"{SITE}/blog/{SLUG}.html"
    faq_h, _faq_ld = faq_html()
    related = "".join(f'<a href="{h}">{t}</a>' for h, t in [
        ("/blog/how-to-value-bank-stocks-pakistan.html", "How to value a Pakistani bank stock"),
        ("/guides/investment-tax-pakistan.html", "How investments (and dividends) are taxed"),
        ("/guides/open-brokerage-account-psx.html", "How to open a PSX brokerage account"),
        ("/guides/how-to-invest-mutual-funds-pakistan.html", "Prefer a fund? Mutual funds explained"),
        ("/blog/", "All blog articles")])

    repl = {
        "{{TITLE}}": _html.escape(title, quote=True),
        "{{META_DESC}}": _html.escape(meta_desc, quote=True),
        "{{CANONICAL}}": canonical,
        "{{OG_IMAGE}}": OG, "{{H1}}": h1, "{{TLDR}}": _html.escape(tldr), "{{AS_OF}}": today,
        "{{DATA_AS_OF}}": data_date, "{{DATA_STATUS}}": data_status,
        "{{GLANCE}}": glance_html(rows, len(full), data_date, payout_date), "{{TABLE}}": table_html(rows, hist),
        "{{FULL_TABLE}}": table_html(full, hist), "{{FULL_COUNT}}": str(len(full)),
        "{{TBL_NOTE}}": (f"Dated price snapshot: {data_date}. Stored cash-dividend announcements "
                         f"through {payout_label}. Sorted by trailing cash dividend per share divided "
                         f"by stored price. Values require issuer-level verification."),
        "{{CARDS}}": cards_html(rows, hist), "{{CHANGELOG}}": changelog(existing_cl, data_date, rows),
        "{{FAQ}}": faq_h, "{{RELATED}}": related, "{{RAIL_GLANCE}}": rail_glance(rows, data_date, len(full)),
        "{{JSONLD}}": build_jsonld(rows, published, today, canonical, h1),
    }
    out = tmpl
    for k, v in repl.items():
        out = out.replace(k, v)
    page.write_text(out, encoding="utf-8")
    return page


if __name__ == "__main__":
    today = sys.argv[1] if len(sys.argv) > 1 else None
    if not today:
        print("usage: build_dividends.py YYYY-MM-DD", file=sys.stderr); sys.exit(2)
    print("wrote", render(today))
