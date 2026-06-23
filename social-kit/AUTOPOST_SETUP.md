# Auto-posting setup — YouTube + LinkedIn

The daily `update-data.yml` job renders the brief, then runs
`scripts/post_youtube.py` and `scripts/post_linkedin.py`. Both **no-op when
their secrets are missing**, so nothing posts until you complete the setup
below. Posting is `continue-on-error`: a failure never blocks the data/homepage
pipeline.

What posts, twice every weekday (Market open ~09:45 PKT, Market close ~16:30 PKT):
- **YouTube** ← `video/out/daily/short.mp4` (9:16), **public** Short.
- **LinkedIn** ← `video/out/daily/linkedin.mp4` (1:1), to the **company page**.

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

## Secrets summary

| Secret | Platform | Notes |
|---|---|---|
| `YT_CLIENT_ID` / `YT_CLIENT_SECRET` | YouTube | from the Desktop OAuth client |
| `YT_REFRESH_TOKEN` | YouTube | long-lived; set once |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn | ~60-day; re-mint periodically |
| `LINKEDIN_ORG_ID` | LinkedIn | numeric page id; never changes |
| `LINKEDIN_VERSION` | LinkedIn | optional, default `202606` |

Missing any platform's secrets → that platform is simply skipped.
