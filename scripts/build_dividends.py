#!/usr/bin/env python3
"""Render the living 'Top 10 PSX dividend stocks' page from data.json + stock_history.json.

One canonical page (no new URLs). Each run swaps the live ranking, redraws the
SVG charts, prepends a dated weekly snapshot, and bumps dateModified.
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


def sparkline(values, w=150, h=36):
    if not values or len(values) < 2:
        return ""
    up = values[-1] >= values[0]
    col = "#0B755F" if up else "#C24132"
    pts = _pts(values, w, h)
    poly = " ".join(f"{x},{y}" for x, y in pts)
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="3-year price trend">'
            f'<polyline fill="none" stroke="{col}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round" points="{poly}"/>'
            f'<circle cx="{pts[-1][0]}" cy="{pts[-1][1]}" r="2.6" fill="{col}"/></svg>')


def chart(values, w=300, h=92):
    if not values or len(values) < 2:
        return '<p class="tbl-note">History backfills on the next refresh.</p>'
    up = values[-1] >= values[0]
    col = "#0B755F" if up else "#C24132"
    fill = "rgba(11,117,95,.10)" if up else "rgba(194,65,50,.10)"
    pts = _pts(values, w, h, pad=6)
    poly = " ".join(f"{x},{y}" for x, y in pts)
    area = f"6,{h-6} " + poly + f" {w-6},{h-6}"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
            f'role="img" aria-label="monthly close">'
            f'<polygon fill="{fill}" points="{area}"/>'
            f'<polyline fill="none" stroke="{col}" stroke-width="2.2" '
            f'stroke-linejoin="round" stroke-linecap="round" points="{poly}"/>'
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
        out.append(
            f'<tr><td class="rk">{i}</td>'
            f'<td class="co"><b>{_html.escape(s["name"])}</b><span>{s["ticker"]}</span></td>'
            f'<td>&#8360; {fmt_pkr(s["price"])}</td>'
            f'<td>&#8360; {fmt_pkr(s.get("div", 0))}</td>'
            f'<td class="yld">{s.get("yield", 0):.2f}%</td>'
            f'<td class="{cls}">{sign}{chg:.1f}%</td>'
            f'<td>{s.get("pe", 0):.1f}</td>'
            f'<td>{sparkline(vals)}</td></tr>')
    out.append("</tbody></table>")
    return "".join(out)


def cards_html(rows, hist):
    out = []
    for s in rows:
        h = hist.get(s["ticker"]) or {}
        vals = h.get("values", [])
        start = vals[0] if vals else s["price"]
        chg = ((s["price"] - start) / start * 100) if start else 0
        cls = "pos" if chg >= 0 else "neg"; sign = "+" if chg >= 0 else ""
        out.append(
            f'<div class="hist-card"><div class="hc-top">'
            f'<div class="hc-name">{_html.escape(s["name"])}<span>{s["ticker"]}</span></div>'
            f'<div class="hc-yld">{s.get("yield",0):.1f}%<span>yield</span></div></div>'
            f'{chart(vals)}'
            f'<div class="hc-foot"><span>&#8360; {fmt_pkr(start)}</span>'
            f'<span class="{cls}">{sign}{chg:.1f}% 3y</span>'
            f'<span>&#8360; {fmt_pkr(s["price"])}</span></div></div>')
    return "".join(out)


def glance_html(rows, total):
    if not rows:
        return "<li>Live figures are refreshing - check back shortly.</li>"
    top = rows[0]
    avg = sum(s["yield"] for s in rows) / len(rows)
    over8 = sum(1 for s in rows if s["yield"] >= 8)
    return "".join([
        f"<li><strong>Highest trailing yield:</strong> {_html.escape(top['name'])} "
        f"({top['ticker']}) at <strong>{top['yield']:.2f}%</strong>.</li>",
        f"<li><strong>{total} listed companies</strong> currently pay a dividend; the full "
        f"ranked list with charts is on this page.</li>",
        f"<li><strong>{over8} of the top 10</strong> currently yield 8% or more; the "
        f"top-10 average is about <strong>{avg:.1f}%</strong>.</li>",
        "<li>Yields are <strong>trailing</strong> (past 12 months) and can change when "
        "a company revises its payout or its price moves.</li>",
        "<li>Dividends from listed shares are taxed (higher for non-filers). Educational "
        "only, not investment advice.</li>",
    ])


def rail_glance(rows, today, total):
    if not rows:
        return f'<div class="gl-row"><div class="gl-n">{today}</div><div class="gl-l">Last refreshed</div></div>'
    top = rows[0]; over8 = sum(1 for s in rows if s["yield"] >= 8)
    cells = [(f"{top['yield']:.1f}%", f"Top yield: {top['ticker']}"),
             (str(total), "Dividend payers"),
             (str(over8), "Top-10 yielding 8%+"),
             (today, "Last refreshed")]
    return "".join(f'<div class="gl-row"><div class="gl-n">{_html.escape(n)}</div>'
                   f'<div class="gl-l">{_html.escape(l)}</div></div>' for n, l in cells)


FAQ = [
    ("What are the highest dividend-paying stocks on the PSX right now?",
     "The table on this page ranks the top 10 listed companies by trailing dividend yield, "
     "refreshed weekly from market data. As yields move with both the dividend and the share "
     "price, the order changes over time - check the live table above for the current ranking."),
    ("Is a higher dividend yield always better?",
     "No. A very high yield can mean the share price has fallen sharply, which lifts the yield "
     "mechanically, or that a one-off payout is not repeatable. Always read the yield alongside "
     "the 12-month price trend and whether the payout is funded by recurring profit."),
    ("How are dividends taxed in Pakistan?",
     "Dividends from listed companies are subject to withholding tax, which is higher for people "
     "who are not on the Active Taxpayers List (non-filers). The exact rate depends on the company "
     "and your filer status - see our investment tax guide for current rates."),
    ("How often is this list updated?",
     "It refreshes automatically every week from the latest available prices and dividend data, "
     "and a dated snapshot is added to the weekly log on this page each time."),
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
    m = re.search(r'Week of ([0-9-]+)', s); return m.group(1) if m else None


def changelog(existing, today, rows):
    top = rows[0] if rows else None
    over8 = sum(1 for s in rows if s["yield"] >= 8)
    snap = (f'<div class="snap"><strong>Week of {today}.</strong> '
            f'Highest yield: {_html.escape(top["name"])} ({top["ticker"]}) at '
            f'{top["yield"]:.2f}%. {over8} of the top 10 yield 8% or more.</div>') if top else ""
    snaps = re.findall(r'<div class="snap">.*?</div>', existing, re.S)
    snaps = [s for s in snaps if _snap_week(s) != today]
    return "".join(([snap] + snaps)[:8])


def _extract_changelog(html):
    m = re.search(r'<div class="changelog">(.*?)</div>\s*<h2', html, re.S)
    return m.group(1) if m else ""


def _extract_published(html):
    m = re.search(r'"datePublished":\s*"([^"]+)"', html); return m.group(1) if m else None


def build_jsonld(rows, faq_ld, published, today, canonical, h1):
    article = {"@context": "https://schema.org", "@type": "Article", "headline": h1,
               "datePublished": published, "dateModified": today,
               "author": {"@type": "Person", "name": "Abdul Ahad"},
               "publisher": {"@type": "Organization", "name": "Pakistan Investment Education"},
               "mainEntityOfPage": canonical}
    itemlist = {"@context": "https://schema.org", "@type": "ItemList",
                "name": "Top 10 PSX dividend stocks", "itemListOrder": "Descending",
                "numberOfItems": len(rows),
                "itemListElement": [{"@type": "ListItem", "position": i,
                                     "name": f'{s["name"]} ({s["ticker"]})'}
                                    for i, s in enumerate(rows, 1)]}
    faqpage = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_ld}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                  {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog/"},
                  {"@type": "ListItem", "position": 3, "name": h1, "item": canonical}]}
    return "\n".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>'
                     for b in (article, itemlist, faqpage, crumbs))


def render(today):
    data = json.loads((ROOT / "data.json").read_text())
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

    h1 = "Top 10 Dividend Stocks on the Pakistan Stock Exchange"
    top = rows[0] if rows else None
    tldr = (f"The PSX's highest-yielding listed shares, ranked weekly. Right now "
            f"{top['name']} ({top['ticker']}) leads at {top['yield']:.1f}%. "
            f"Yields are trailing and a high yield can signal a falling price as much as a "
            f"generous payout - read each chart with the number.") if top else \
           "The PSX's highest-yielding listed shares, ranked and charted weekly."
    title = "Top 10 Dividend Stocks in Pakistan (PSX) 2026 - Live Yields & Charts"
    canonical = f"{SITE}/blog/{SLUG}.html"
    faq_h, faq_ld = faq_html()
    related = "".join(f'<a href="{h}">{t}</a>' for h, t in [
        ("/guides/best-dividend-stocks-psx.html", "Best Dividend Stocks on the PSX: the full guide"),
        ("/guides/investment-tax-pakistan.html", "How investments (and dividends) are taxed"),
        ("/guides/open-brokerage-account-psx.html", "How to open a PSX brokerage account"),
        ("/guides/how-to-invest-mutual-funds-pakistan.html", "Prefer a fund? Mutual funds explained"),
        ("/blog/", "All blog articles")])

    repl = {
        "{{TITLE}}": title, "{{META_DESC}}": tldr[:155], "{{CANONICAL}}": canonical,
        "{{OG_IMAGE}}": OG, "{{H1}}": h1, "{{TLDR}}": _html.escape(tldr), "{{AS_OF}}": today,
        "{{GLANCE}}": glance_html(rows, len(full)), "{{TABLE}}": table_html(rows, hist),
        "{{FULL_TABLE}}": table_html(full, hist), "{{FULL_COUNT}}": str(len(full)),
        "{{TBL_NOTE}}": (f"As of {today}. Ranked by trailing 12-month dividend yield from "
                         f"automatically scraped prices and dividends. Refreshes weekly. "
                         f"Past payouts do not guarantee future ones."),
        "{{CARDS}}": cards_html(rows, hist), "{{CHANGELOG}}": changelog(existing_cl, today, rows),
        "{{FAQ}}": faq_h, "{{RELATED}}": related, "{{RAIL_GLANCE}}": rail_glance(rows, today, len(full)),
        "{{JSONLD}}": build_jsonld(rows, faq_ld, published, today, canonical, h1),
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
