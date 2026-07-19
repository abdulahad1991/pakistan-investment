#!/usr/bin/env python3
"""One-shot TikTok SANDBOX dry-run — run this OFF-camera before recording the audit demo.

You run it, do the browser consent once, paste the redirected URL back, and it does the
rest automatically:
  1. opens the TikTok authorize page (Login Kit + the 3 scopes),
  2. you log in as the brand account, Approve, paste the redirected `…/tiktok?code=…` URL,
  3. exchanges the code for a refresh token,
  4. saves all creds to scripts/.tiktok_token.env (gitignored, chmod 600) for the on-camera run,
  5. runs scripts/post_tiktok.py in BOTH modes (inbox draft + direct SELF_ONLY) so you can
     confirm the video actually lands on TikTok before you hit record.

Secret handling: the client SECRET is read from $TIKTOK_CLIENT_SECRET or a hidden prompt —
never hardcoded, never echoed. The refresh token is written only to the gitignored env file.
Still run this off-camera (the saved file + your account activity are yours to keep private).

For the RECORDING afterwards (no browser re-auth needed — the token is already saved):
    source scripts/.tiktok_token.env                 # off-camera, silent
    TIKTOK_MODE=inbox  python scripts/post_tiktok.py  # on-camera
    TIKTOK_MODE=direct python scripts/post_tiktok.py  # on-camera

Needs: pip install requests   (CI has it; install locally if missing)
Run:   python scripts/tiktok_demo.py
"""
import datetime
import getpass
import os
import subprocess
import sys
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_KEY = "sbaw1ypbbw2cb1m9rm"                    # sandbox app key — PUBLIC
REDIRECT_URI = "https://pakinvestlysis.com/tiktok"
SCOPES = "video.publish,video.upload,user.info.basic"
AUTHORIZE = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
ENV_FILE = os.path.join(ROOT, "scripts", ".tiktok_token.env")


def main():
    try:
        import requests
    except ImportError:
        sys.exit("Missing dependency — run:  pip install requests")

    # 0) Today's render + caption must exist (post_tiktok reads them).
    day = datetime.date.today().strftime("%Y-%m-%d")
    short = os.path.join(ROOT, "video", "out", "daily", "short.mp4")
    payload = os.path.join(ROOT, "social-kit", "daily", f"{day}.json")
    if not (os.path.exists(short) and os.path.exists(payload)):
        sys.exit(f"Missing today's render/caption:\n  {short}\n  {payload}\n"
                 f"Build them first:  cd video && npm run daily   then re-run this.")

    secret = os.environ.get("TIKTOK_CLIENT_SECRET") or getpass.getpass(
        "TikTok client SECRET (hidden — paste and press Enter): ").strip()
    if not secret:
        sys.exit("No client secret provided.")

    # 1) Authorize (Login Kit).
    url = AUTHORIZE + "?" + urlencode({
        "client_key": CLIENT_KEY, "scope": SCOPES, "response_type": "code",
        "redirect_uri": REDIRECT_URI, "state": "demo",
    })
    print("\nStep 1 — a TikTok login/consent page is opening in your browser.")
    print("Log in as the BRAND account, approve the scopes, and you'll land on")
    print("pakinvestlysis.com/tiktok.  If nothing opens, paste this URL yourself:\n")
    print("  " + url + "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    pasted = input("Step 2 — paste the FULL redirected URL here (…/tiktok?code=…):\n  ").strip()
    code = pasted
    if "code=" in pasted:
        code = parse_qs(urlparse(pasted).query).get("code", [""])[0]
    code = code.split("*")[0] if "*" in code else code   # TikTok appends a *NN suffix
    if not code:
        sys.exit("Couldn't find ?code= in what you pasted. Re-run and paste the whole URL.")

    # 2) Exchange the code for a refresh token.
    print("\nExchanging the code for a refresh token…")
    r = requests.post(
        TOKEN, headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"client_key": CLIENT_KEY, "client_secret": secret, "code": code,
              "grant_type": "authorization_code", "redirect_uri": REDIRECT_URI},
        timeout=30,
    )
    d = r.json()
    if r.status_code != 200 or "refresh_token" not in d:
        sys.exit(f"Token exchange failed ({r.status_code}): {d}")
    refresh = d["refresh_token"]
    print(f"✓ Refresh token obtained (granted scopes: {d.get('scope')}).")

    # 3) Save creds for the on-camera poster runs (gitignored, owner-only).
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(f"export TIKTOK_CLIENT_KEY='{CLIENT_KEY}'\n")
        f.write(f"export TIKTOK_CLIENT_SECRET='{secret}'\n")
        f.write(f"export TIKTOK_REDIRECT_URI='{REDIRECT_URI}'\n")
        f.write(f"export TIKTOK_REFRESH_TOKEN='{refresh}'\n")
    os.chmod(ENV_FILE, 0o600)
    print(f"✓ Creds saved to {ENV_FILE} (gitignored).")

    # 4) Dry-run BOTH modes now, using the real poster (exactly what you'll record).
    env = dict(os.environ, TIKTOK_CLIENT_KEY=CLIENT_KEY, TIKTOK_CLIENT_SECRET=secret,
               TIKTOK_REDIRECT_URI=REDIRECT_URI, TIKTOK_REFRESH_TOKEN=refresh)
    poster = os.path.join(ROOT, "scripts", "post_tiktok.py")
    results = {}
    for mode in ("inbox", "direct"):
        print(f"\n── dry-run: TIKTOK_MODE={mode} → {'draft (video.upload)' if mode=='inbox' else 'SELF_ONLY post (video.publish)'} ──")
        rc = subprocess.run([sys.executable, poster], env=dict(env, TIKTOK_MODE=mode)).returncode
        results[mode] = rc
        if rc != 0:
            print(f"  ⚠ {mode} exited {rc} — see the error above.")

    print("\n" + "=" * 60)
    ok = all(v == 0 for v in results.values())
    if ok:
        print("✓ Both modes succeeded. Open the brand TikTok account and confirm:")
        print("    • a DRAFT in your inbox   (from video.upload)")
        print("    • a PRIVATE post          (from video.publish, SELF_ONLY in sandbox)")
        print("\nIf both are there, you're ready to RECORD. On camera just do:")
        print("    source scripts/.tiktok_token.env        (off-camera, silent)")
        print("    TIKTOK_MODE=inbox  python scripts/post_tiktok.py")
        print("    TIKTOK_MODE=direct python scripts/post_tiktok.py")
    else:
        print("✗ At least one mode failed — fix the error above, then re-run.")
        print(f"   inbox={results.get('inbox')}  direct={results.get('direct')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
