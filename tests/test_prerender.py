"""Unit tests for scripts/prerender.py.

The point of prerender is that the served HTML never contains a bare "-" where a
live figure belongs. These tests pin the two things that can silently regress:
the Pakistani digit grouping (must match formatPKR in app.js) and the
placeholder substitution (must be text-only, idempotent, and leave containers
that have child elements alone).
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("prerender", ROOT / "scripts" / "prerender.py")
prerender = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prerender)


class TestFormatPKR:
    def test_pakistani_grouping(self):
        # X,XX,XXX - not the western X,XXX,XXX
        assert prerender.format_pkr(424200) == "4,24,200"
        assert prerender.format_pkr(178185) == "1,78,185"
        assert prerender.format_pkr(36369) == "36,369"
        assert prerender.format_pkr(999) == "999"
        assert prerender.format_pkr(1000) == "1,000"

    def test_negative_and_none(self):
        assert prerender.format_pkr(-424200) == "-4,24,200"
        assert prerender.format_pkr(None) == "-"


class TestBuildValues:
    DATA = {
        "updated": "2026-07-19T12:35:37Z",
        "macro": {"pkr_usd": 277.96, "sbp_rate": 11.5, "inflation_cpi": 11.1,
                  "kse100_level": 178185},
        "gold": {"tola_24k": 424200, "tola_22k": 388850, "g10_24k": 363689,
                 "g10_22k": 333382, "gram_24k": 36369, "gram_22k": 33338,
                 "chg1y_pct": 25.5, "source_type": "local"},
        "fuel": {"petrol": 316.15, "hsd": 354.35, "kerosene": 233.71,
                 "ldo": 199.98, "asof": "18 Jul 2026"},
    }

    def test_ticker_and_pills(self):
        v = prerender.build_values(self.DATA)
        assert v["tk-kse"] == "1,78,185"
        assert v["m-kse"] == v["h-kse"] == "178K"   # app.js renders these as thousands
        assert v["tk-sbp"] == "11.5%"
        assert v["tk-pkr"] == "&#8360;277.96"

    def test_derived_karats(self):
        v = prerender.build_values(self.DATA)
        # 21K/18K are derived off 24K, then converted at 11.6638 g per tola
        assert v["gr-tola21"] == "&#8360;3,71,175"
        assert v["gr-gram21"] == "&#8360;31,823"
        assert v["gr-tola18"] == "&#8360;3,18,150"

    def test_no_relative_timestamps(self):
        # A relative age baked into static HTML freezes at build time.
        v = prerender.build_values(self.DATA)
        assert "ago" not in v["data-age"]
        assert "19 July 2026" in v["data-age"]

    def test_missing_sections_are_skipped(self):
        v = prerender.build_values({"updated": "2026-07-19T12:35:37Z", "macro": {}})
        assert "gr-tola24" not in v
        assert "f-petrol" not in v


class TestApply:
    def test_fills_and_is_idempotent(self):
        html = '<b id="tk-kse">-</b>'
        once, n = prerender.apply(html, {"tk-kse": "1,78,185"})
        assert once == '<b id="tk-kse">1,78,185</b>' and n == 1
        twice, _ = prerender.apply(once, {"tk-kse": "1,78,185"})
        assert twice == once

    def test_overwrites_a_stale_value(self):
        html = '<b id="tk-kse">1,00,000</b>'
        out, _ = prerender.apply(html, {"tk-kse": "1,78,185"})
        assert out == '<b id="tk-kse">1,78,185</b>'

    def test_leaves_containers_with_children_alone(self):
        # Only the text run up to the next tag is replaced, so an element whose
        # first child is a tag is not clobbered.
        html = '<div id="tk-kse"><span>x</span></div>'
        out, _ = prerender.apply(html, {"tk-kse": "1,78,185"})
        assert "<span>x</span>" in out

    def test_ignores_unknown_ids(self):
        html = '<b id="other">-</b>'
        out, n = prerender.apply(html, {"tk-kse": "1,78,185"})
        assert out == html and n == 0
