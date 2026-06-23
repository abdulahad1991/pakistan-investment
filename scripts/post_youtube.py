#!/usr/bin/env python3
"""Auto-upload today's daily brief Short to YouTube (public).

Reads the structured copy emitted by build_daily.py
(social-kit/daily/<YYYY-MM-DD>.json -> "youtube": {title, description, tags})
and uploads <root>/video/out/daily/short.mp4 (the 9:16 render) via the
YouTube Data API v3, authenticating non-interactively from a stored OAuth
refresh token.

Designed to be safe in CI:
  * No credentials in env  -> prints a skip notice and exits 0 (no-op).
  * Upload fails           -> prints the error and exits 1 (the workflow step
                              is `continue-on-error`, so it never blocks the
                              data pipeline / homepage video / commit).

One-time setup (refresh token, secrets) is documented in
social-kit/AUTOPOST_SETUP.md; get the token with scripts/get_youtube_token.py.

Env (GitHub secrets): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Run: python scripts/post_youtube.py
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_ID = "25"  # News & Politics — closest fit for a market brief


def _skip(msg):
    print(f"[post_youtube] skip: {msg}")
    sys.exit(0)


def main():
    cid = os.environ.get("YT_CLIENT_ID")
    csecret = os.environ.get("YT_CLIENT_SECRET")
    refresh = os.environ.get("YT_REFRESH_TOKEN")
    if not (cid and csecret and refresh):
        _skip("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN not set")

    file_str = datetime.date.today().strftime("%Y-%m-%d")
    payload_path = os.path.join(ROOT, "social-kit", "daily", f"{file_str}.json")
    video_path = os.path.join(ROOT, "video", "out", "daily", "short.mp4")
    if not os.path.exists(payload_path):
        _skip(f"no caption payload at {payload_path}")
    if not os.path.exists(video_path):
        _skip(f"no Short render at {video_path}")

    with open(payload_path, encoding="utf-8") as f:
        yt = json.load(f)["youtube"]

    # Imported here so a creds-less skip never needs the libraries installed.
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    creds = Credentials(
        token=None,  # forces a refresh from the refresh_token on first call
        refresh_token=refresh,
        client_id=cid,
        client_secret=csecret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": yt["title"][:100],
            "description": yt["description"][:5000],
            "tags": yt.get("tags", []),
            "categoryId": CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        try:
            _status, response = request.next_chunk()
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504):
                print(f"[post_youtube] transient {e.resp.status}, retrying...")
                continue
            print(f"[post_youtube] ERROR: {e}")
            sys.exit(1)

    vid = response["id"]
    print(f"[post_youtube] uploaded: https://youtube.com/shorts/{vid}")


if __name__ == "__main__":
    main()
