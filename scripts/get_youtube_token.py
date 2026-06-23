#!/usr/bin/env python3
"""ONE-TIME, LOCAL: mint a long-lived YouTube OAuth refresh token.

Run this on your laptop (not in CI). A browser opens; log in as the channel's
Google account and approve. It prints the three values to store as GitHub
secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.

Prereqs (see social-kit/AUTOPOST_SETUP.md):
  * Google Cloud project with "YouTube Data API v3" enabled.
  * OAuth consent screen set to **In production** (NOT Testing — Testing
    revokes the refresh token after 7 days). Verification is NOT required;
    click "Advanced -> Go to <app> (unsafe)" on the warning screen.
  * A "Desktop app" OAuth client; download its JSON as client_secret.json
    into this folder.

  pip install google-auth-oauthlib
  python scripts/get_youtube_token.py
"""
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    secrets = os.path.join(HERE, "client_secret.json")
    if not os.path.exists(secrets):
        sys.exit("Put your Desktop-app OAuth JSON at scripts/client_secret.json first.")
    flow = InstalledAppFlow.from_client_secrets_file(secrets, SCOPES)
    # offline + consent guarantees a refresh_token is returned.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    print("\n=== store these as GitHub repo secrets ===")
    print("YT_CLIENT_ID    =", creds.client_id)
    print("YT_CLIENT_SECRET=", creds.client_secret)
    print("YT_REFRESH_TOKEN=", creds.refresh_token)


if __name__ == "__main__":
    main()
