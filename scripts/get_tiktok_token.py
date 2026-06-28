#!/usr/bin/env python3
"""One-time: mint a TikTok refresh token for the auto-poster.

TikTok's Login Kit only accepts a REGISTERED redirect URI (https; localhost is
not allowed), so this uses a manual copy-the-code flow instead of a local
callback server:

  1. It prints an authorize URL — open it, log in as the posting account, approve.
  2. TikTok redirects to your app's registered Redirect URI with `?code=...`.
     The page itself can be anything (even a 404) — you just read the URL.
  3. Paste the whole redirected URL (or just the code) back here.
  4. It exchanges the code and prints TIKTOK_REFRESH_TOKEN (valid ~365 days).

Setup before running (see social-kit/AUTOPOST_SETUP.md):
  - Create a TikTok app at developers.tiktok.com, add the "Content Posting API"
    product, and register a Redirect URI (e.g. https://pakinvestlysis.com/tiktok).
  - Request scopes: video.publish (public direct post) + video.upload (drafts).

Env:
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET   (app credentials)
  TIKTOK_REDIRECT_URI                       (must EXACTLY match the registered URI)
  TIKTOK_SCOPES   (optional, default "video.publish,video.upload,user.info.basic")
Run: python scripts/get_tiktok_token.py
"""
import os
import sys
from urllib.parse import urlencode, urlparse, parse_qs

AUTHORIZE = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"


def main():
    client_key = os.environ.get("TIKTOK_CLIENT_KEY")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET")
    redirect_uri = os.environ.get("TIKTOK_REDIRECT_URI")
    scopes = os.environ.get(
        "TIKTOK_SCOPES", "video.publish,video.upload,user.info.basic")
    if not (client_key and client_secret and redirect_uri):
        sys.exit("Set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET and "
                 "TIKTOK_REDIRECT_URI (the URI registered in your TikTok app).")

    try:
        import requests
    except ImportError:
        sys.exit("pip install requests")

    q = urlencode({
        "client_key": client_key,
        "scope": scopes,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": "pakinvest",
    })
    print("\n1) Open this URL, log in as the posting account, and approve:\n")
    print(f"   {AUTHORIZE}?{q}\n")
    print("2) You'll be redirected to your Redirect URI with ?code=... in the URL.")
    pasted = input("3) Paste the FULL redirected URL (or just the code) here:\n   ").strip()

    code = pasted
    if "code=" in pasted:
        code = parse_qs(urlparse(pasted).query).get("code", [""])[0]
    code = code.split("*")[0] if "*" in code else code  # TikTok appends a *NN suffix
    if not code:
        sys.exit("No authorization code found in what you pasted.")

    r = requests.post(
        TOKEN,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    data = r.json()
    if r.status_code != 200 or "refresh_token" not in data:
        sys.exit(f"Token exchange failed ({r.status_code}): {data}")

    print("\n✅ Success. Add these as repo secrets:\n")
    print(f"   TIKTOK_CLIENT_KEY     = {client_key}")
    print(f"   TIKTOK_CLIENT_SECRET  = {client_secret}")
    print(f"   TIKTOK_REFRESH_TOKEN  = {data['refresh_token']}")
    print(f"\n   (granted scopes: {data.get('scope')}; "
          f"refresh token valid ~{round(data.get('refresh_expires_in', 31536000) / 86400)} days)\n")


if __name__ == "__main__":
    main()
