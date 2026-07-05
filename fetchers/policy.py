"""SBP Policy Rate corridor — State Bank of Pakistan (SBP), the official source.

SBP's 2026-07 site redesign killed the legacy /ecodata/index2.asp rate box
(the URL now serves a generic shell; /economic-data is JS-rendered, empty
server-side). The corridor now ships in the server-rendered "Economic Data
snapshot" on the M2M page (ecodata/rates/m2m/m2m-current.asp):
  - SBP Policy Rate 11.50% p.a.                    (the headline target rate)
  - SBP Overnight Reverse (Repo) Ceiling Rate      = policy rate + 100bps
  - SBP Overnight Reverse (Floor) Rate             = policy rate - 100bps

The labels are wrapped in nested tags and the percentages live in separate
cells, so we strip tags + collapse whitespace, then anchor on the distinctive
label text (paren placement differs between the old box and the new snapshot,
so 'Ceiling/Floor ... Rate' tolerates an optional ')'). Both layouts also show
a "Weighted-average Overnight Repo Rate" (e.g. 11.25%) which we must NOT
confuse with the corridor — we only match values that immediately follow our
three labels.

STANCE/direction is NOT on this page. It is derived in fetch() by comparing the
freshly parsed rate to the prior partition: up => Tightening, down => Easing,
equal => Holding. Policy changes are EVENT-driven (MPC meetings), not scheduled.
"""
import re
import html as _html
from .base import http_get, partition, run, in_band, load_partition

SOURCE = "https://www.sbp.org.pk/ecodata/rates/m2m/m2m-current.asp"
NAME = "policy"


def _plain(html_text):
    """HTML -> tag-free, entity-decoded, single-spaced plain text."""
    t = _html.unescape(html_text)
    t = t.replace("\xa0", " ")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def parse_policy(html_text):
    """Return {'rate', 'floor', 'ceiling'} (floats, % p.a.) from the SBP rate box.

    Pure string -> dict; no network. Raises ValueError if any leg is missing.
    """
    text = _plain(html_text)

    def _num(pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return float(m.group(1)) if m else None

    # "SBP Policy <strong>Rat</strong>e" tag-strips to "SBP Policy Rat e", so we
    # anchor on "SBP Policy" and grab the first percentage that closely follows.
    rate = _num(r"SBP Policy.{0,40}?(\d+(?:\.\d+)?)\s*%")
    # Legacy box prints "(Ceiling) Rate"; the 2026-07 snapshot "(Repo) Ceiling
    # Rate" — hence the optional ')' between the keyword and "Rate".
    ceiling = _num(r"Ceiling\)?\s*Rate\s*(\d+(?:\.\d+)?)\s*%")
    floor = _num(r"Floor\)?\s*Rate\s*(\d+(?:\.\d+)?)\s*%")

    if rate is None or ceiling is None or floor is None:
        raise ValueError(
            f"SBP policy rate box not found: rate={rate} "
            f"floor={floor} ceiling={ceiling}")
    return {"rate": rate, "floor": floor, "ceiling": ceiling}


def fetch():
    parsed = parse_policy(http_get(SOURCE))
    if not in_band(parsed["rate"], 5, 25):  # SBP policy rate realistically 5-25%
        raise ValueError(f"SBP policy rate out of sanity band: {parsed['rate']}")

    # Direction is not on the page — derive it from the prior partition, and
    # PERSIST it until the rate actually changes. base.run() overwrites the
    # partition with the current rate every run, so the run after any MPC change
    # would see prior==current; resetting to "Holding" there would flip the
    # stance back within one cycle and read "Holding" right through an active
    # hiking/cutting cycle (the very bug this pipeline set out to fix). So when
    # the rate is unchanged we CARRY FORWARD the last recorded stance and only
    # recompute Tightening/Easing on an actual rate move.
    prior = load_partition(NAME)
    prior_rate = None
    prior_dir = None
    if prior and isinstance(prior.get("value"), dict):
        prior_rate = prior["value"].get("rate")
        prior_dir = prior.get("sbp_direction")
    direction = prior_dir or "Holding"
    if prior_rate is not None:
        try:
            pr = float(prior_rate)
            if parsed["rate"] > pr:
                direction = "Tightening"
            elif parsed["rate"] < pr:
                direction = "Easing"
            # else: rate unchanged -> keep the carried-forward prior stance
        except (TypeError, ValueError):
            pass

    return partition(
        NAME, parsed, as_of=None, source="State Bank of Pakistan (SBP)",
        cadence="event", sbp_direction=direction, source_url=SOURCE)


if __name__ == "__main__":
    run(NAME, fetch)
