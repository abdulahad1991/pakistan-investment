"""Shared infrastructure for the per-category fetchers.

Pure stdlib (urllib) so the parser unit tests import this with zero third-party
deps. The HTTP layer is only exercised at fetch time (in CI); tests call the
``parse_*`` functions directly on fixtures.
"""
import json
import time
import datetime
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PART_DIR = ROOT / "data" / "partitions"

# A realistic browser UA — several official PK sources (PSX, SBP, PBS, forex.pk)
# return 403 to the default python UA.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def utcnow_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url, headers=None, data=None, timeout=30, retries=3, backoff=2.0):
    """GET, or POST when ``data`` is given, with browser UA + linear backoff.

    Returns the decoded body text. Raises the last exception after ``retries``.
    """
    hdrs = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8"}
    if headers:
        hdrs.update(headers)
    body = data.encode() if isinstance(data, str) else data
    method = "POST" if body is not None else "GET"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - retry on any transport error
            last = e
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last


class AllSourcesFailed(Exception):
    """Every source in a crawl_first() chain failed — the signal for run() to
    carry the prior value forward flagged ok=False (rather than a fetcher just
    dying because ONE upstream page changed shape)."""

    def __init__(self, name, errors):
        self.name = name
        self.errors = errors  # list of (label, message)
        joined = "; ".join(f"[{lbl}] {msg}" for lbl, msg in errors)
        super().__init__(f"{name}: all {len(errors)} sources failed: {joined}")


def crawl_first(name, attempts):
    """Failover crawl: return the first source that yields a valid partition.

    ``attempts`` is an ordered ``[(label, thunk), ...]``. Each thunk does its
    own http_get + parse and returns a ``partition(...)`` dict (or raises). We
    try them in priority order — typically: primary source, then a re-crawl of
    an alternate URL carrying the same data, then a cross-provider fallback —
    and return the FIRST that succeeds, annotated with provenance:

      * ``via``            — the label of the source that produced the value.
      * ``failover``       — True when a non-primary source had to step in.
      * ``primary_errors`` — the earlier sources' errors (for the health block).

    Raises AllSourcesFailed only when EVERY attempt fails; run() then carries
    the prior partition forward flagged ok=False. This is what stops a single
    upstream redesign from taking three fetchers stale at once.
    """
    errors = []
    for label, thunk in attempts:
        try:
            payload = thunk()
            if not isinstance(payload, dict) or "value" not in payload:
                raise ValueError("source returned a malformed partition")
            payload = dict(payload)
            payload["via"] = label
            if errors:  # a fallback won — record that the primary was down
                payload["failover"] = True
                payload["primary_errors"] = [f"[{l}] {m}" for l, m in errors]
            return payload
        except Exception as e:  # noqa: BLE001 - try the next source on any error
            errors.append((label, f"{type(e).__name__}: {e}"[:160]))
    raise AllSourcesFailed(name, errors)


def in_band(v, lo, hi):
    """Sanity band — reject absurd parsed values before they reach the site."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return lo <= v <= hi


def partition(name, value, as_of, source, ok=True, cadence=None, **extra):
    """Provenance-wrapped result. ``value`` may be a scalar or a nested dict."""
    p = {
        "name": name,
        "value": value,
        "as_of": as_of,           # the data's own date (e.g. '2026-05'), NOT fetch time
        "source": source,
        "ok": ok,
        "fetched_at": utcnow_iso(),
    }
    if cadence:
        p["cadence"] = cadence
    p.update(extra)
    return p


def write_partition(name, payload):
    PART_DIR.mkdir(parents=True, exist_ok=True)
    (PART_DIR / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_partition(name):
    f = PART_DIR / f"{name}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def run(name, fetch_fn):
    """Execute a fetcher with graceful fallback.

    On success: write the fresh partition (ok=True).
    On failure: KEEP the prior partition but flag ok=False + last_error so the
    merge step / UI can surface 'data delayed' instead of silently serving an
    old number as if it were current. This is the core anti-staleness contract.
    """
    prior = load_partition(name)
    try:
        payload = fetch_fn()
        if not isinstance(payload, dict) or "value" not in payload:
            raise ValueError("fetcher returned a malformed partition")
        print(f"  ✓ {name}: {payload.get('value')!r} (as of {payload.get('as_of')})")
        return write_partition(name, payload)
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"[:200]
        print(f"  ✗ {name} FAILED: {msg}")
        if prior is not None:
            prior = dict(prior)
            prior["ok"] = False
            prior["last_error"] = msg
            prior["last_attempt"] = utcnow_iso()
            return write_partition(name, prior)
        return write_partition(name, partition(
            name, None, None, "n/a", ok=False, last_error=msg))
