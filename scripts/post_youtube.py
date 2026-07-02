#!/usr/bin/env python3
"""Auto-upload a rendered brief to YouTube (public), then drop an engagement
comment on it.

Default (no args) = today's daily Short: reads the structured copy emitted by
build_daily.py (social-kit/daily/<YYYY-MM-DD>.json -> "youtube": {title,
description, tags}) and uploads <root>/video/out/daily/short.mp4 (9:16).

Weekly (or any other) video: pass explicit paths —
  python scripts/post_youtube.py \
      --video video/out/weekly/review.mp4 \
      --caption social-kit/weekly/<YYYY-MM-DD>.json
A 16:9 video over 60s is never treated as a Short by YouTube; the weekly
caption simply carries no "#Shorts" text, nothing else to do here.

After ANY successful upload a top-level comment is posted (site link + an
engagement question rotated by weekday). Pinning is impossible via the API.
The comment needs the youtube.force-ssl scope — if the stored refresh token
only has youtube.upload the comment fails with a clear warning and the step
still succeeds (comment failure must never fail the upload).

Designed to be safe in CI:
  * No credentials in env  -> prints a skip notice and exits 0 (no-op).
  * Upload fails           -> prints the error and exits 1 (the workflow step
                              is `continue-on-error`, so it never blocks the
                              data pipeline / homepage video / commit).

One-time setup (refresh token, secrets) is documented in
social-kit/AUTOPOST_SETUP.md; get the token with scripts/get_youtube_token.py
(re-mint it WITH the youtube.force-ssl scope to enable comments).

Env (GitHub secrets): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Run: python scripts/post_youtube.py [--video PATH] [--caption PATH]
"""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# upload = the video insert; force-ssl = commentThreads.insert. The token is
# refreshed WITHOUT narrowing (scopes=None below) so a legacy upload-only
# refresh token keeps uploading and a re-minted one also unlocks comments.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
CATEGORY_ID = "25"  # News & Politics — closest fit for a market brief

SITE = "https://pakinvestlysis.com"
# Rotated deterministically by weekday (Mon=0). Honest engagement bait only —
# questions, never predictions or advice from us.
COMMENT_QUESTIONS = [
    "KSE-100 is hafte 190k cross karega? Aap ki raye?",                    # Mon
    "Gold ya stocks — 2026 mein aap kis par zyada bharosa karte hain?",    # Tue
    "SBP agla policy rate cut kab karega? Kya lagta hai?",                 # Wed
    "National Savings ya mutual funds — aap kya prefer karte hain aur kyun?",  # Thu
    "Dollar is saal 300 tak jayega ya niche rahega? Comment mein batayen.",    # Fri
    "Aap ki portfolio mein gold kitna percent hai?",                       # Sat
    "Agle hafte market se kya expect kar rahe hain?",                      # Sun
]


def _skip(msg):
    print(f"[post_youtube] skip: {msg}")
    sys.exit(0)


def parse_args():
    ap = argparse.ArgumentParser(description="Upload a brief to YouTube")
    ap.add_argument("--video", help="video file to upload "
                    "(default: video/out/daily/short.mp4 — today's daily Short)")
    ap.add_argument("--caption", help="caption payload .json containing a "
                    "'youtube' block (default: social-kit/daily/<today>.json)")
    return ap.parse_args()


def post_comment(youtube, video_id):
    """Top-level engagement comment; NEVER raises — a comment failure must not
    fail the upload step."""
    from googleapiclient.errors import HttpError

    q = COMMENT_QUESTIONS[datetime.date.today().weekday() % len(COMMENT_QUESTIONS)]
    text = f"Full data, charts aur free tools: {SITE} — {q}"
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={"snippet": {
                "videoId": video_id,
                "topLevelComment": {"snippet": {"textOriginal": text}},
            }},
        ).execute()
        print(f"[post_youtube] comment posted: {q}")
    except HttpError as e:
        if e.resp.status == 403:
            print("[post_youtube] WARNING: comment failed (403 / insufficient "
                  "permissions). The stored YT_REFRESH_TOKEN lacks the "
                  "youtube.force-ssl scope — re-mint it with "
                  "scripts/get_youtube_token.py including "
                  "https://www.googleapis.com/auth/youtube.force-ssl and update "
                  "the YT_REFRESH_TOKEN secret. Upload itself succeeded.")
        else:
            print(f"[post_youtube] WARNING: comment failed ({e}); "
                  "upload itself succeeded.")
    except Exception as e:  # comment must never sink the step
        print(f"[post_youtube] WARNING: comment failed ({e}); "
              "upload itself succeeded.")


def main():
    args = parse_args()
    cid = os.environ.get("YT_CLIENT_ID")
    csecret = os.environ.get("YT_CLIENT_SECRET")
    refresh = os.environ.get("YT_REFRESH_TOKEN")
    if not (cid and csecret and refresh):
        _skip("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN not set")

    is_short = args.video is None  # default flow uploads the 9:16 daily Short
    file_str = datetime.date.today().strftime("%Y-%m-%d")
    payload_path = (os.path.join(ROOT, args.caption) if args.caption
                    else os.path.join(ROOT, "social-kit", "daily", f"{file_str}.json"))
    video_path = (os.path.join(ROOT, args.video) if args.video
                  else os.path.join(ROOT, "video", "out", "daily", "short.mp4"))
    if not os.path.exists(payload_path):
        _skip(f"no caption payload at {payload_path}")
    if not os.path.exists(video_path):
        _skip(f"no render at {video_path}")

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
        # scopes=None on purpose: refresh with whatever the token was granted.
        # Passing only youtube.upload would narrow the access token and lock
        # out commentThreads.insert even on a force-ssl-capable refresh token.
        scopes=None,
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
            # Defaults public for real runs; set YT_PRIVACY=unlisted|private to
            # test without broadcasting to subscribers.
            "privacyStatus": os.environ.get("YT_PRIVACY") or "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    want_privacy = body["status"]["privacyStatus"]
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
    got_privacy = response.get("status", {}).get("privacyStatus", "?")
    url = f"https://youtube.com/shorts/{vid}" if is_short else f"https://youtu.be/{vid}"
    print(f"[post_youtube] uploaded ({got_privacy}): {url}")
    if want_privacy == "public" and got_privacy != "public":
        print(f"[post_youtube] WARNING: requested public but got '{got_privacy}' — "
              "channel likely not phone-verified; verify at youtube.com/verify.")

    post_comment(youtube, vid)


if __name__ == "__main__":
    main()
