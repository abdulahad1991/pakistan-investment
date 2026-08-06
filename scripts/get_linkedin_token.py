#!/usr/bin/env python3
"""ONE-TIME, LOCAL: mint a LinkedIn org-admin access token + find the org id.

Run on your laptop. A browser opens; log in as a LinkedIn user who is an
ADMINISTRATOR of the company page and approve. It prints:
  * LINKEDIN_ACCESS_TOKEN  (~60-day token — store as a GitHub secret)
  * LINKEDIN_REFRESH_TOKEN (~1-year token, only if the app is approved for
                            programmatic refresh; store it and post_linkedin.py
                            mints a fresh access token every run, so CI stops
                            dying every 60 days — same shape as YT_REFRESH_TOKEN)
  * LINKEDIN_ORG_ID        (numeric id of each page you admin — pick yours)

Prereqs (see social-kit/AUTOPOST_SETUP.md):
  * A LinkedIn Developer app with the **Community Management API** product
    approved, associated + verified with your company page.
  * Add this exact Redirect URL in the app's Auth tab:
        http://localhost:8000/callback
  * export LINKEDIN_CLIENT_ID=...  LINKEDIN_CLIENT_SECRET=...

  pip install requests
  python scripts/get_linkedin_token.py
"""
import datetime
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import requests

REDIRECT = "http://localhost:8000/callback"
SCOPES = "w_organization_social r_organization_social rw_organization_admin"
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
    cid = os.environ.get("LINKEDIN_CLIENT_ID")
    csecret = os.environ.get("LINKEDIN_CLIENT_SECRET")
    if not (cid and csecret):
        sys.exit("export LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET first.")

    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode({
        "response_type": "code", "client_id": cid, "redirect_uri": REDIRECT,
        "state": "csrf123", "scope": SCOPES,
    })
    print("Opening browser to authorize...\n", auth_url)
    webbrowser.open(auth_url)
    srv = HTTPServer(("localhost", 8000), _Handler)
    srv.handle_request()  # serves the single callback
    if not _code.get("code"):
        sys.exit("No authorization code received.")

    tok = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
        "grant_type": "authorization_code", "code": _code["code"],
        "client_id": cid, "client_secret": csecret, "redirect_uri": REDIRECT,
    }, timeout=30)
    tok.raise_for_status()
    body = tok.json()
    access = body["access_token"]
    refresh = body.get("refresh_token")

    print("\n=== store as GitHub repo secrets ===")
    print("LINKEDIN_ACCESS_TOKEN =", access)
    expires = body.get("expires_in")
    if expires:
        dead = datetime.date.today() + datetime.timedelta(seconds=int(expires))
        print(f"  (access token expires {dead:%d %b %Y})")

    if refresh:
        print("\nLINKEDIN_REFRESH_TOKEN =", refresh)
        r_exp = body.get("refresh_token_expires_in")
        if r_exp:
            dead = datetime.date.today() + datetime.timedelta(seconds=int(r_exp))
            print(f"  (refresh token expires {dead:%d %b %Y})")
        print("  Store this one too — post_linkedin.py prefers it and mints a\n"
              "  fresh access token each run, so CI keeps posting unattended.\n"
              "  It also needs LINKEDIN_CLIENT_ID + LINKEDIN_CLIENT_SECRET as secrets.")
    else:
        print("\nNo refresh_token issued — this app isn't approved for programmatic\n"
              "refresh tokens, so the access token above is all you get. Re-run this\n"
              "script roughly every 50 days and update the secret, or request refresh\n"
              "token access from LinkedIn developer support.")

    # Look up which org pages this member administers.
    acl = requests.get(
        "https://api.linkedin.com/rest/organizationAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED",
        headers={"Authorization": f"Bearer {access}", "LinkedIn-Version": "202606",
                 "X-Restli-Protocol-Version": "2.0.0"}, timeout=30)
    print("\nPages you administer (use the numeric id as LINKEDIN_ORG_ID):")
    if acl.status_code == 200:
        for el in acl.json().get("elements", []):
            print("  ", el.get("organizationTarget") or el.get("organization"))
    else:
        print("   (lookup failed", acl.status_code, "- find the id in your page admin URL)")


if __name__ == "__main__":
    main()
