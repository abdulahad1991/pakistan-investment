#!/usr/bin/env python3
"""Auto-post today's daily brief to a Facebook PAGE — a Reel + a data-board post.

Two posts per run (matching the user's ask), driven by the copy that
build_daily.py emits in social-kit/daily/<YYYY-MM-DD>.json -> "facebook":
  * REEL  ← video/out/daily/short.mp4 (9:16), published via the Reels API
            (start → upload → finish). Caption = facebook.reel.
  * FEED  ← a page post whose message IS the full market board (petrol, HSD,
            kerosene, LDO, KSE-100, USD/PKR, policy rate, inflation, gold).
            Posted as a photo (video/out/daily/card.png, the DailyCard still)
            so it gets image reach; falls back to a plain text post if the
            still is missing. Message = facebook.feed.

Same CI contract as the other posters:
  * Missing creds            -> skip + exit 0 (no-op).
  * A post fails             -> error + exit 1 (the workflow step is
                                `continue-on-error`, so it never blocks the
                                data / homepage pipeline).

Facebook PAGE tokens minted from a long-lived user token do NOT expire (they
live as long as you stay a page admin), so unlike LinkedIn there is no periodic
refresh chore. Mint one with scripts/get_facebook_token.py. Full setup:
social-kit/AUTOPOST_SETUP.md.

Env (GitHub secrets): FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
                      FB_MODE (optional: both|reel|feed, default both)
                      FB_API_VERSION (optional, default v21.0)
Run: python scripts/post_facebook.py
"""
import datetime
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _skip(msg):
    print(f"[post_facebook] skip: {msg}")
    sys.exit(0)


def _load_facebook_copy():
    file_str = datetime.date.today().strftime("%Y-%m-%d")
    payload_path = os.path.join(ROOT, "social-kit", "daily", f"{file_str}.json")
    if not os.path.exists(payload_path):
        _skip(f"no caption payload at {payload_path}")
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
    fb = payload.get("facebook")
    if not fb:
        _skip("caption payload has no 'facebook' block (rebuild with build_daily.py)")
    return fb


def _post_feed(requests, graph, page_id, token, message):
    """Photo post with the DailyCard still (best reach) + the full-board message;
    plain text post if the still isn't there. Returns the new post id."""
    card = os.path.join(ROOT, "video", "out", "daily", "card.png")
    if os.path.exists(card):
        with open(card, "rb") as img:
            r = requests.post(
                f"{graph}/{page_id}/photos",
                data={"message": message, "access_token": token},
                files={"source": img},
                timeout=120,
            )
        kind = "photo"
    else:
        r = requests.post(
            f"{graph}/{page_id}/feed",
            data={"message": message, "access_token": token},
            timeout=60,
        )
        kind = "text"
    if r.status_code not in (200, 201):
        raise RuntimeError(f"feed ({kind}) {r.status_code}: {r.text}")
    body = r.json()
    post_id = body.get("post_id") or body.get("id", "")
    print(f"[post_facebook] feed {kind} posted: "
          f"https://www.facebook.com/{post_id}")
    return post_id


def _post_reel(requests, graph, page_id, token, description):
    """Publish the 9:16 Short as a Facebook Reel via the 3-phase upload."""
    video = os.path.join(ROOT, "video", "out", "daily", "short.mp4")
    if not os.path.exists(video):
        print(f"[post_facebook] reel skip: no render at {video}")
        return None
    size = os.path.getsize(video)

    # 1. start -> video_id + upload_url
    r = requests.post(f"{graph}/{page_id}/video_reels",
                      data={"upload_phase": "start", "access_token": token},
                      timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"reel start {r.status_code}: {r.text}")
    start = r.json()
    video_id = start["video_id"]
    upload_url = start.get("upload_url") or (
        f"https://rupload.facebook.com/video-upload/{_VERSION}/{video_id}")

    # 2. upload the bytes (single shot; our clip is a few MB)
    with open(video, "rb") as f:
        blob = f.read()
    up = requests.post(upload_url,
                       headers={"Authorization": f"OAuth {token}",
                                "offset": "0", "file_size": str(size)},
                       data=blob, timeout=180)
    if up.status_code not in (200, 201) or not up.json().get("success", True):
        raise RuntimeError(f"reel upload {up.status_code}: {up.text}")

    # 3. finish -> publish (Facebook publishes once processing completes)
    r = requests.post(f"{graph}/{page_id}/video_reels",
                      data={"upload_phase": "finish", "video_id": video_id,
                            "video_state": "PUBLISHED", "description": description,
                            "access_token": token}, timeout=60)
    if r.status_code not in (200, 201) or not r.json().get("success", True):
        raise RuntimeError(f"reel finish {r.status_code}: {r.text}")

    # Best-effort: wait briefly for processing so a hard error surfaces in logs.
    deadline = time.time() + 60
    while time.time() < deadline:
        g = requests.get(f"{graph}/{video_id}",
                         params={"fields": "status", "access_token": token},
                         timeout=30)
        if g.status_code == 200:
            vs = (g.json().get("status") or {}).get("video_status")
            if vs in ("ready", "published"):
                break
            if vs == "error":
                raise RuntimeError(f"reel processing error: {g.text}")
        time.sleep(6)
    print(f"[post_facebook] reel published: video_id {video_id}")
    return video_id


# Module-global so _post_reel's upload_url fallback can see the API version.
_VERSION = os.environ.get("FB_API_VERSION") or "v21.0"


def main():
    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not (page_id and token):
        _skip("FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN not set")

    mode = (os.environ.get("FB_MODE") or "both").strip().lower()
    if mode not in ("both", "reel", "feed"):
        mode = "both"
    graph = f"https://graph.facebook.com/{_VERSION}"

    fb = _load_facebook_copy()
    import requests  # only needed once we're actually posting

    failures = []
    if mode in ("both", "feed"):
        try:
            _post_feed(requests, graph, page_id, token, fb.get("feed", ""))
        except Exception as e:  # noqa: BLE001
            print(f"[post_facebook] ERROR (feed): {e}")
            failures.append("feed")
    if mode in ("both", "reel"):
        try:
            _post_reel(requests, graph, page_id, token, fb.get("reel", ""))
        except Exception as e:  # noqa: BLE001
            print(f"[post_facebook] ERROR (reel): {e}")
            failures.append("reel")

    if failures:
        sys.exit(1)  # continue-on-error in CI; surfaces the failure without blocking


if __name__ == "__main__":
    main()
