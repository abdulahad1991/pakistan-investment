#!/usr/bin/env python3
"""ONE-TIME, LOCAL: mint a long-lived Facebook PAGE access token + find the page id.

Run on your laptop. A browser opens; log in as a Facebook user who is an ADMIN
of the target Page and approve. It exchanges the code for a long-lived USER
token, then reads /me/accounts and prints, for every page you admin:
  * FB_PAGE_ID
  * FB_PAGE_ACCESS_TOKEN   (derived from a long-lived user token -> effectively
                            NON-EXPIRING; store once as a GitHub secret, no
                            periodic refresh chore like LinkedIn)

Prereqs (see social-kit/AUTOPOST_SETUP.md):
  * A Facebook app (type: Business) with the "Facebook Login" product.
  * You are an admin of the Page you want to post to.
  * In the app's Facebook Login settings add this exact Redirect URL:
        http://localhost:8000/callback
  * export FB_APP_ID=...  FB_APP_SECRET=...

Posting to your OWN page needs NO App Review — pages_manage_posts is available
with Standard Access to an app admin/developer/tester on their own page.

  pip install requests
  python scripts/get_facebook_token.py
"""
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import requests

VERSION = os.environ.get("FB_API_VERSION") or "v21.0"
GRAPH = f"https://graph.facebook.com/{VERSION}"
REDIRECT = "http://localhost:8000/callback"
# publish page posts + reels, read page list + engagement.
SCOPES = "pages_manage_posts,pages_read_engagement,pages_show_list,business_management"
_code = {}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        _code["code"] = q.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Done. Return to the terminal.")

    def log_message(self, *a):
        pass


def main():
    cid = os.environ.get("FB_APP_ID")
    csecret = os.environ.get("FB_APP_SECRET")
    if not (cid and csecret):
        sys.exit("export FB_APP_ID and FB_APP_SECRET first.")

    auth_url = "https://www.facebook.com/{}/dialog/oauth?".format(VERSION) + urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPES, "state": "csrf123",
    })
    print("Opening browser to authorize...\n", auth_url)
    webbrowser.open(auth_url)
    srv = HTTPServer(("localhost", 8000), _Handler)
    srv.handle_request()  # serves the single callback
    if not _code.get("code"):
        sys.exit("No authorization code received.")

    # 1. code -> short-lived user token
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "client_id": cid, "client_secret": csecret,
        "redirect_uri": REDIRECT, "code": _code["code"],
    }, timeout=30)
    r.raise_for_status()
    short = r.json()["access_token"]

    # 2. short -> long-lived user token (~60 days)
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": cid,
        "client_secret": csecret, "fb_exchange_token": short,
    }, timeout=30)
    r.raise_for_status()
    long_user = r.json()["access_token"]

    # 3. long-lived user token -> per-page tokens (these do NOT expire)
    r = requests.get(f"{GRAPH}/me/accounts", params={
        "fields": "name,id,access_token", "access_token": long_user,
    }, timeout=30)
    r.raise_for_status()
    pages = r.json().get("data", [])
    if not pages:
        sys.exit("No pages found — is this user an admin of a Facebook Page?")

    print("\n=== store as GitHub repo secrets (pick your page) ===")
    for p in pages:
        print(f"\nPage: {p.get('name')}")
        print("  FB_PAGE_ID          =", p.get("id"))
        print("  FB_PAGE_ACCESS_TOKEN =", p.get("access_token"))
    print("\n(These page tokens are long-lived / non-expiring — set once.)")


if __name__ == "__main__":
    main()
