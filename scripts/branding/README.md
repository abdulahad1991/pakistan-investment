# Branding / OG generators

One-off scripts to regenerate brand assets and OG share banners after a logo,
favicon, or brand-name change. Not run in CI. Require Pillow + Poppins TTFs.

## Setup
```
python3 -m venv /tmp/pilvenv && /tmp/pilvenv/bin/pip install Pillow
```
Poppins TTF path is hard-coded at the top of each script (FDIR) — adjust if needed.

## gen_brand_assets.py
From `assets/logo.png` (header) + `assets/favicon.png` (source), writes:
- `assets/logo-light.png` (teal→white recolour, keeps gold/lime accent — for dark footer)
- `assets/favicon-16/32/192/512.png`, `assets/apple-touch-icon.png`, root `favicon.ico`
After running, also fix the header `<img>` intrinsic dims site-wide to match the
new logo aspect (e.g. `width="239" height="40"`), via a perl sweep over `*.html`.

## gen_og_banners.py
Regenerates every `assets/og/*.png` (1200×630) in brand: lime accent bar, white
pakInvestlysis wordmark, per-page title pulled from each page's `og:title`.
Add new pages to the `slug2` loop at the bottom. After regenerating, bump the
`?v=N` query on `og:image`/`twitter:image` site-wide so social caches refetch.
