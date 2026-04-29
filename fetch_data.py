#!/usr/bin/env python3
"""
Fetches live financial data and writes data.json.
Run by GitHub Actions daily at 06:00 PKT (01:00 UTC).
"""
import json, re, sys, subprocess
from datetime import datetime, timezone

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

# ── 2. KSE-100 ────────────────────────────────────────────────────
try:
    kse = yf.Ticker("^KSE")
    hist = kse.history(period="5d")
    if not hist.empty:
        level = int(hist["Close"].dropna().iloc[-1])
        data["macro"]["kse100_level"] = level
        today_lbl = datetime.now().strftime("%b'%y")
        if data["kse100_history"]["labels"][-1] != today_lbl:
            data["kse100_history"]["labels"].append(today_lbl)
            data["kse100_history"]["values"].append(level)
        fetched.append(f"KSE-100 = {level:,}")
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
    r = requests.get("https://www.sbp.org.pk/MPC/index.htm", timeout=12, headers=HEADERS)
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
STOCK_TICKERS = {
    "FFC.KA": "FFC", "MCB.KA": "MCB", "HUBC.KA": "HUBC", "UBL.KA": "UBL",
    "HBL.KA": "HBL", "OGDC.KA": "OGDC", "PPL.KA": "PPL",  "MEBL.KA": "MEBL",
    "ENGRO.KA": "ENGRO", "LUCK.KA": "LUCK", "FATIMA.KA": "FATIMA", "PSO.KA": "PSO",
}
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

# ── Write updated data.json ───────────────────────────────────────
data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open("data.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"\n  data.json updated — {len(fetched)} live sources")
for item in fetched:
    print(f"  ✓ {item}")
