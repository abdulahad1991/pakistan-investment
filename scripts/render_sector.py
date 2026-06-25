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
OG_DEFAULT = f"{SITE}/assets/og/blog-index.png?v=2"   # reuse an existing OG png (?v bust cache)


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
    """Editorial FAQ matching the standard blog template (details/summary in .prose)."""
    html_items, ld = [], []
    for qa in faq:
        html_items.append(
            f'<details class="faq-item"><summary class="faq-question">'
            f'{_html.escape(qa["q"])}</summary>'
            f'<div class="faq-answer">{_html.escape(qa["a"])}</div></details>')
        ld.append({"@type": "Question", "name": qa["q"],
                   "acceptedAnswer": {"@type": "Answer", "text": qa["a"]}})
    return "".join(html_items), ld


def _avg(rows, key):
    vals = [s.get(key, 0) for s in rows if s.get(key, 0)]
    return sum(vals) / len(vals) if vals else 0.0


def glance_bullets(rows):
    """The 'At a glance' callout bullets, derived from live data."""
    if not rows:
        return "<li>Live figures are refreshing - check back shortly.</li>"
    top, bot = rows[0], rows[-1]
    avg_y = _avg(rows, "yield")
    return "".join([
        f"<li><strong>{len(rows)} listed names</strong> in this group are tracked here, "
        f"with prices and ratios refreshed automatically through the week.</li>",
        f"<li><strong>Strongest over 12 months:</strong> {_html.escape(top['name'])} "
        f"({top['ticker']}, {top.get('chg1y', 0):+.1f}%); weakest: "
        f"{_html.escape(bot['name'])} ({bot['ticker']}, {bot.get('chg1y', 0):+.1f}%). "
        f"Past performance is not a forecast.</li>",
        f"<li><strong>Average dividend yield</strong> across the group is about "
        f"{avg_y:.2f}% - useful for telling income names from growth names.</li>",
        "<li>Educational only, not investment advice. Verify against the PSX and "
        "company sources before acting.</li>",
    ])


def rail_glance(rows, today):
    """Right-rail 'At a glance' stat rows, derived from live data."""
    if not rows:
        return f'<div class="gl-row"><div class="gl-n">{today}</div><div class="gl-l">Last refreshed</div></div>'
    top = rows[0]
    avg_y = _avg(rows, "yield")
    cells = [
        (str(len(rows)), "Listed names tracked"),
        (f"{top.get('chg1y', 0):+.0f}%", f"12-mo top: {top['ticker']}"),
        (f"{avg_y:.1f}%", "Avg dividend yield"),
        (today, "Last refreshed"),
    ]
    return "".join(f'<div class="gl-row"><div class="gl-n">{_html.escape(n)}</div>'
                   f'<div class="gl-l">{_html.escape(l)}</div></div>' for n, l in cells)


def rail_next(related):
    """Right-rail 'Read next' links from the sector's related list + blog index."""
    links = [f'<a href="{r["href"]}">{_html.escape(r["text"])} →</a>' for r in related[:3]]
    links.append('<a href="/blog/">All blog articles →</a>')
    return "".join(links)


def _snap_week(snap_html):
    m = re.search(r'Week of ([0-9-]+)', snap_html)
    return m.group(1) if m else None


def changelog_append(existing_html, snap_html, cap=8):
    snaps = re.findall(r'<div class="snap">.*?</div>', existing_html, re.S)
    # Drop any prior snapshot for the same week so re-renders don't duplicate it.
    wk = _snap_week(snap_html)
    if wk:
        snaps = [s for s in snaps if _snap_week(s) != wk]
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
    related = "".join(f'<a href="{r["href"]}">{_html.escape(r["text"])}</a>'
                      for r in cfg["related"])
    desk = cfg.get("desk") or f"Living Sector Page · {cfg['data_sector'].title()}"

    repl = {
        "{{TITLE}}": cfg["title"], "{{META_DESC}}": cfg["tldr"][:155],
        "{{CANONICAL}}": canonical, "{{OG_IMAGE}}": OG_DEFAULT, "{{H1}}": cfg["h1"],
        "{{DESK}}": desk, "{{TLDR}}": cfg["tldr"], "{{AS_OF}}": today,
        "{{GLANCE}}": glance_bullets(rows), "{{PERF_TABLE}}": perf_table(rows),
        "{{MOVERS}}": movers_line(rows), "{{NEWS_LIST}}": news_html(items),
        "{{CHANGELOG}}": changelog, "{{EVERGREEN_BODY}}": body, "{{FAQ_HTML}}": faq_html,
        "{{RAIL_GLANCE}}": rail_glance(rows, today), "{{RAIL_NEXT}}": rail_next(cfg["related"]),
        "{{RELATED}}": related, "{{JSONLD}}": build_jsonld(meta, faq_ld),
    }
    out = tmpl
    for k, v in repl.items():
        out = out.replace(k, v)
    page_path.write_text(out, encoding="utf-8")
    return page_path
