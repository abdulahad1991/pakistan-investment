#!/usr/bin/env python3
"""Orchestrate one publish run: news -> pick sector -> render -> audit -> register.

Rotation state lives in data/blog_state.json so each weekday run advances to the
next sector. `today` is passed in (CI supplies `date -u +%F`) for determinism.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "blog_state.json"

sys.path.insert(0, str(ROOT / "scripts"))
import fetch_news, render_sector, audit_post, register_post   # noqa: E402


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"index": 0, "history": []}


def pick_next(state, sectors):
    i = state.get("index", 0)
    slug = sectors[i % len(sectors)]["slug"]
    state = dict(state)
    state["index"] = i + 1
    return slug, state


def main(today):
    sectors = json.loads((ROOT / "scripts/sectors.json").read_text())
    try:
        fetch_news.main()
    except Exception as e:
        print(f"news fetch failed (continue): {e}", file=sys.stderr)
    state = load_state()
    slug, state = pick_next(state, sectors)
    cfg = next(s for s in sectors if s["slug"] == slug)
    path = render_sector.render(slug, today)
    res = audit_post.audit(path)
    audit_post.main(str(path))   # opens a gh issue if flagged
    register_post.register(slug, cfg["title"], cfg["tldr"][:155], today)
    state["history"] = ([{"slug": slug, "date": today,
                          "ok": res["ok"], "words": res["words"]}]
                        + state.get("history", []))[:60]
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    print(f"published {slug} ({today}) ok={res['ok']} words={res['words']}")


if __name__ == "__main__":
    today = sys.argv[1] if len(sys.argv) > 1 else None
    if not today:
        print("usage: run_blog_engine.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    main(today)
