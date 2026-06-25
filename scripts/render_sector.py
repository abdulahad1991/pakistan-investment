#!/usr/bin/env python3
"""Render/refresh a living sector hub page from template + live data + news.

One canonical page per sector (no new URLs per run). Each refresh swaps the
live figures and news, prepends a dated changelog snapshot, and bumps the
JSON-LD dateModified. Pure string composition - no AI, no network.
"""
import json, re, html as _html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://pakinvestlysis.com"
OG_DEFAULT = f"{SITE}/assets/og/blog-index.png"   # reuse an existing OG png


def fmt_pkr(n):
    """Pakistani digit grouping X,XX,XXX (no decimals), mirroring formatPKR()."""
    n = float(n)
    neg = n < 0
    whole = int(round(abs(n)))
    s = str(whole)
    if len(s) <= 3:
        grouped = s
    else:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(?<=\d)(?=(\d\d)+$)", ",", head)
        grouped = f"{head},{tail}"
    return ("-" if neg else "") + grouped


def _sector_stocks(data_sector):
    data = json.loads((ROOT / "data.json").read_text())
    rows = [s for s in data["stocks"]
            if s.get("sector") == data_sector and s.get("price", 0) > 0]
    rows.sort(key=lambda s: s.get("chg1y", 0), reverse=True)
    return rows


def perf_table(rows):
    rows = [s for s in rows if s.get("price", 0) > 0]   # never show a ₨0 row
    if not rows:
        return "<p>Live figures are refreshing - check back shortly.</p>"
    out = ['<table class="perf-table"><thead><tr><th>Company</th><th>Price (PKR)</th>',
           '<th>1Y %</th><th>Div yield</th><th>P/E</th></tr></thead><tbody>']
    for s in rows:
        up = s.get("chg1y", 0) >= 0
        cls = "perf-up" if up else "perf-down"
        sign = "+" if up else ""
        out.append(f'<tr><td>{_html.escape(s["name"])} ({s["ticker"]})</td>'
                   f'<td>&#8360; {fmt_pkr(s["price"])}</td>'
                   f'<td class="{cls}">{sign}{s.get("chg1y", 0):.1f}%</td>'
                   f'<td>{s.get("yield", 0):.2f}%</td>'
                   f'<td>{s.get("pe", 0):.1f}</td></tr>')
    out.append("</tbody></table>")
    return "".join(out)


def movers_line(rows):
    if not rows:
        return ""
    top, bot = rows[0], rows[-1]
    return (f"Over the past year the strongest listed name here is {top['name']} "
            f"({top['ticker']}, {top.get('chg1y', 0):+.1f}%) and the weakest is "
            f"{bot['name']} ({bot['ticker']}, {bot.get('chg1y', 0):+.1f}%). "
            f"Past performance is not a forecast.")


def news_html(items):
    if not items:
        return "<li>No fresh headlines in the last two weeks.</li>"
    out = []
    for it in items:
        t = _html.escape(it["title"])
        u = _html.escape(it["url"])
        src = _html.escape(it.get("source", ""))
        out.append(f'<li><a href="{u}" rel="nofollow noopener" target="_blank">{t}</a>'
                   f' <span class="src">{src}</span></li>')
    return "".join(out)


def faq_block(faq):
    html_items, ld = [], []
    for qa in faq:
        html_items.append(f'<div class="faq-item"><h3>{_html.escape(qa["q"])}</h3>'
                          f'<p>{_html.escape(qa["a"])}</p></div>')
        ld.append({"@type": "Question", "name": qa["q"],
                   "acceptedAnswer": {"@type": "Answer", "text": qa["a"]}})
    return "".join(html_items), ld


def changelog_append(existing_html, snap_html, cap=8):
    snaps = re.findall(r'<div class="snap">.*?</div>', existing_html, re.S)
    snaps = [snap_html] + snaps
    return "".join(snaps[:cap])


def _extract_changelog(html):
    m = re.search(r'<div class="changelog">(.*?)</div>\s*</section>', html, re.S)
    return m.group(1) if m else ""


def _extract_published(html):
    m = re.search(r'"datePublished":\s*"([^"]+)"', html)
    return m.group(1) if m else None


def build_jsonld(meta, faq_ld):
    article = {"@context": "https://schema.org", "@type": "Article",
               "headline": meta["h1"], "datePublished": meta["published"],
               "dateModified": meta["modified"],
               "author": {"@type": "Person", "name": "Abdul Ahad"},
               "publisher": {"@type": "Organization", "name": "Pakistan Investment Advisor"},
               "mainEntityOfPage": meta["canonical"]}
    faqpage = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_ld}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                  {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog/"},
                  {"@type": "ListItem", "position": 3, "name": meta["h1"], "item": meta["canonical"]}]}
    return "\n".join(
        f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>'
        for b in (article, faqpage, crumbs))


def render(slug, today):
    cfg = next(s for s in json.loads((ROOT / "scripts/sectors.json").read_text())
               if s["slug"] == slug)
    tmpl = (ROOT / "scripts/templates/sector.html").read_text()
    body = (ROOT / "scripts" / cfg["body"]).read_text()
    rows = _sector_stocks(cfg["data_sector"])

    queue = {}
    qp = ROOT / "data" / "news_queue.json"
    if qp.exists():
        queue = json.loads(qp.read_text())
    items = (queue.get(slug) or {}).get("items", [])

    page_path = ROOT / "blog" / f"{slug}.html"
    published, existing_changelog = today, ""
    if page_path.exists():
        old = page_path.read_text()
        published = _extract_published(old) or today
        existing_changelog = _extract_changelog(old)

    headline = items[0]["title"] if items else ""
    snap = (f'<div class="snap"><strong>Week of {today}.</strong> '
            f'{_html.escape(movers_line(rows))}'
            f'{" Top headline: " + _html.escape(headline) if headline else ""}</div>')
    changelog = changelog_append(existing_changelog, snap)

    faq_html, faq_ld = faq_block(cfg["faq"])
    canonical = f"{SITE}/blog/{slug}.html"
    meta = {"h1": cfg["h1"], "canonical": canonical,
            "published": published, "modified": today}
    related = "".join(f'<li><a href="{r["href"]}">{_html.escape(r["text"])}</a></li>'
                      for r in cfg["related"])

    repl = {
        "{{TITLE}}": cfg["title"], "{{META_DESC}}": cfg["tldr"][:155],
        "{{CANONICAL}}": canonical, "{{OG_IMAGE}}": OG_DEFAULT, "{{H1}}": cfg["h1"],
        "{{TLDR}}": cfg["tldr"], "{{AS_OF}}": today, "{{PERF_TABLE}}": perf_table(rows),
        "{{MOVERS}}": movers_line(rows), "{{NEWS_LIST}}": news_html(items),
        "{{CHANGELOG}}": changelog, "{{EVERGREEN_BODY}}": body, "{{FAQ_HTML}}": faq_html,
        "{{RELATED}}": related, "{{JSONLD}}": build_jsonld(meta, faq_ld),
    }
    out = tmpl
    for k, v in repl.items():
        out = out.replace(k, v)
    page_path.write_text(out, encoding="utf-8")
    return page_path
