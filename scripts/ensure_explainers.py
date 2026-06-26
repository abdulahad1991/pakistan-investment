#!/usr/bin/env python3
"""Ensure every blog has a 60s Urdu explainer + the player embedded. Idempotent.

For each blog/*.html (skips *index* and *v1-backup*):
  - if assets/blog-audio/<slug>.json is missing -> generate it (build_explainer)
  - if the page lacks the player -> embed <div class="blog-explainer"> + the script

Run locally (in the Pillow/edge-tts venv) or in CI. Safe to re-run: it only
touches blogs that are missing audio or the embed. This is the "habit": new
blogs get an explainer on the next run.
"""
import sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_explainer as bx

AUDIO = ROOT / "assets" / "blog-audio"


def blogs():
    for p in sorted((ROOT / "blog").glob("*.html")):
        n = p.name
        if "index" in n or "v1-backup" in n:
            continue
        yield p


def embed(html, slug):
    div = f'<div class="blog-explainer" data-explainer="{slug}"></div>'
    if 'class="blog-explainer"' not in html:
        if '<p class="lead">' in html:
            html = html.replace('<p class="lead">', div + '\n\n      <p class="lead">', 1)
        elif re.search(r'<h2[ >]', html):
            html = re.sub(r'(<h2[ >])', div + r'\n\n      \1', html, count=1)
        else:
            html = html.replace('<div class="prose">', '<div class="prose">\n      ' + div, 1)
    if "blog-explainer.js" not in html:
        html = html.replace("</body>", '<script src="/assets/blog-explainer.js" defer></script>\n</body>', 1)
    return html


def main():
    made, embedded, failed = [], [], []
    for p in blogs():
        slug = p.stem
        manifest = AUDIO / f"{slug}.json"
        if not manifest.exists():
            try:
                bx.build(slug)
                made.append(slug)
            except Exception as e:
                print(f"  FAIL {slug}: {e}", file=sys.stderr)
                failed.append(slug)
                continue
        if not manifest.exists():
            continue
        html = p.read_text(encoding="utf-8")
        new = embed(html, slug)
        if new != html:
            p.write_text(new, encoding="utf-8")
            embedded.append(slug)
    print(f"generated audio: {len(made)} {made}")
    print(f"embedded player: {len(embedded)} {embedded}")
    if failed:
        print(f"failed: {failed}")


if __name__ == "__main__":
    main()
