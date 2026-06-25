#!/usr/bin/env python3
"""Idempotently register a sector page in sitemap.xml and llms.txt."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://pakinvestlysis.com"


def upsert_sitemap(path, loc, lastmod):
    xml = Path(path).read_text(encoding="utf-8")
    block = (f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
             f"    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>\n")
    if loc in xml:
        xml = re.sub(rf"(<loc>{re.escape(loc)}</loc>\s*<lastmod>)[^<]+(</lastmod>)",
                     rf"\g<1>{lastmod}\g<2>", xml)
    else:
        xml = xml.replace("</urlset>", block + "</urlset>")
    Path(path).write_text(xml, encoding="utf-8")


def upsert_llms(path, title, url, desc):
    txt = Path(path).read_text(encoding="utf-8")
    line = f"- [{title}]({url}): {desc}\n"
    if url in txt:
        txt = re.sub(rf"- \[[^\]]*\]\({re.escape(url)}\):[^\n]*\n", line, txt)
    elif "## Sector Outlooks" in txt:
        txt = txt.replace("## Sector Outlooks\n", "## Sector Outlooks\n\n" + line, 1)
    else:
        # add the section before the last top-level "## " heading
        m = list(re.finditer(r"^## ", txt, re.M))
        insert_at = m[-1].start() if m else len(txt)
        txt = txt[:insert_at] + f"## Sector Outlooks\n\n{line}\n" + txt[insert_at:]
    Path(path).write_text(txt, encoding="utf-8")


def register(slug, title, desc, today):
    url = f"{SITE}/blog/{slug}.html"
    upsert_sitemap(ROOT / "sitemap.xml", url, today)
    upsert_llms(ROOT / "llms.txt", title, url, desc)


if __name__ == "__main__":
    import sys
    register(*sys.argv[1:])
