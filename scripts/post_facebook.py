#!/usr/bin/env python3
"""Auto-post the daily brief to a Facebook PAGE as SEPARATE posts.

Daily (default) — three independent posts, each its own image + caption:
  * MARKET  ← video/out/daily/card.png    + facebook.market
  * PETROL  ← video/out/daily/petrol.png   + facebook.petrol
  * REEL    ← video/out/daily/short.mp4     + facebook.reel   (Reels API)
Weekly (--weekly, Fridays) — the weekly digest:
  * IMAGE   ← video/out/weekly/digest.png   + facebook.image
  * VIDEO   ← video/out/weekly/review.mp4    + facebook.video  (Reels API)

Copy comes from build_daily.py / build_weekly.py, in
social-kit/{daily,weekly}/<YYYY-MM-DD>.json -> "facebook".

CI contract (same as the other posters): missing creds -> skip + exit 0;
a post fails -> exit 1 (the step is continue-on-error, so posting never blocks
the data/render pipeline). Each post is attempted independently, so one failing
never stops the others.

Facebook PAGE tokens minted from a long-lived user token do NOT expire.
Mint one with scripts/get_facebook_token.py. Full setup: social-kit/AUTOPOST_SETUP.md.

Env: FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
     FB_MODE (daily only: all|market|petrol|reel, default all)
     FB_API_VERSION (optional, default v21.0)
Run: python scripts/post_facebook.py [--weekly] [--caption PATH]
"""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION = os.environ.get("FB_API_VERSION") or "v21.0"


def _skip(msg):
    print(f"[post_facebook] skip: {msg}")
    sys.exit(0)


def _load_facebook(caption_path):
    if not os.path.exists(caption_path):
        _skip(f"no caption payload at {caption_path}")
    with open(caption_path, encoding="utf-8") as f:
        fb = json.load(f).get("facebook")
    if not fb:
        _skip("caption payload has no 'facebook' block (rebuild with build_daily.py)")
    return fb


def _post_photo(requests, graph, page_id, token, image_path, message, label):
    """Photo post (image + caption). Returns the post id, or None if no image."""
    if not os.path.exists(image_path):
        print(f"[post_facebook] {label} skip: no image at {image_path}")
        return None
    with open(image_path, "rb") as img:
        r = requests.post(
            f"{graph}/{page_id}/photos",
            data={"message": message, "access_token": token},
            files={"source": img},
            timeout=120,
        )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{label} photo {r.status_code}: {r.text}")
    body = r.json()
    pid = body.get("post_id") or body.get("id", "")
    print(f"[post_facebook] {label} posted: https://www.facebook.com/{pid}")
    return pid


def _post_reel(requests, graph, page_id, token, video_path, description, label):
    """Publish a video as a Facebook Reel via the 3-phase upload."""
    if not os.path.exists(video_path):
        print(f"[post_facebook] {label} skip: no video at {video_path}")
        return None
    size = os.path.getsize(video_path)
    r = requests.post(f"{graph}/{page_id}/video_reels",
                      data={"upload_phase": "start", "access_token": token}, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{label} reel start {r.status_code}: {r.text}")
    start = r.json()
    video_id = start["video_id"]
    upload_url = start.get("upload_url") or (
        f"https://rupload.facebook.com/video-upload/{_VERSION}/{video_id}")
    with open(video_path, "rb") as f:
        blob = f.read()
    up = requests.post(upload_url,
                       headers={"Authorization": f"OAuth {token}",
                                "offset": "0", "file_size": str(size)},
                       data=blob, timeout=180)
    if up.status_code not in (200, 201) or not up.json().get("success", True):
        raise RuntimeError(f"{label} reel upload {up.status_code}: {up.text}")
    r = requests.post(f"{graph}/{page_id}/video_reels",
                      data={"upload_phase": "finish", "video_id": video_id,
                            "video_state": "PUBLISHED", "description": description,
                            "access_token": token}, timeout=60)
    if r.status_code not in (200, 201) or not r.json().get("success", True):
        raise RuntimeError(f"{label} reel finish {r.status_code}: {r.text}")
    print(f"[post_facebook] {label} reel published: video_id {video_id}")
    return video_id


def main():
    ap = argparse.ArgumentParser(description="Post the brief to a Facebook page")
    ap.add_argument("--weekly", action="store_true",
                    help="post the weekly digest (image + video) instead of the daily posts")
    ap.add_argument("--caption", help="override the caption payload .json path")
    args = ap.parse_args()

    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not (page_id and token):
        _skip("FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN not set")

    graph = f"https://graph.facebook.com/{_VERSION}"
    file_str = datetime.date.today().strftime("%Y-%m-%d")
    import requests  # only needed once we're actually posting

    if args.weekly:
        caption = args.caption or os.path.join(ROOT, "social-kit", "weekly", f"{file_str}.json")
        fb = _load_facebook(caption)
        wk = os.path.join(ROOT, "video", "out", "weekly")
        jobs = [
            ("weekly-image", lambda: _post_photo(
                requests, graph, page_id, token,
                os.path.join(wk, "digest.png"), fb.get("image", ""), "weekly-image")),
            ("weekly-video", lambda: _post_reel(
                requests, graph, page_id, token,
                os.path.join(wk, "review.mp4"), fb.get("video", ""), "weekly-video")),
        ]
    else:
        caption = args.caption or os.path.join(ROOT, "social-kit", "daily", f"{file_str}.json")
        fb = _load_facebook(caption)
        d = os.path.join(ROOT, "video", "out", "daily")
        all_jobs = [
            ("market", lambda: _post_photo(
                requests, graph, page_id, token,
                os.path.join(d, "card.png"), fb.get("market", ""), "market")),
            ("petrol", lambda: _post_photo(
                requests, graph, page_id, token,
                os.path.join(d, "petrol.png"), fb.get("petrol", ""), "petrol")),
            ("reel", lambda: _post_reel(
                requests, graph, page_id, token,
                os.path.join(d, "short.mp4"), fb.get("reel", ""), "reel")),
        ]
        mode = (os.environ.get("FB_MODE") or "all").strip().lower()
        jobs = all_jobs if mode == "all" else [(k, fn) for k, fn in all_jobs if k == mode]
        if not jobs:
            _skip(f"FB_MODE={mode!r} matched no post")

    failures = []
    for label, fn in jobs:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"[post_facebook] ERROR ({label}): {e}")
            failures.append(label)
    if failures:
        sys.exit(1)  # continue-on-error in CI; surfaces failures without blocking


if __name__ == "__main__":
    main()
