#!/usr/bin/env python3
"""Auto-post today's daily brief Short to TikTok via the Content Posting API.

Reads the structured copy from build_daily.py
(social-kit/daily/<YYYY-MM-DD>.json) and uploads <root>/video/out/daily/short.mp4
(the 9:16 render) using TikTok's v2 Content Posting API, authenticating
non-interactively from a stored OAuth refresh token.

Two modes (TIKTOK_MODE):
  * "direct" (default) — POST /v2/post/publish/video/init/ then publish. Public
    auto-posting requires the TikTok app to be AUDITED; an unaudited app can only
    post at privacy SELF_ONLY (private). The script asks creator_info for the
    allowed privacy levels and picks the most public one available, so it goes
    public automatically once the app is approved.
  * "inbox" — POST /v2/post/publish/inbox/video/init/ — sends the video to the
    creator's TikTok inbox as a DRAFT to publish manually in-app. Works WITHOUT
    audit; use this until the app is approved.

Safe in CI (same contract as post_youtube.py / post_linkedin.py):
  * Missing creds      -> skip + exit 0 (no-op).
  * API/upload failure -> error + exit 1 (the workflow step is
                          `continue-on-error`, so posting never blocks the rest
                          of the pipeline).

TikTok refresh tokens last ~365 days — re-mint with scripts/get_tiktok_token.py
and update TIKTOK_REFRESH_TOKEN. Full setup: social-kit/AUTOPOST_SETUP.md

Env (GitHub secrets): TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
                      TIKTOK_MODE     (optional: direct|inbox, default direct)
                      TIKTOK_PRIVACY  (optional: default PUBLIC_TO_EVERYONE)
Run: python scripts/post_tiktok.py
"""
import datetime
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://open.tiktokapis.com/v2"
TOKEN_URL = f"{API}/oauth/token/"


def _skip(msg):
    print(f"[post_tiktok] skip: {msg}")
    sys.exit(0)


def _fail(msg):
    print(f"[post_tiktok] ERROR: {msg}")
    sys.exit(1)


def _caption(payload):
    """TikTok caption (<=2200 chars). Prefer a dedicated tiktok field, else
    compose from the hook + body, else fall back to the YouTube title."""
    tk = payload.get("tiktok")
    if isinstance(tk, dict) and tk.get("caption"):
        return tk["caption"][:2200]
    hook = (payload.get("hook") or "").strip()
    body = (payload.get("body") or "").strip()
    cap = (hook + ("\n\n" + body if body else "")).strip()
    if not cap:
        cap = payload.get("youtube", {}).get("title", "Pakistan market brief")
    return cap[:2200]


def _refresh_access_token(client_key, client_secret, refresh_token, requests):
    r = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    data = r.json()
    if r.status_code != 200 or "access_token" not in data:
        _fail(f"token refresh failed ({r.status_code}): {data}")
    # TikTok returns a (possibly rotated) refresh_token; the original stays valid
    # for its 365-day life, so we keep using the stored one — no write-back needed.
    return data["access_token"]


def _put_video(upload_url, video_bytes, requests):
    size = len(video_bytes)
    r = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
        data=video_bytes,
        timeout=120,
    )
    if r.status_code not in (200, 201, 206):
        _fail(f"video byte upload failed ({r.status_code}): {r.text[:300]}")


def main():
    client_key = os.environ.get("TIKTOK_CLIENT_KEY")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET")
    refresh_token = os.environ.get("TIKTOK_REFRESH_TOKEN")
    if not (client_key and client_secret and refresh_token):
        _skip("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / TIKTOK_REFRESH_TOKEN not set")

    file_str = datetime.date.today().strftime("%Y-%m-%d")
    payload_path = os.path.join(ROOT, "social-kit", "daily", f"{file_str}.json")
    video_path = os.path.join(ROOT, "video", "out", "daily", "short.mp4")
    if not os.path.exists(payload_path):
        _skip(f"no caption payload at {payload_path}")
    if not os.path.exists(video_path):
        _skip(f"no Short render at {video_path}")

    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
    caption = _caption(payload)

    with open(video_path, "rb") as f:
        video_bytes = f.read()
    size = len(video_bytes)

    import requests  # only needed on a real (creds-present) run

    access_token = _refresh_access_token(
        client_key, client_secret, refresh_token, requests)
    auth = {"Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"}
    # Whole file in one chunk (the Short is a few MB, well under the 64MB limit).
    source_info = {
        "source": "FILE_UPLOAD",
        "video_size": size,
        "chunk_size": size,
        "total_chunk_count": 1,
    }

    mode = (os.environ.get("TIKTOK_MODE") or "direct").lower()

    if mode == "inbox":
        # Draft to the creator's inbox — no privacy needed, works unaudited.
        r = requests.post(f"{API}/post/publish/inbox/video/init/",
                          headers=auth, json={"source_info": source_info}, timeout=30)
        data = r.json()
        if r.status_code != 200 or data.get("error", {}).get("code") not in (None, "ok"):
            _fail(f"inbox init failed ({r.status_code}): {data}")
        upload_url = data["data"]["upload_url"]
        _put_video(upload_url, video_bytes, requests)
        print(f"[post_tiktok] uploaded to inbox (draft) — publish it in the TikTok app. "
              f"publish_id={data['data'].get('publish_id')}")
        return

    # ── direct post ──────────────────────────────────────────────────
    # Ask which privacy levels this creator/app may use (unaudited -> SELF_ONLY).
    ci = requests.post(f"{API}/post/publish/creator_info/query/",
                       headers=auth, timeout=30).json()
    opts = (ci.get("data") or {}).get("privacy_level_options") or ["SELF_ONLY"]
    want = os.environ.get("TIKTOK_PRIVACY") or "PUBLIC_TO_EVERYONE"
    privacy = want if want in opts else (
        "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in opts else opts[0])

    body = {
        "post_info": {
            "title": caption,
            "privacy_level": privacy,
            "disable_comment": False,
            "disable_duet": False,
            "disable_stitch": False,
        },
        "source_info": source_info,
    }
    r = requests.post(f"{API}/post/publish/video/init/",
                      headers=auth, json=body, timeout=30)
    data = r.json()
    if r.status_code != 200 or "data" not in data or not data["data"].get("upload_url"):
        _fail(f"direct init failed ({r.status_code}): {data}")
    publish_id = data["data"]["publish_id"]
    _put_video(data["data"]["upload_url"], video_bytes, requests)

    # Poll until TikTok finishes processing/publishing.
    status = "PROCESSING"
    for _ in range(20):
        time.sleep(5)
        s = requests.post(f"{API}/post/publish/status/fetch/",
                          headers=auth, json={"publish_id": publish_id}, timeout=30).json()
        status = (s.get("data") or {}).get("status", "PROCESSING")
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            break
    if status == "PUBLISH_COMPLETE":
        print(f"[post_tiktok] published ({privacy}) publish_id={publish_id}")
        if privacy != "PUBLIC_TO_EVERYONE":
            print("[post_tiktok] NOTE: posted privately — the app is not audited yet, "
                  "so PUBLIC_TO_EVERYONE isn't available. Submit the app for audit to go public.")
    else:
        _fail(f"publish did not complete: status={status}")


if __name__ == "__main__":
    main()
