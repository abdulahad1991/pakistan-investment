# Auto-posting setup — YouTube + LinkedIn + TikTok + Facebook

The daily `update-data.yml` job renders the brief, then runs
`scripts/post_youtube.py`, `scripts/post_linkedin.py`, `scripts/post_tiktok.py`
and `scripts/post_facebook.py`. All **no-op when their secrets are missing**, so
nothing posts until you complete the setup below. Posting is `continue-on-error`:
a failure never blocks the data/homepage pipeline.

What posts, twice every weekday (Market open ~09:45 PKT, Market close ~16:30 PKT):
- **YouTube** ← `video/out/daily/short.mp4` (9:16), **public** Short.
- **LinkedIn** ← `video/out/daily/linkedin.mp4` (1:1), to the **company page**.
- **TikTok** ← `video/out/daily/short.mp4` (9:16), public once the app is audited
  (private/draft before that — see the TikTok section).
- **Facebook** (page) ← **two** posts: a **Reel** (`short.mp4`, 9:16) and a **feed
  data-board post** (`card.png` still + a caption listing petrol/HSD/kerosene/LDO
  + KSE-100/USD/rate/inflation/gold). See the Facebook section.

Caption text comes from `social-kit/daily/<date>.json` (built by `build_daily.py`).

---

## YouTube (one-time, ~15 min — then permanent)

1. **Google Cloud Console** → create/pick a project.
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **OAuth consent screen**: User type **External**; fill app name + emails.
4. **Audience → Publish app → set status to "In production".**
   ⚠️ Leave it in *Testing* and Google **revokes the refresh token after 7 days**
   (CI breaks weekly). Production fixes this. You do **not** need Google
   verification — at the "Google hasn't verified this app" screen during step 6,
   click **Advanced → Go to <app> (unsafe)**.
5. **Credentials → Create credentials → OAuth client ID → Desktop app.**
   Download the JSON to `scripts/client_secret.json`.
6. Locally:
   ```bash
   pip install google-auth-oauthlib
   python scripts/get_youtube_token.py     # browser opens; log in as the channel account
   ```
   It prints `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
7. Add those as **repo secrets** (Settings → Secrets and variables → Actions),
   or:
   ```bash
   gh secret set YT_CLIENT_ID --body '...'
   gh secret set YT_CLIENT_SECRET --body '...'
   gh secret set YT_REFRESH_TOKEN --body '...'
   ```
8. **Verify the channel's phone number** in YouTube Studio — unverified channels
   can have `public` silently downgraded to `unlisted`.

**Maintenance:** none. The refresh token is long-lived (dies only after 6 months
of *no* uploads; twice-daily keeps it alive). `client_secret.json` is local
only — don't commit it.

---

## LinkedIn company page (one-time + ~60-day token refresh)

> Heads-up: LinkedIn access tokens **expire in ~60 days** and refresh tokens are
> gated. Plan to re-run the token grab (step 5) roughly every 50 days. A 401 in
> the LinkedIn step = token lapsed.

1. **developer.linkedin.com → Create app.** Associate it with your **company
   page** (the app's company = that page). You must be a **page admin**.
2. **App → Settings → Verify**: generate the verify URL, have a page admin click
   it (verifies the app on the page).
3. **Products → request "Community Management API".** This needs LinkedIn review
   (Development Tier: days; Standard Tier needs a screencast, 1–3 weeks).
   Development Tier limits (500/app/day) are plenty for 2 posts/day.
4. **Auth tab → add Redirect URL:** `http://localhost:8000/callback`
5. Locally:
   ```bash
   pip install requests
   export LINKEDIN_CLIENT_ID=...        # app Auth tab
   export LINKEDIN_CLIENT_SECRET=...
   python scripts/get_linkedin_token.py # browser opens; log in as a page admin
   ```
   It prints `LINKEDIN_ACCESS_TOKEN` and lists the org URNs you administer.
6. Add **repo secrets**:
   ```bash
   gh secret set LINKEDIN_ACCESS_TOKEN --body '...'
   gh secret set LINKEDIN_ORG_ID --body '12345678'   # numeric id from the org URN
   # optional; defaults to 202606 if unset:
   gh secret set LINKEDIN_VERSION --body '202606'
   ```

**Maintenance:**
- **~every 50 days:** re-run step 5, then `gh secret set LINKEDIN_ACCESS_TOKEN ...`.
- **~once a year:** bump `LINKEDIN_VERSION` before the pinned value is sunset
  (LinkedIn supports each `YYYYMM` for ≥1 year).

---

## TikTok (one-time + ~yearly token refresh)

> ⚠️ **The big difference from YouTube/LinkedIn:** TikTok will **not let an
> unaudited app post publicly**. Until TikTok audits your app, a "direct" post
> can only be **private (SELF_ONLY)**, or you push it to your **drafts inbox** to
> publish by hand. To get fully-automatic **public** posting you must submit the
> app for audit (below). The poster handles both states automatically.

1. **developer.tiktok.com → Manage apps → Connect an app.** Create the app.
2. **Add product → "Content Posting API".** (Also add **Login Kit** for OAuth.)
3. **Request scopes:** `video.publish` (public direct post) **and** `video.upload`
   (drafts). `user.info.basic` is added automatically.
4. **Add a Redirect URI** under Login Kit — TikTok requires **https** and a
   registered domain (localhost is rejected). Use a URL on your own site, e.g.
   `https://pakinvestlysis.com/tiktok`. The page doesn't need to do anything —
   the token script just reads the `?code=` TikTok appends to it.
5. **Mint the refresh token locally:**
   ```bash
   pip install requests
   export TIKTOK_CLIENT_KEY=...        # app "Client key"
   export TIKTOK_CLIENT_SECRET=...     # app "Client secret"
   export TIKTOK_REDIRECT_URI=https://pakinvestlysis.com/tiktok   # EXACTLY as registered
   python scripts/get_tiktok_token.py
   ```
   Open the printed URL, log in **as the posting account**, approve, then paste
   the redirected URL back. It prints `TIKTOK_REFRESH_TOKEN` (valid ~365 days).
6. **Add repo secrets:**
   ```bash
   gh secret set TIKTOK_CLIENT_KEY --body '...'
   gh secret set TIKTOK_CLIENT_SECRET --body '...'
   gh secret set TIKTOK_REFRESH_TOKEN --body '...'
   # until the app is audited, push to drafts instead of posting privately:
   gh secret set TIKTOK_MODE --body 'inbox'      # switch to 'direct' (or unset) after audit
   ```
7. **Go public (after testing):** in the app dashboard, **submit for review /
   audit** of the Content Posting API. Once approved, `PUBLIC_TO_EVERYONE`
   becomes available — set `TIKTOK_MODE=direct` (or delete the secret; direct is
   the default) and posts go out publicly with no further changes.

**Maintenance:**
- **~once a year:** re-run step 5 and `gh secret set TIKTOK_REFRESH_TOKEN ...`
  (refresh token lasts ~365 days; daily posting does not auto-extend it).
- A 401/expired-token error in the TikTok step = re-mint the refresh token.

**Modes at a glance:**
| `TIKTOK_MODE` | App audited? | Result |
|---|---|---|
| `inbox` | not needed | Lands in your TikTok **drafts** — tap publish in the app |
| `direct` (default) | **no** | Posts **privately** (SELF_ONLY) + warns |
| `direct` (default) | **yes** | Posts **publicly**, fully automatic |

---

## Facebook page (one-time — then permanent)

> The nicest of the four: a Page token minted from a long-lived user token
> **does not expire** (it lives as long as you stay a page admin) — set it once,
> no periodic refresh chore. And posting to **your own** page needs **no App
> Review**.

Two posts go out per run: a **Reel** (the 9:16 Short) and a **feed data-board
post** (the DailyCard still + a caption listing petrol, HSD, kerosene, LDO,
KSE-100, USD/PKR, policy rate, inflation and gold).

1. **Have a Facebook Page** (a business Page, not a personal profile). You must
   be a Page **admin**.
2. **developers.facebook.com → My Apps → Create app → type "Business".** Add the
   **Facebook Login** product.
3. **App → Settings → Basic:** copy the **App ID** and **App Secret**.
4. **Facebook Login → Settings → Valid OAuth Redirect URIs:** add
   `http://localhost:8000/callback` (localhost is accepted while the app is in
   Development mode).
5. Locally:
   ```bash
   pip install requests
   export FB_APP_ID=...        # Settings → Basic → App ID
   export FB_APP_SECRET=...    # Settings → Basic → App Secret
   python scripts/get_facebook_token.py   # browser opens; log in as a page admin
   ```
   It prints, for each page you admin, its **FB_PAGE_ID** and a long-lived
   **FB_PAGE_ACCESS_TOKEN**.
6. Add **repo secrets**:
   ```bash
   gh secret set FB_PAGE_ID --body '1234567890'
   gh secret set FB_PAGE_ACCESS_TOKEN --body '...'
   # optional; both|reel|feed, defaults to posting both:
   gh secret set FB_MODE --body 'both'
   ```

**Why no App Review:** `pages_manage_posts`, `pages_read_engagement` and
`pages_show_list` are available with **Standard Access** to an app
admin/developer/tester acting on a page they administer. App Review is only
needed to act on pages where you are not a role on the app.

**Maintenance:** essentially none — the page token does not expire. If you change
your Facebook password, remove the app, or lose admin on the page, re-run step 5
and update `FB_PAGE_ACCESS_TOKEN`. A `190 / OAuthException` in the Facebook step
= re-mint the token.

---

## Secrets summary

| Secret | Platform | Notes |
|---|---|---|
| `YT_CLIENT_ID` / `YT_CLIENT_SECRET` | YouTube | from the Desktop OAuth client |
| `YT_REFRESH_TOKEN` | YouTube | long-lived; set once |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn | ~60-day; re-mint periodically |
| `LINKEDIN_ORG_ID` | LinkedIn | numeric page id; never changes |
| `LINKEDIN_VERSION` | LinkedIn | optional, default `202606` |
| `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` | TikTok | from the TikTok app |
| `TIKTOK_REFRESH_TOKEN` | TikTok | ~365-day; re-mint yearly |
| `TIKTOK_MODE` | TikTok | optional: `inbox` (drafts) or `direct` (default) |
| `TIKTOK_PRIVACY` | TikTok | optional, default `PUBLIC_TO_EVERYONE` |
| `FB_PAGE_ID` | Facebook | numeric page id; never changes |
| `FB_PAGE_ACCESS_TOKEN` | Facebook | long-lived / non-expiring; set once |
| `FB_MODE` | Facebook | optional: `both` (default), `reel`, or `feed` |
| `FB_API_VERSION` | Facebook | optional, default `v21.0` |

Missing any platform's secrets → that platform is simply skipped.
