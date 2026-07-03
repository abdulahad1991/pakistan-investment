"""Pure-logic tests for the daily brief's social copy layer:

  * pick_headline — biggest-|%|-move selection, FLAT DAY, missing data -> None
  * build_yt_title — story-first ordering, hard <=100-char cap
  * build_yt_description — searchable first line ("KSE 100 today" +
    "gold rate today Pakistan" with the day's numbers)

No network, no filesystem — these functions are pure by design.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_daily as bd  # noqa: E402


def _data(kse=184841, kse_pct=2.27, tola=433300, usd=278.15):
    """Minimal data.json shape for the headline/title/description layer.
    kse_pct=None mirrors a data.json without kse100_change_pct."""
    macro = {"kse100_level": kse, "pkr_usd": usd,
             "sbp_rate": 11.5, "inflation_cpi": 11.7}
    if kse_pct is not None:
        macro["kse100_change_pct"] = kse_pct
    return {
        "macro": macro,
        "gold": {"tola_24k": tola, "chg1y_pct": 25.5,
                 "history": {"labels": [], "values": []}},
        "kse100_history": {"labels": [], "values": []},
        "stocks": [],
    }


# Previous trading day's social-kit payload, new structured form.
PREV = {"metrics": {"kse100": 180000.0, "gold_tola": 424400.0, "pkr_usd": 278.15}}


# ---------------------------------------------------------------------------
# pick_headline
# ---------------------------------------------------------------------------
def test_headline_biggest_move_wins_gold():
    # KSE +0.5% vs gold (433300 vs 424400) = +2.097% -> gold leads
    h = bd.pick_headline(_data(kse_pct=0.5), PREV,
                         date_str="2 Jul 2026", session="Market close")
    assert h == {"text": "GOLD ₨4,33,300", "kicker": "+2.1% TODAY",
                 "sub": "2 Jul · Market close"}


def test_headline_kse_wins_without_prev_payload():
    # No previous payload: only the KSE candidate (data.json's own change pct).
    h = bd.pick_headline(_data(kse_pct=2.27), None,
                         date_str="2 Jul 2026", session="Market open")
    assert h["text"] == "KSE-100 184,841"        # western grouping for the index
    assert h["kicker"] == "+2.3% TODAY"
    assert h["sub"] == "2 Jul · Market open"


def test_headline_negative_move_keeps_sign():
    h = bd.pick_headline(_data(kse_pct=-1.24), None,
                         date_str="3 Jul 2026", session="Market close")
    assert h["kicker"] == "-1.2% TODAY"


def test_headline_flat_day():
    # KSE +0.05%, gold 0%, USD 0% -> every |move| < 0.15% -> FLAT DAY
    prev = {"metrics": {"kse100": 184841, "gold_tola": 433300, "pkr_usd": 278.15}}
    h = bd.pick_headline(_data(kse_pct=0.05), prev,
                         date_str="2 Jul 2026", session="Market close")
    assert h["kicker"] == "FLAT DAY"


def test_headline_missing_data_returns_none():
    assert bd.pick_headline({}, None) is None
    # KSE level present but NO day change derivable anywhere -> no candidates.
    assert bd.pick_headline(_data(kse_pct=None), None) is None
    # Garbage input must not raise either.
    assert bd.pick_headline({"macro": None, "gold": None}, {"metrics": "x"}) is None


def test_headline_prev_metrics_regex_fallback_from_hook():
    # Pre-`metrics` payloads: numbers are recovered from our own hook copy.
    prev = {"hook": ("Pakistan market brief — 2 Jul 2026 (Market close): "
                     "KSE-100 at 180,000, the rupee at ₨278.15/$, "
                     "gold ₨4,24,400/tola (+25.5% in a year).")}
    h = bd.pick_headline(_data(kse_pct=0.5), prev,
                         date_str="3 Jul 2026", session="Market close")
    assert h["text"] == "GOLD ₨4,33,300"
    assert h["kicker"] == "+2.1% TODAY"


# ---------------------------------------------------------------------------
# YouTube title
# ---------------------------------------------------------------------------
def _props(data, session="Market close"):
    return bd.build_props(data, "2 Jul 2026", session)


def test_title_gold_story_first():
    data = _data(kse_pct=0.5)
    cands = bd.day_candidates(data, PREV)          # gold is the big move
    t = bd.build_yt_title(_props(data), cands, "2 Jul 2026")
    assert t.startswith("Gold rate today ₨4,33,300 (+2.1%)")
    assert "KSE-100 184,841 (+0.5%)" in t
    assert t.endswith("| 2 Jul close brief")
    assert len(t) <= bd.YT_TITLE_MAX


def test_title_kse_story_first():
    data = _data(kse_pct=2.27)
    cands = bd.day_candidates(data, None)          # KSE only
    t = bd.build_yt_title(_props(data), cands, "2 Jul 2026")
    assert t.startswith("KSE-100 today 184,841 (+2.3%)")
    assert "gold rate ₨4,33,300/tola" in t
    assert len(t) <= bd.YT_TITLE_MAX


def test_title_fallback_without_candidates_and_open_session():
    t = bd.build_yt_title(_props(_data(), session="Market open"), None, "2 Jul 2026")
    assert t.startswith("KSE-100 today 184,841")
    assert t.endswith("| 2 Jul open brief")
    assert len(t) <= bd.YT_TITLE_MAX


def test_title_never_exceeds_100_chars():
    # Absurdly large values still respect YouTube's hard cap.
    data = _data(kse=999999999, tola=99999999999, kse_pct=12.34)
    prev = {"metrics": {"kse100": 9e8, "gold_tola": 9e10, "pkr_usd": 500.0}}
    cands = bd.day_candidates(data, prev)
    t = bd.build_yt_title(_props(data), cands, "22 Dec 2026")
    assert len(t) <= 100


# ---------------------------------------------------------------------------
# YouTube description
# ---------------------------------------------------------------------------
def test_description_first_line_keywords_and_numbers():
    data = _data()
    cands = bd.day_candidates(data, PREV)
    desc = bd.build_yt_description(_props(data), "Story of the day.", cands)
    first = desc.splitlines()[0]
    assert "KSE 100 today" in first
    assert "gold rate today Pakistan" in first
    assert "184,841" in first                      # the day's numbers, in line 1
    assert "4,33,300" in first
    assert "(+2.3%)" in first                      # KSE day change


def test_description_reuses_story_then_static_block():
    desc = bd.build_yt_description(_props(_data()), "Unique daily story line.", None)
    assert "Unique daily story line." in desc
    assert "not financial advice" in desc.lower()
    assert "pakinvestlysis.com" in desc
    assert "#Shorts" in desc                       # daily Short keeps the tag


def test_social_payload_carries_metrics_and_restrained_tags():
    data = _data()
    p = _props(data)
    s = bd.social_payload("2 Jul 2026", p, bd.day_candidates(data, PREV))
    # metrics block = what tomorrow's run diffs against
    assert s["metrics"] == {"kse100": 184841, "gold_tola": 433300, "pkr_usd": 278.15}
    assert s["youtube"]["tags"] == bd.YT_TAGS      # unchanged, restrained set
    assert len(s["youtube"]["title"]) <= 100
    # LinkedIn copy stays on the existing honest format
    assert "Not financial advice" in s["linkedin"]["text"]
    assert "Market close" in s["linkedin"]["text"]


# ---------------------------------------------------------------------------
# build_spotlight — the rotating bonus scene (tool / rate / question)
# ---------------------------------------------------------------------------
SPOT_KEYS = {"kind", "kicker", "heading", "body", "cta"}


def _spot_data():
    d = _data()
    d["national_savings"] = [
        {"name": "Special Savings Certificate", "rate": 12.4, "recommended": True},
        {"name": "Behbood Savings Certificate", "rate": 13.9},
    ]
    d["mutual_funds"] = [
        {"name": "Meezan Islamic Income Fund", "type": "Islamic Income", "ret_1y": 9.03},
        {"name": "Al Meezan Mutual Fund", "type": "Islamic Equity", "ret_1y": 33.7},
    ]
    return d


def test_spotlight_rotates_all_three_kinds_across_sessions():
    d = _spot_data()
    cands = bd.day_candidates(d, PREV)
    # (ordinal*2 + sess) % 3 -> consecutive sessions walk tool -> rate -> question
    kinds = [bd.build_spotlight(d, cands, s, o)["kind"]
             for o in (738709, 738710) for s in ("Market open", "Market close")]
    assert set(kinds) == {"tool", "rate", "question"}
    # same (day, session) is deterministic
    a = bd.build_spotlight(d, cands, "Market open", 738709)
    assert a == bd.build_spotlight(d, cands, "Market open", 738709)
    assert set(a) == SPOT_KEYS


def test_spotlight_rate_prefers_recommended_savings_vs_inflation():
    d = _spot_data()  # inflation_cpi = 11.7 < 12.4 -> "se oopar"
    s = bd._spotlight_rate(d)
    assert s["kind"] == "rate"
    assert s["heading"] == "12.4%"          # recommended cert wins over 13.9%
    assert "Special Savings" in s["body"]
    assert "11.7" in s["body"] and "oopar" in s["body"]


def test_spotlight_rate_falls_back_to_income_fund_then_tool():
    d = _spot_data()
    d["national_savings"] = []
    s = bd._spotlight_rate(d)
    assert s["heading"] == "9.03%"          # income fund only, never equity
    assert "Meezan Islamic Income" in s["body"]
    d["mutual_funds"] = []
    assert bd._spotlight_rate(d) is None
    # a rate SLOT with no rate data promotes the tool promo instead
    spot = bd.build_spotlight(d, None, "Market open", 738710)  # slot 1 = rate
    assert spot["kind"] == "tool"


def test_spotlight_question_uses_kse_move_or_generic():
    d = _spot_data()
    q = bd._spotlight_question(bd.day_candidates(d, PREV))
    assert q["heading"] == "KSE +2.3% aaj"
    assert q["cta"] == "COMMENT BELOW"
    assert bd._spotlight_question(None)["heading"] == "Sona ya stocks?"


def test_spotlight_never_raises_on_garbage():
    spot = bd.build_spotlight({"national_savings": "x", "mutual_funds": None},
                              None, None, 738711)
    assert set(spot) == SPOT_KEYS and spot["kind"] in {"tool", "rate", "question"}
