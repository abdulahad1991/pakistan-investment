import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

def test_universe_wellformed():
    uni = json.loads((ROOT / "scripts/psx_universe.json").read_text())
    assert isinstance(uni, dict)
    # the four content sectors must exist with >= 5 names each
    for sec in ["Automobile", "Technology", "FMCG", "Textile"]:
        assert sec in uni, f"missing sector {sec}"
        assert len(uni[sec]) >= 5, f"{sec} has too few names"
    # every entry has the three required keys and a .KA yahoo symbol
    seen = set()
    for sec, rows in uni.items():
        for r in rows:
            assert {"ticker", "name", "yahoo"} <= r.keys(), r
            assert r["yahoo"].endswith(".KA"), r
            assert r["ticker"] not in seen, f"duplicate ticker {r['ticker']}"
            seen.add(r["ticker"])
    assert len(seen) >= 80, "universe should be comprehensive (>= 80 names)"


def test_ensure_seeds_real_function():
    from stock_universe import ensure_seeds, load_universe
    uni = load_universe()
    tickers = {r["ticker"] for rows in uni.values() for r in rows}
    yahoos = {r["yahoo"] for rows in uni.values() for r in rows}
    data = {"stocks": []}
    tmap = ensure_seeds(data, uni)
    assert {s["ticker"] for s in data["stocks"]} == tickers
    assert set(tmap.keys()) == yahoos and set(tmap.values()) == tickers
    # idempotent: a second call adds nothing
    before = len(data["stocks"])
    ensure_seeds(data, uni)
    assert len(data["stocks"]) == before
    # existing live row keeps its values but gets sector/name normalised
    data2 = {"stocks": [{"ticker": "FFC", "name": "old", "sector": "old",
                         "price": 555.6, "chg1y": 45.7, "hi52": 0, "lo52": 0,
                         "div": 0, "yield": 0, "pe": 0}]}
    ensure_seeds(data2, uni)
    ffc = next(s for s in data2["stocks"] if s["ticker"] == "FFC")
    assert ffc["price"] == 555.6            # live value preserved
    assert ffc["sector"] == "Fertilizer"   # normalised from universe
    assert ffc["name"] == "Fauji Fertilizer"


def test_sectors_config():
    cfg = json.loads((ROOT / "scripts/sectors.json").read_text())
    uni = json.loads((ROOT / "scripts/psx_universe.json").read_text())
    slugs = set()
    for s in cfg:
        assert {"slug", "title", "h1", "data_sector", "news_query",
                "tldr", "faq", "body"} <= s.keys()
        assert s["data_sector"] in uni, f"{s['data_sector']} not in universe"
        assert (ROOT / "scripts" / s["body"]).exists(), s["body"]
        assert len(s["faq"]) >= 3
        assert s["slug"] not in slugs
        slugs.add(s["slug"])
    assert {"automotive-sector-pakistan", "it-sector-pakistan",
            "fmcg-sector-pakistan", "exporters-sector-pakistan"} == slugs


def test_template_has_all_tokens():
    t = (ROOT / "scripts/templates/sector.html").read_text()
    for tok in ["{{TITLE}}", "{{META_DESC}}", "{{CANONICAL}}", "{{OG_IMAGE}}",
                "{{H1}}", "{{TLDR}}", "{{AS_OF}}", "{{PERF_TABLE}}", "{{MOVERS}}",
                "{{NEWS_LIST}}", "{{CHANGELOG}}", "{{EVERGREEN_BODY}}",
                "{{FAQ_HTML}}", "{{RELATED}}", "{{JSONLD}}"]:
        assert tok in t, f"template missing {tok}"
    # live site chrome must survive the templating
    assert "assets/v2.css" in t
    assert 'id="site-nav"' in t
    assert "</html>" in t


def test_parse_google_news_rss():
    import fetch_news
    sample = '''<?xml version="1.0"?><rss><channel>
      <item><title>Auto sales rise - Business Recorder</title>
      <link>https://news.google.com/x</link>
      <pubDate>Wed, 25 Jun 2026 06:00:00 GMT</pubDate>
      <source url="https://brecorder.com">Business Recorder</source></item>
    </channel></rss>'''
    items = fetch_news.parse_rss(sample, limit=5)
    assert items[0]["title"].startswith("Auto sales rise")
    assert items[0]["source"] == "Business Recorder"
    assert items[0]["url"].startswith("http")
    # title-suffix fallback when <source> is absent
    s2 = ('<rss><channel><item><title>Tax news - Dawn</title>'
          '<link>http://d</link></item></channel></rss>')
    assert fetch_news.parse_rss(s2)[0]["source"] == "Dawn"


def test_perf_table_skips_zero_price():
    import render_sector as rs
    rows = [{"ticker": "INDU", "name": "Indus Motor", "price": 1500.5,
             "chg1y": 12.3, "yield": 4.1, "pe": 7.2},
            {"ticker": "ZERO", "name": "Unfilled", "price": 0,
             "chg1y": 0, "yield": 0, "pe": 0}]
    html = rs.perf_table(rows)
    assert "INDU" in html and "ZERO" not in html      # price==0 skipped
    assert "1,500" in html                             # Pakistani grouping
    assert rs.fmt_pkr(1234567) == "12,34,567"          # X,XX,XXX grouping


def test_changelog_prepends_and_caps():
    import render_sector as rs
    existing = '<div class="snap">old</div>'
    out = rs.changelog_append(existing, '<div class="snap">new</div>', cap=8)
    assert out.index("new") < out.index("old")         # newest first
    many = "".join(f'<div class="snap">s{i}</div>' for i in range(20))
    capped = rs.changelog_append(many, '<div class="snap">fresh</div>', cap=8)
    assert capped.count('class="snap"') == 8           # capped


def test_render_writes_page():
    import render_sector as rs
    p = rs.render("automotive-sector-pakistan", "2026-06-25")
    try:
        html = p.read_text()
        assert "{{" not in html                        # all tokens filled
        assert "<title>" in html
        assert "FAQPage" in html and "BreadcrumbList" in html and "Article" in html
        assert "assets/v2.css" in html                 # chrome survived
    finally:
        if p.exists():
            p.unlink()                                  # do not leave an artifact


def test_audit_flags_thin_and_tokens(tmp_path):
    import audit_post as ap
    bad = tmp_path / "x.html"
    bad.write_text("<html><body>short {{TLDR}}</body></html>")
    res = ap.audit(bad)
    assert res["ok"] is False
    assert any("token" in f for f in res["flags"])
    assert any("word" in f for f in res["flags"])
    assert any("disclaimer" in f for f in res["flags"])


def test_register_idempotent(tmp_path):
    import register_post as rp
    sm = tmp_path / "sitemap.xml"
    sm.write_text('<?xml version="1.0"?>\n<urlset>\n</urlset>\n')
    rp.upsert_sitemap(sm, "https://pakinvestlysis.com/blog/x.html", "2026-06-25")
    rp.upsert_sitemap(sm, "https://pakinvestlysis.com/blog/x.html", "2026-06-27")
    s = sm.read_text()
    assert s.count("blog/x.html") == 1                  # upsert, not duplicate
    assert "2026-06-27" in s and "2026-06-25" not in s  # lastmod updated
    # llms.txt: creates section once, then upserts the line
    lm = tmp_path / "llms.txt"
    lm.write_text("# Site\n\nintro\n\n## Tools\n\n- [a](b): c\n")
    rp.upsert_llms(lm, "Auto", "https://pakinvestlysis.com/blog/x.html", "desc1")
    rp.upsert_llms(lm, "Auto", "https://pakinvestlysis.com/blog/x.html", "desc2")
    t = lm.read_text()
    assert t.count("## Sector Outlooks") == 1
    assert t.count("blog/x.html") == 1 and "desc2" in t and "desc1" not in t
