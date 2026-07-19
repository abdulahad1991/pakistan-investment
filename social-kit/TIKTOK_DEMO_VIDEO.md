# TikTok Production audit — demo video runbook

Goal: one screen recording (mp4/mov, **≤50 MB**, ~2–3 min) that shows the **complete
end-to-end TikTok integration on pakinvestlysis.com**, in the **sandbox** environment,
demonstrating **every product + scope** the app requests. Do this, upload it on the
audit form, submit → Production.

Products/scopes we request (and ONLY these):
- **Login Kit** — `user.info.basic`
- **Content Posting API** — `video.publish` (direct post) + `video.upload` (draft/inbox)

---

## A. Dashboard prep (do first — these cause most rejections)

In developer.tiktok.com → your app (keep it in **Sandbox** for the recording):

1. **Products:** keep ONLY **Login Kit** + **Content Posting API**. **Remove** Share Kit,
   Display API, Data Portability, etc. Any product left selected must be demoed, or the
   review is rejected/delayed.
2. **Scopes:** exactly `user.info.basic`, `video.upload`, `video.publish`. Nothing else.
3. **Redirect URI:** `https://pakinvestlysis.com/tiktok` — must match **exactly**.
4. **Sandbox → Target users:** add the **brand TikTok account** you'll log in as. A
   sandbox app can only call the API for accounts added here — without this the post
   call fails on camera.
5. **Bake the Client Key** into `tiktok.html` (line with `__SET_TIKTOK_CLIENT_KEY__`),
   commit + push so the live page has it (no on-camera "paste key" step). The Client
   Key is public; the Client **Secret** never goes in the page.

Have ready before hitting record:
- Browser logged in to the **brand TikTok account** (the one added as sandbox target user).
- A terminal at the repo root with a **fresh render present**: run `cd video && npm run daily`
  (or just re-render the short) so `video/out/daily/short.mp4` + `social-kit/daily/<today>.json`
  are today's. (Already rendered for 2026-07-19.)
- **Mint the refresh token OFF-camera, then export it** in the shell you'll record:
  ```bash
  export TIKTOK_CLIENT_KEY='...'; export TIKTOK_CLIENT_SECRET='...'
  export TIKTOK_REDIRECT_URI='https://pakinvestlysis.com/tiktok'
  python scripts/get_tiktok_token.py         # prints TIKTOK_REFRESH_TOKEN
  export TIKTOK_REFRESH_TOKEN='<printed value>'
  clear                                      # wipe the exports off the screen
  ```

> ⚠️ **Never record `get_tiktok_token.py` or the `export` lines.** The script prints your
> **client secret** and refresh token; the exports show the secret. Do all of that before
> recording and `clear` the terminal. The poster (`post_tiktok.py`) prints no secrets — safe
> to record. Test the whole thing once as a silent dry run before the real take.

---

## B. The recording (shot list + narration)

Keep the **pakinvestlysis.com** domain visible in the address bar wherever possible.
Record at 1080×~ with QuickTime or macOS **⌘⇧5**. Speak the narration or add captions.

| # | On screen | Say |
|---|---|---|
| 1 | **pakinvestlysis.com** homepage — scroll to the Daily Market Brief video | "This is pakinvestlysis.com, a free educational site. Each market session we auto-generate this Daily Market Brief video." |
| 2 | Go to **pakinvestlysis.com/tiktok** → click **"Connect TikTok account"** | "To post it to our own TikTok, the site starts TikTok Login Kit here." |
| 3 | **TikTok consent screen** — pause 2–3 s so the app name + the three scopes are readable → **Approve** | "TikTok asks the account to approve our scopes: user.info.basic, video.upload and video.publish." |
| 4 | Redirect back to **pakinvestlysis.com/tiktok** → **"✅ Authorized"** panel (granted scopes shown) | "The account is returned to our site, authorized — the refresh token is exchanged and stored server-side." |
| 5 | Terminal (token already exported off-camera): `TIKTOK_MODE=inbox python scripts/post_tiktok.py` → prints `uploaded to inbox … publish_id=…` | "Using the Content Posting API video.upload scope, we send today's brief to the account as a draft." |
| 6 | Terminal: `TIKTOK_MODE=direct python scripts/post_tiktok.py` → prints `published (SELF_ONLY) publish_id=…` | "And the video.publish scope posts it directly — private here in sandbox, public once approved." |
| 7 | Open **TikTok app/web** on the brand account → show the brief in **Drafts/Inbox** and the **SELF_ONLY post** | "Here's the same brief now on TikTok — the draft from video.upload and the private post from video.publish." |

That covers: the **matching domain**, **Login Kit** (2–4), **user.info.basic** (consent),
**video.upload** (5, 7), **video.publish** (6, 7), **Content Posting API** result (7).

Shots 5–6 are terminal because posting is server-side automation — that's fine; the
interactive on-domain UI (2–4) is what reviewers most want to see. The token mint is done
off-camera (it prints secrets) — the "Authorized" panel in shot 4 already proves the auth.

---

## C. Keep it under 50 MB

A 2–3 min 1080p screen recording can exceed 50 MB. If so:
- Export/trim in QuickTime, or
- `ffmpeg -i in.mov -vcodec h264 -crf 28 -acodec aac demo.mp4` (drops it well under 50 MB).

No music needed. One file is enough (form allows up to 5).

---

## D. Submit

Upload the file on the audit form, confirm the scope list matches (Login Kit +
Content Posting API; `user.info.basic`, `video.upload`, `video.publish`), submit for
review. On approval: `gh secret set TIKTOK_MODE --body 'direct'` → daily posts go public
automatically.
