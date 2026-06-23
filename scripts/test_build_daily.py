import unittest

import build_daily as bd

# Minimal fixture mirroring the real data.json shape consumed by build_props.
DATA = {
    "macro": {
        "pkr_usd": 278.1,
        "sbp_rate": 11.5,
        "inflation_cpi": 7.0,
        "kse100_level": 179516,
    },
    "kse100_history": {"labels": ["Jan'25", "Jun'26"], "values": [162994, 173001]},
    "gold": {
        "tola_24k": 445500,
        "chg1y_pct": 23.7,
        "history": {"labels": ["Jul'25", "Jun'26"], "values": [332000, 410000]},
    },
    "stocks": [
        {"ticker": "FFC", "name": "Fauji Fertilizer", "chg1y": 56.8},
        {"ticker": "HUBC", "name": "Hub Power", "chg1y": 88.3},
        {"ticker": "MCB", "name": "MCB Bank", "chg1y": 55.8},
        {"ticker": "OGDC", "name": "Oil & Gas Dev", "chg1y": 38.1},
        {"ticker": "PSO", "name": "Pakistan State Oil", "chg1y": 12.0},
    ],
}
AS_OF = "22 Jun 2026"
SESSION = "Market open"


class BuildDailyTest(unittest.TestCase):
    def setUp(self):
        self.p = bd.build_props(DATA, AS_OF, SESSION)

    def test_top_level_keys(self):
        self.assertEqual(
            set(self.p.keys()),
            {"colors", "audio", "date", "session", "footer", "macro", "gold",
             "kseSeries", "goldSeries", "movers", "allocation"},
        )
        self.assertEqual(self.p["date"], AS_OF)
        self.assertEqual(self.p["footer"], bd.FOOTER)

    def test_session_passthrough(self):
        self.assertEqual(self.p["session"], SESSION)

    def test_macro_has_all_five_rates(self):
        # The video board renders these five: KSE-100, rupee, SBP rate, inflation
        # (+ gold lives in its own key). Inflation is the row added for parity
        # with the website's live macro pills.
        self.assertEqual(
            self.p["macro"],
            {"kse100": 179516, "pkrUsd": 278.1, "sbpRate": 11.5, "inflation": 7.0},
        )

    def test_inflation_comes_from_cpi(self):
        self.assertEqual(self.p["macro"]["inflation"], DATA["macro"]["inflation_cpi"])

    def test_gold_value_and_change(self):
        self.assertEqual(self.p["gold"], {"tola": 445500, "change1y": 23.7})

    def test_series_pin_live_value_at_end(self):
        # last point of each series is pinned to the headline figure
        self.assertEqual(self.p["kseSeries"]["values"][-1], 179516)
        self.assertEqual(self.p["goldSeries"]["values"][-1], 445500)

    def test_movers_sorted_desc_top4(self):
        tickers = [m["ticker"] for m in self.p["movers"]]
        self.assertEqual(tickers, ["HUBC", "FFC", "MCB", "OGDC"])  # PSO drops off
        self.assertEqual(self.p["movers"][0]["change1y"], 88.3)

    def test_caption_is_honest_with_session_and_number(self):
        md = bd.caption_md("2026-06-22", self.p)
        self.assertIn("Not financial advice", md)
        self.assertIn("## LinkedIn", md)
        self.assertIn("## YouTube Short", md)
        self.assertIn(SESSION, md)              # session tag surfaces in the copy
        self.assertIn("4,45,500", md)            # Pakistani grouping for gold/tola


if __name__ == "__main__":
    unittest.main()
