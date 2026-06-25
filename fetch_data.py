#!/usr/bin/env python3
"""
Fetches live financial data and writes data.json.
Run by GitHub Actions daily at 06:00 PKT (01:00 UTC).
"""
import json, re, sys, subprocess
from datetime import datetime, timezone
from pathlib import Path

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg,
                           "--quiet", "--break-system-packages"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for pkg in ["yfinance", "pandas", "requests", "beautifulsoup4"]:
    try: __import__(pkg.replace("-",""))
    except ImportError: install(pkg)

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}

# ── Load existing data.json as fallback ───────────────────────────
with open("data.json", "r") as f:
    data = json.load(f)

fetched = []

# ── 1. PKR / USD ──────────────────────────────────────────────────
try:
    fx = yf.Ticker("PKR=X")
    hist = fx.history(period="5d")
    if not hist.empty:
        rate = round(float(hist["Close"].dropna().iloc[-1]), 1)
        data["macro"]["pkr_usd"] = rate
        fetched.append(f"PKR/USD = {rate}")
except Exception as e:
    print(f"  PKR/USD failed: {e}")

# ── 2. KSE-100 (scraped from PSX website) ─────────────────────────
try:
    r = requests.get("https://www.psx.com.pk/market-summary/", timeout=20, headers=HEADERS)
    if r.status_code == 200:
        lines = [l.strip() for l in BeautifulSoup(r.text, "html.parser")
                 .get_text(separator="\n").splitlines() if l.strip()]
        for i, line in enumerate(lines):
            if "KSE-100" in line or "KSE100" in line:
                window = " ".join(lines[i:i+6])
                m = re.search(r"([\d,]{6,}(?:\.\d+)?)", window)
                if m:
                    level = int(float(m.group(1).replace(",", "")))
                    if level > 50000:
                        data["macro"]["kse100_level"] = level
                        today_lbl = datetime.now().strftime("%b'%y")
                        if data["kse100_history"]["labels"][-1] != today_lbl:
                            data["kse100_history"]["labels"].append(today_lbl)
                            data["kse100_history"]["values"].append(level)
                        fetched.append(f"KSE-100 = {level:,}")
                        break
except Exception as e:
    print(f"  KSE-100 failed: {e}")

# ── 3. CDNS Rates ─────────────────────────────────────────────────
CDNS_MAP = {
    "special savings":  "Special Savings Certificate",
    "regular income":   "Regular Income Certificate",
    "behbood":          "Behbood Savings Certificate",
    "defence savings":  "Defence Savings Certificate",
    "savings account":  "CDNS Savings Account",
}
CDNS_URLS = [
    "https://www.savings.gov.pk/profit-rates/",
    "http://www.savings.gov.pk/profit-rates/",
    "https://savings.gov.pk/profit-rates/",
]

def _parse_cdns(html):
    soup = BeautifulSoup(html, "html.parser")
    lines = [l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()]
    found = {}
    for i, line in enumerate(lines):
        ll = line.lower()
        for kw, scheme in CDNS_MAP.items():
            if kw in ll:
                window = " ".join(lines[i: i + 6])
                m = re.search(r"(\d{1,2}\.\d{1,2})\s*%?", window)
                if m:
                    val = float(m.group(1))
                    if 5.0 <= val <= 25.0:
                        found[scheme] = val
                break
    return found

cdns_html = None
for _url in CDNS_URLS:
    try:
        r = requests.get(_url, timeout=20, headers=HEADERS)
        if r.status_code == 200:
            cdns_html = r.text
            break
    except Exception:
        pass

if cdns_html:
    try:
        rates = _parse_cdns(cdns_html)
        for s in data["national_savings"]:
            if s["name"] in rates:
                s["rate"] = rates[s["name"]]
                fetched.append(f"CDNS {s['name'][:20]} = {rates[s['name']]}%")
        if not rates:
            print("  CDNS scrape: page loaded but no rates matched")
    except Exception as e:
        print(f"  CDNS parse failed: {e}")
else:
    print("  CDNS scrape failed: all URLs unreachable")

# ── 4. SBP Policy Rate ────────────────────────────────────────────
try:
    r = requests.get("https://www.sbp.org.pk/m_policy/index.asp", timeout=20, headers=HEADERS)
    if r.status_code == 200:
        text = BeautifulSoup(r.text, "html.parser").get_text()
        for pat in [
            r"policy rate[^\d]{0,20}(\d{1,2}\.?\d*)\s*(?:percent|%)",
            r"(\d{1,2}\.?\d*)\s*(?:percent|%)\s*per annum",
        ]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                if 5.0 <= val <= 25.0:
                    data["macro"]["sbp_rate"] = val
                    today_lbl = datetime.now().strftime("%b'%y")
                    if data["sbp_history"]["labels"][-1] != today_lbl:
                        data["sbp_history"]["labels"].append(today_lbl)
                        data["sbp_history"]["values"].append(val)
                    fetched.append(f"SBP Rate = {val}%")
                    break
except Exception as e:
    print(f"  SBP rate failed: {e}")

# ── 5. Live stock prices ──────────────────────────────────────────
# Universe lives in scripts/psx_universe.json so adding a stock is a one-file
# edit. ensure_seeds() auto-seeds any missing ticker at zero (so the loop below
# can fill it) and normalises sector/name; graceful fallback keeps last good value.
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from stock_universe import ensure_seeds
STOCK_TICKERS = ensure_seeds(data)   # yahoo -> short; mutates data["stocks"]
live_count = 0
for yahoo_ticker, short in STOCK_TICKERS.items():
    try:
        stk  = yf.Ticker(yahoo_ticker)
        hist = stk.history(period="2y")
        if hist.empty or len(hist) < 30:
            continue
        cp   = round(float(hist["Close"].dropna().iloc[-1]), 2)
        p1y  = float(hist["Close"].dropna().iloc[-252]) if len(hist) > 252 else float(hist["Close"].dropna().iloc[0])
        chg  = round(((cp - p1y) / p1y) * 100, 1) if p1y else 0
        hi52 = round(float(hist["High"].tail(252).max()), 2)
        lo52 = round(float(hist["Low"].tail(252).min()), 2)
        divs = stk.dividends
        ann_d = 0
        if not divs.empty:
            cutoff = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1)
            ann_d  = round(float(divs[divs.index >= cutoff].sum()), 2)
        dy = round((ann_d / cp) * 100, 2) if cp else 0
        try:    pe = round(float(stk.info.get("trailingPE") or 0), 1)
        except: pe = 0
        for s in data["stocks"]:
            if s["ticker"] == short:
                s.update({"price": cp, "chg1y": chg, "hi52": hi52, "lo52": lo52,
                           "div": ann_d, "yield": dy, "pe": pe})
                live_count += 1
                break
    except Exception:
        pass
if live_count:
    fetched.append(f"Stocks live: {live_count}/{len(STOCK_TICKERS)}")

# ── 6. Mutual fund returns (finhisaab — server-rendered, requests-scrapable) ──
# Each fund page renders rows like "<N> Year(s) <cumulative>% <annualized>%";
# we take the ANNUALIZED (second) figure. Falls back to existing data.json
# values if a page is unreachable or its structure changes.
FUND_SLUGS = {
    "Meezan Islamic Income Fund": "meezan-islamic-income-fund",
    "Al Meezan Mutual Fund":      "al-meezan-mutual-fund",
    "NBP Savings Fund":           "nbp-savings-fund",
    "NBP Islamic Stock Fund":     "nbp-islamic-stock-fund",
    "JS Islamic Fund":            "js-islamic-fund",
}

def _fund_return(text, years):
    m = re.search(r"(?<!\d)" + str(years) + r" Years?\s+[+-]?[\d.]+%\s+([+-]?[\d.]+)%", text)
    if not m:
        return None
    val = round(float(m.group(1)), 1)
    return val if -95.0 <= val <= 500.0 else None

fund_count = 0
for fund in data["mutual_funds"]:
    slug = FUND_SLUGS.get(fund["name"])
    if not slug:
        continue
    try:
        r = requests.get(f"https://finhisaab.com/mutual-funds/{slug}", timeout=20, headers=HEADERS)
        if r.status_code != 200:
            continue
        text = re.sub(r"\s+", " ", BeautifulSoup(r.text, "html.parser").get_text(separator=" "))
        y1 = _fund_return(text, 1)
        if y1 is None:
            continue  # structure changed — keep existing values
        fund["ret_1y"] = y1
        y3 = _fund_return(text, 3)
        y5 = _fund_return(text, 5)
        if y3 is not None:
            fund["ret_3y"] = y3
        if y5 is not None:
            fund["ret_5y"] = y5
        fund_count += 1
    except Exception:
        pass
if fund_count:
    fetched.append(f"Mutual fund returns: {fund_count}/{len(FUND_SLUGS)}")

# ── 7. Gold (local gold.pk scrape → international yfinance fallback) ──
# Pakistani gold is quoted per tola (11.6638 g). We prefer the local
# Sarafa-style rate (which carries the local premium/duty buyers actually
# pay) and fall back to the international spot derived from gold futures
# (GC=F, USD/oz, 24K) converted at the live PKR/USD when the scrape fails.
TOLA_G = 11.6638  # grams per tola

def _to_int(s):
    try:
        v = int(str(s).replace(",", ""))
        return v if 100000 <= v <= 2000000 else None  # sanity band for PKR/tola
    except Exception:
        return None

def _scrape_local_gold():
    """gold.pk is server-rendered — returns (tola_24k, tola_22k) or None."""
    try:
        r = requests.get("https://gold.pk/", timeout=20, headers=HEADERS)
        if r.status_code != 200:
            return None
        txt = re.sub(r"\s+", " ", BeautifulSoup(r.text, "html.parser").get_text(" "))
        # 24K per tola — prefer the table form ("Rs. 445500.00 24 Karat Gold Rate (1 Tola)"),
        # fall back to the prose ("for 24 karat is Rs. 445500").
        m24 = (re.search(r"Rs\.?\s*([\d,]+)(?:\.\d+)?\s*24 Karat Gold Rate \(1 ?Tola\)", txt)
               or re.search(r"for 24 karat is Rs\.?\s*([\d,]+)", txt, re.I))
        m22 = (re.search(r"22 [Kk]arat Gold price for today is Rs\.?\s*([\d,]+)", txt)
               or re.search(r"Rs\.?\s*([\d,]+)(?:\.\d+)?\s*22 Karat Gold Rate \(1 ?Tola\)", txt))
        t24 = _to_int(m24.group(1)) if m24 else None
        t22 = _to_int(m22.group(1)) if m22 else None
        if t24:
            return (t24, t22)
    except Exception as e:
        print(f"  Gold local scrape failed: {e}")
    return None

def _intl_gold_tola_24k():
    """International spot via GC=F (USD/oz, 24K) × live PKR/USD → PKR/tola."""
    try:
        oz = yf.Ticker("GC=F").history(period="5d")["Close"].dropna()
        if oz.empty:
            return None
        usd_oz = float(oz.iloc[-1])
        return round(usd_oz / 31.1035 * data["macro"]["pkr_usd"] * TOLA_G)
    except Exception as e:
        print(f"  Gold intl spot failed: {e}")
    return None

def _build_gold_history():
    """Real PKR/tola 24K monthly history from GC=F × PKR=X (last ~6 years)."""
    try:
        oz = yf.Ticker("GC=F").history(period="6y", interval="1mo")["Close"].dropna()
        if oz.empty:
            return None
        fx = yf.Ticker("PKR=X").history(period="6y", interval="1mo")["Close"].dropna()
        labels, values = [], []
        for ts, usd_oz in oz.items():
            if not fx.empty:
                prior = fx[fx.index <= ts]
                rate = float(prior.iloc[-1]) if len(prior) else float(fx.iloc[0])
            else:
                rate = data["macro"]["pkr_usd"]
            tola = round(float(usd_oz) / 31.1035 * rate * TOLA_G)
            if 50000 <= tola <= 2000000:
                labels.append(ts.strftime("%b'%y"))
                values.append(tola)
        return {"labels": labels, "values": values} if len(values) >= 6 else None
    except Exception as e:
        print(f"  Gold history failed: {e}")
    return None

gold = data.setdefault("gold", {})
local = _scrape_local_gold()
if local and local[0]:
    t24, t22 = local
    if not t22:
        t22 = round(t24 * 22 / 24)
    gold.update({"tola_24k": t24, "tola_22k": t22, "source": "gold.pk",
                 "source_type": "local"})
    fetched.append(f"Gold local: 24K tola = {t24:,}")
else:
    t24 = _intl_gold_tola_24k()
    if t24:
        gold.update({"tola_24k": t24, "tola_22k": round(t24 * 22 / 24),
                     "source": "International spot (GC=F × PKR/USD)",
                     "source_type": "international"})
        fetched.append(f"Gold intl: 24K tola = {t24:,}")

# Derived units (computed so per-tola, per-10g and per-gram always agree)
if gold.get("tola_24k"):
    t24 = gold["tola_24k"]; t22 = gold["tola_22k"]
    gold["gram_24k"] = round(t24 / TOLA_G)
    gold["gram_22k"] = round(t22 / TOLA_G)
    gold["g10_24k"]  = round(t24 / TOLA_G * 10)
    gold["g10_22k"]  = round(t22 / TOLA_G * 10)

# History (rebuilt from real data each run; keep prior on failure)
hist = _build_gold_history()
if hist:
    gold["history"] = hist
    fetched.append(f"Gold history: {len(hist['values'])} months")

# 1-year change from monthly history (-13 = 12 months back)
hv = gold.get("history", {}).get("values", [])
if len(hv) >= 13 and hv[-13]:
    gold["chg1y_pct"] = round((hv[-1] - hv[-13]) / hv[-13] * 100, 1)

# ── Write updated data.json ───────────────────────────────────────
data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open("data.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"\n  data.json updated — {len(fetched)} live sources")
for item in fetched:
    print(f"  ✓ {item}")
