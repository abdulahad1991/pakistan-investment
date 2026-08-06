#!/usr/bin/env bash
# Record the screencast LinkedIn asks for on the Community Management API
# Standard Tier access form ("a screen recording of your application
# showcasing the Community Management API integration").
#
# It records a REAL run against the real Page -- read use cases first
# (demo_linkedin_api.py), then the write path (post_linkedin.py), then the
# published post opened in the browser. Nothing here is staged or mocked;
# the post the reviewer sees in the video is the post that exists on the Page.
#
# Prereqs
#   1. LINKEDIN_ACCESS_TOKEN + LINKEDIN_ORG_ID exported in this shell
#      (mint the token with: python scripts/get_linkedin_token.py)
#   2. Today's caption payload + 1:1 render (this script builds both if absent)
#   3. A way to capture the screen -- either of:
#      a. --no-capture, and you start the recording yourself with Cmd+Shift+5
#         (recommended: no TCC permission needed, and you can frame a window)
#      b. the default, which shells out to `screencapture -v`. That needs
#         Screen Recording permission for the app HOSTING this shell -- VS Code,
#         iTerm, Ghostty, Terminal, whichever. macOS only lists an app under
#         System Settings -> Privacy & Security -> Screen & System Audio
#         Recording once it has asked, so if yours isn't listed, run this once
#         to trigger the prompt, approve, then restart that app and re-run.
#
# Usage: ./scripts/record_linkedin_demo.sh [--no-capture]
# Output: video/out/linkedin-api-demo.mov  (upload unlisted to YouTube,
#         paste that URL into the form's screen-recording field).
#         With --no-capture the output is wherever your recorder saves it.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$(command -v python3 || command -v python)"   # CI has `python`, macOS has `python3`
OUT="$ROOT/video/out/linkedin-api-demo.mov"
CAPTURE=1
[ "${1:-}" = "--no-capture" ] && CAPTURE=0
TODAY="$(date +%Y-%m-%d)"
PAYLOAD="$ROOT/social-kit/daily/$TODAY.json"
RENDER="$ROOT/video/out/daily/linkedin.mp4"

say() { printf '\n\033[1;34m>> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- preflight
say "Preflight (not recorded)"
[ -n "$PY" ] || die "no python3/python on PATH"
[ -n "${LINKEDIN_ACCESS_TOKEN:-}" ] || die "LINKEDIN_ACCESS_TOKEN not exported. Run: $PY scripts/get_linkedin_token.py"
[ -n "${LINKEDIN_ORG_ID:-}" ] || die "LINKEDIN_ORG_ID not exported (numeric Page id)."

# build_daily.py writes BOTH social-kit/daily/<date>.json and the
# video/daily-props.json that the Remotion compositions render from, so it has
# to run before the render even when only the render is missing.
if [ ! -f "$PAYLOAD" ] || [ ! -f "$RENDER" ]; then
  say "Building today's props + caption"
  "$PY" scripts/build_daily.py || die "build_daily.py failed"
fi
[ -f "$PAYLOAD" ] || die "still no $PAYLOAD"

if [ ! -f "$RENDER" ]; then
  say "No 1:1 render -- rendering DailyBrief-1x1 (takes a few minutes)"
  ( cd video && npx remotion render DailyBrief-1x1 --props=daily-props.json out/daily/linkedin.mp4 ) \
    || die "remotion render failed"
fi
[ -f "$RENDER" ] || die "still no $RENDER"

mkdir -p "$(dirname "$OUT")"

if [ "$CAPTURE" = 1 ]; then
  rm -f "$OUT"
  cat <<'EOF'

  Ready. When you press Enter:
    - screen recording starts (whole display)
    - the read use cases run, then the live post is published
    - the published post opens in your browser
    - recording stops automatically

  Put this terminal window where it is readable and close anything private
  on screen -- the whole display is captured.

EOF
else
  cat <<'EOF'

  --no-capture: this script will NOT record. Start the recording yourself:

    1. Press Cmd+Shift+5, choose "Record Entire Screen" (or Record Selected
       Portion and frame this terminal), click Record.
    2. Come back here and press Enter.
    3. When the demo finishes, stop the recording from the menu bar.

  Close anything private that is on screen first.

EOF
fi
read -r -p "  Press Enter to start... " _

# ---------------------------------------------------------------- record
if [ "$CAPTURE" = 1 ]; then
  screencapture -v "$OUT" &
  REC_PID=$!
  trap 'kill -INT "$REC_PID" 2>/dev/null' EXIT
  sleep 3
  # screencapture dies immediately if Screen Recording permission is missing.
  if ! kill -0 "$REC_PID" 2>/dev/null; then
    trap - EXIT
    die "screencapture exited -- the app hosting this shell (${TERM_PROGRAM:-unknown}) lacks Screen Recording permission. Approve it in System Settings -> Privacy & Security -> Screen & System Audio Recording, restart that app, and re-run. Or re-run with --no-capture and record via Cmd+Shift+5."
  fi
fi

clear
cat <<EOF
================================================================
  pakinvestlysis.com - LinkedIn Community Management API
  Screencast for Standard Tier access review
  Organization: urn:li:organization:${LINKEDIN_ORG_ID##*:}
  Date: $TODAY
================================================================

  What this integration does:
  A scheduled GitHub Actions job runs twice each weekday, renders a
  1:1 "Pakistan Daily Market Brief" video from that day's published
  data, and publishes it to our own LinkedIn Page via the Videos API
  followed by the Posts API. No end users authenticate; we access
  only the organization we administer.

EOF
sleep 6

say "PART 1 - Page management reads (admin role, Page, existing posts)"
sleep 2
"$PY" scripts/demo_linkedin_api.py
sleep 4

say "PART 2 - The content we are about to publish"
"$PY" -c "import json;print(json.load(open('$PAYLOAD'))['linkedin']['text'])"
echo
ls -lh "$RENDER"
sleep 5
say "Playing the 1:1 render that gets uploaded"
open "$RENDER"
sleep 12

say "PART 3 - Write path: Videos API upload -> Posts API publish"
sleep 2
POST_LOG="$(mktemp)"
"$PY" scripts/post_linkedin.py 2>&1 | tee "$POST_LOG"
POST_URL="$(grep -o 'https://www.linkedin.com/feed/update/[^ ]*' "$POST_LOG" | tail -1)"

if [ -n "$POST_URL" ]; then
  say "PART 4 - The post is live on the Page: $POST_URL"
  sleep 3
  open "$POST_URL"
  sleep 15
else
  say "No post URL in output -- see the error above. Recording anyway."
  sleep 8
fi

say "Demo complete."
sleep 3

if [ "$CAPTURE" = 1 ]; then
  kill -INT "$REC_PID" 2>/dev/null
  trap - EXIT
  wait "$REC_PID" 2>/dev/null
  echo
  echo "  Recording saved: $OUT"
else
  echo
  echo "  Stop your recording now (menu bar stop button, or Cmd+Ctrl+Esc)."
fi

echo "  Next: upload it to YouTube as UNLISTED, paste the URL into the"
echo "        form's 'link to your screen recording' field."
[ -n "$POST_URL" ] && echo "  Live post: $POST_URL"
