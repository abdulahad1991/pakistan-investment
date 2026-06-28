"""PSX dividend-payout fetcher — cash dividends per share for a symbol.

The PSX Data Portal payouts table (https://dps.psx.com.pk/company/payouts,
served per-symbol) lists every corporate action in reverse-chronological order:

    Date (announce) | Financial Results (period) | Details | Book Closure

``Details`` look like '32.50%(iii) (D)' where the trailing parenthetical marks
the action type — (D) cash **D**ividend, (B) **B**onus shares, (R) **R**ights.
We KEEP ONLY (D) cash rows. A dividend is quoted as a percentage of *par*, so

    cash_per_share = pct/100 * FACE_VALUE

Default par is Rs 10. A few issuers subdivided their shares: ``PAR_OVERRIDE``
fixes those (e.g. Lucky Cement is Rs 2 par, so a 200% payout is Rs 4, not Rs 20).

Pure stdlib + re. ``parse_payouts`` takes a string and returns values — no
network, no import-time side effects — so the unit tests run on the fixture
with zero third-party deps.
"""
import re
import time
import html as _html
import datetime

from .base import http_get, partition, run, in_band

NAME = "dividends"

# Payouts are AJAX-loaded — a plain GET of the company page shows "No record
# found". The data only comes from a POST to /company/payouts with the symbol
# in the body and an XHR header (this is exactly how the fixture was captured).
PAYOUTS_URL = "https://dps.psx.com.pk/company/payouts"
COMPANY_REFERER = "https://dps.psx.com.pk/company/{sym}"
SOURCE = "Pakistan Stock Exchange (PSX Data Portal) — company/payouts"
CADENCE = "daily"

# A dividend is quoted as a % of par/face value. Default par is Rs 10.
DEFAULT_FACE = 10
# Issuers that subdivided their shares away from Rs 10 par. Verified necessary:
# Lucky Cement (LUCK) is Rs 2 par => 200% = Rs 4, NOT Rs 20.
PAR_OVERRIDE = {"LUCK": 2}

# ---------------------------------------------------------------------------
# Pure parser (what the test calls)
# ---------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
# Leading percentage in the Details cell, e.g. '32.50%' or '200%'.
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
# Action-type marker — the (D)/(B)/(R) single-letter parenthetical(s).
_TYPE = re.compile(r"\(\s*([DBR])\s*\)")
# Announce date prefix, e.g. 'April 29, 2026' (time, if any, is dropped).
_DATE = re.compile(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})")


def _text(fragment):
    """Visible text of an HTML fragment: strip tags, unescape, collapse space."""
    return _WS.sub(" ", _html.unescape(_TAG.sub("", fragment))).strip()


def _announce_date(s):
    """Parse the day-level date out of an announce string; None if absent."""
    m = _DATE.search(s)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(
            f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date()
    except ValueError:
        return None


def face_value(symbol):
    """Par/face value for a symbol — Rs 10 unless overridden."""
    return PAR_OVERRIDE.get((symbol or "").strip().upper(), DEFAULT_FACE)


def parse_payouts(html, symbol):
    """Parse the PSX payouts table for ``symbol``, keeping only (D) cash rows.

    Returns::

        {latest_cash, latest_pct, period, announce, book_closure,
         ttm_cash, symbol, face_value}

    ``latest_*`` describe the most recent cash-dividend row; ``ttm_cash`` is the
    sum of cash-dividend rows announced in the trailing ~12 months (anchored on
    the most recent row's announce date). Money is PKR per share.
    """
    face = face_value(symbol)
    rows = []
    for rowhtml in _ROW.findall(html):
        cells = _CELL.findall(rowhtml)
        if len(cells) < 4:
            continue  # header (<th>) and malformed rows
        announce, period, details, book = (_text(c) for c in cells[:4])
        if "D" not in _TYPE.findall(details):
            continue  # keep ONLY cash dividend rows (skip bonus/rights)
        mpct = _PCT.search(details)
        if not mpct:
            continue
        pct = float(mpct.group(1))
        rows.append({
            "announce": announce,
            "period": period,
            "book_closure": book,
            "pct": pct,
            "cash": round(pct / 100.0 * face, 4),
            "date": _announce_date(announce),
        })

    if not rows:
        return {
            "latest_cash": None, "latest_pct": None, "period": None,
            "announce": None, "book_closure": None, "ttm_cash": 0.0,
            "symbol": (symbol or "").strip().upper(), "face_value": face,
        }

    dated = [r for r in rows if r["date"] is not None]
    latest = max(dated, key=lambda r: r["date"]) if dated else rows[0]

    # Trailing ~12 months, anchored on the most recent announce date.
    if latest["date"] is not None:
        anchor = latest["date"]
        try:
            cutoff = anchor.replace(year=anchor.year - 1)
        except ValueError:  # Feb 29 anchor
            cutoff = anchor.replace(year=anchor.year - 1, day=28)
        ttm = round(sum(r["cash"] for r in dated if r["date"] >= cutoff), 4)
    else:
        ttm = round(sum(r["cash"] for r in rows), 4)

    return {
        "latest_cash": latest["cash"],
        "latest_pct": latest["pct"],
        "period": latest["period"],
        "announce": latest["announce"],
        "book_closure": latest["book_closure"],
        "ttm_cash": ttm,
        "symbol": (symbol or "").strip().upper(),
        "face_value": face,
    }


# ---------------------------------------------------------------------------
# Network fetch (CI only)
# ---------------------------------------------------------------------------

def _post_payouts(symbol):
    """POST the payouts XHR for one symbol and return its raw HTML table."""
    return http_get(
        PAYOUTS_URL,
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": COMPANY_REFERER.format(sym=symbol),
        },
        data=f"symbol={symbol}",
    )


def fetch_one(symbol):
    """Payout dict for a single symbol (latest_cash, ttm_cash, ...) or None."""
    data = parse_payouts(_post_payouts(symbol), symbol)
    return data if data.get("latest_cash") is not None else None


def fetch(symbols=None, throttle=0.3):
    """Fetch cash-dividend payouts for a list of symbols.

    Returns a partition whose value is ``{SYMBOL: payout_dict}`` for every
    symbol that has at least one cash dividend on record. Per-symbol failures
    are skipped (graceful), so one bad symbol never sinks the whole run. The
    throttle keeps us polite over the ~117-name universe.

    ``symbols`` defaults to the headline names; the orchestrator passes the
    full displayed universe (the tickers in data.json).
    """
    if symbols is None:
        symbols = ["OGDC", "HBL", "MEBL", "LUCK", "ENGROH", "PSO", "FFC", "MARI"]
    out = {}
    latest_date = None
    for i, sym in enumerate(symbols):
        sym = (sym or "").strip().upper()
        if sym:
            try:
                data = parse_payouts(_post_payouts(sym), sym)
                # Skip non-payers/empty tables — store nothing rather than a 0.
                if data.get("latest_cash") is not None:
                    out[sym] = data
                    d = _announce_date(data.get("announce") or "")
                    if d and (latest_date is None or d > latest_date):
                        latest_date = d
            except Exception:  # noqa: BLE001 - one symbol must not sink the run
                pass
        # Throttle on EVERY iteration — a skipped/failed symbol still spent a
        # request, so the delay must apply regardless of the outcome (a run of
        # non-payers must not machine-gun PSX).
        if throttle and i < len(symbols) - 1:
            time.sleep(throttle)

    if not out:
        raise ValueError("no payouts parsed for any requested symbol")

    # A payouts snapshot is a ROLLING dataset re-polled in full each run, so its
    # freshness is the fetch time — NOT the most recent announcement, which is
    # naturally weeks old between earnings seasons. as_of=None => the merge
    # judges staleness by the ok flag, not by a months-old event date.
    latest_announce = latest_date.isoformat() if latest_date else None
    return partition(NAME, out, None, SOURCE, cadence=CADENCE,
                     count=len(out), latest_announce=latest_announce)


if __name__ == "__main__":
    run(NAME, fetch)
