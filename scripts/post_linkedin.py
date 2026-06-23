#!/usr/bin/env python3
"""Auto-post today's daily brief video to a LinkedIn COMPANY PAGE.

Reads the structured copy from build_daily.py
(social-kit/daily/<YYYY-MM-DD>.json -> "linkedin": {text}) and posts
<root>/video/out/daily/linkedin.mp4 (the 1:1 render) to the organization
page, using the current versioned REST flow (Videos API + Posts API):

  initializeUpload -> PUT bytes -> finalizeUpload -> poll until AVAILABLE -> POST /posts

Safe in CI (same contract as post_youtube.py):
  * Missing creds -> skip + exit 0.   * API failure -> error + exit 1
    (the workflow step is `continue-on-error`, so posting never blocks the
    rest of the pipeline).

LinkedIn access tokens last ~60 days; re-mint with scripts/get_linkedin_token.py
and update the LINKEDIN_ACCESS_TOKEN secret. Full setup: social-kit/AUTOPOST_SETUP.md

Env (GitHub secrets): LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID
                      LINKEDIN_VERSION (optional, default 202606)
Run: python scripts/post_linkedin.py
"""
import datetime
import json
import os
import sys
import time
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REST = "https://api.linkedin.com/rest"


def _skip(msg):
    print(f"[post_linkedin] skip: {msg}")
    sys.exit(0)


def _fail(msg):
    print(f"[post_linkedin] ERROR: {msg}")
    sys.exit(1)


def main():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    org_id = os.environ.get("LINKEDIN_ORG_ID")
    version = os.environ.get("LINKEDIN_VERSION") or "202606"  # unset secret -> "" -> default
    if not (token and org_id):
        _skip("LINKEDIN_ACCESS_TOKEN / LINKEDIN_ORG_ID not set")

    owner = f"urn:li:organization:{org_id.split(':')[-1]}"  # accept id or full URN
    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": version,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    file_str = datetime.date.today().strftime("%Y-%m-%d")
    payload_path = os.path.join(ROOT, "social-kit", "daily", f"{file_str}.json")
    video_path = os.path.join(ROOT, "video", "out", "daily", "linkedin.mp4")
    if not os.path.exists(payload_path):
        _skip(f"no caption payload at {payload_path}")
    if not os.path.exists(video_path):
        _skip(f"no LinkedIn render at {video_path}")

    with open(payload_path, encoding="utf-8") as f:
        text = json.load(f)["linkedin"]["text"]
    size = os.path.getsize(video_path)

    import requests  # only needed once we're actually posting

    # 1. initializeUpload
    r = requests.post(
        f"{REST}/videos?action=initializeUpload",
        headers=headers,
        json={"initializeUploadRequest": {"owner": owner, "fileSizeBytes": size,
                                          "uploadCaptions": False, "uploadThumbnail": False}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        _fail(f"initializeUpload {r.status_code}: {r.text}")
    val = r.json()["value"]
    video_urn = val["video"]
    instructions = val["uploadInstructions"]
    upload_token = val.get("uploadToken", "")

    # 2. PUT the bytes (single part for our small <4MB clip). No auth headers on
    #    the pre-signed DMS URL; capture each part's ETag in order.
    with open(video_path, "rb") as f:
        blob = f.read()
    part_ids = []
    for ins in instructions:
        first, last = ins.get("firstByte", 0), ins.get("lastByte", len(blob) - 1)
        put = requests.put(
            ins["uploadUrl"],
            data=blob[first:last + 1],
            headers={"Content-Type": "application/octet-stream"},
            timeout=120,
        )
        if put.status_code not in (200, 201):
            _fail(f"upload PUT {put.status_code}: {put.text}")
        etag = put.headers.get("etag") or put.headers.get("ETag")
        if not etag:
            _fail("upload PUT returned no ETag")
        part_ids.append(etag)

    # 3. finalizeUpload
    r = requests.post(
        f"{REST}/videos?action=finalizeUpload",
        headers=headers,
        json={"finalizeUploadRequest": {"video": video_urn, "uploadToken": upload_token,
                                        "uploadedPartIds": part_ids}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        _fail(f"finalizeUpload {r.status_code}: {r.text}")

    # 4. Poll until the video is processed (else the post can fail / break).
    encoded = quote(video_urn, safe="")
    deadline = time.time() + 150
    status = None
    while time.time() < deadline:
        g = requests.get(f"{REST}/videos/{encoded}", headers=headers, timeout=30)
        if g.status_code == 200:
            status = g.json().get("status")
            if status == "AVAILABLE":
                break
            if status == "PROCESSING_FAILED":
                _fail("video PROCESSING_FAILED")
        time.sleep(5)
    if status != "AVAILABLE":
        _fail(f"video not AVAILABLE before timeout (last status: {status})")

    # 5. Create the post.
    post = {
        "author": owner,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                         "thirdPartyDistributionChannels": []},
        "content": {"media": {"title": "Pakistan Daily Market Brief", "id": video_urn}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    r = requests.post(f"{REST}/posts", headers=headers, json=post, timeout=30)
    if r.status_code != 201:
        _fail(f"create post {r.status_code}: {r.text}")
    post_urn = r.headers.get("x-restli-id", "")
    print(f"[post_linkedin] posted: https://www.linkedin.com/feed/update/{post_urn}/")


if __name__ == "__main__":
    main()
