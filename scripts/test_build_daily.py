import unittest

import build_daily as bd

# Minimal fixture mirroring the real data.json shape.
DATA = {
    "macro": {
        "pkr_usd": 278.1,
        "sbp_rate": 11.5,
        "sbp_direction": "Holding",
        "kse100_level": 179516,
    },
    "national_savings": [
        {"name": "Behbood Savings Certificate", "rate": 12.72},
        {"name": "Special Savings Certificate", "rate": 11.6},
    ],
    "kse100_history": {"values": [162994, 173001]},
    "gold": {"tola_24k": 445500, "chg1y_pct": 23.7},
}
AS_OF = "22 Jun 2026"


class BuildDailyTest(unittest.TestCase):
    def setUp(self):
        self.metrics = bd.build_metrics(DATA, AS_OF)

    def test_all_five_metrics_present(self):
        keys = [m["key"] for m in self.metrics]
        self.assertEqual(keys, ["gold", "kse100", "policy", "fx", "nss"])

    def test_props_match_schema_keys(self):
        expected = {
            "colors", "audio", "durationInFrames", "kicker", "label", "value",
            "valuePrefix", "valueSuffix", "decimals", "locale", "trend",
            "changeLabel", "asOf", "takeaway", "footer",
        }
        for m in self.metrics:
            self.assertEqual(set(m["props"].keys()), expected, m["key"])
            self.assertEqual(m["props"]["asOf"], AS_OF)
            self.assertEqual(m["props"]["footer"], bd.FOOTER)

    def test_gold_value_and_trend(self):
        gold = self.metrics[0]["props"]
        self.assertEqual(gold["value"], 445500)
        self.assertEqual(gold["valuePrefix"], "₨")
        self.assertEqual(gold["locale"], "en-IN")
        self.assertEqual(gold["trend"], "up")  # chg1y_pct 23.7 > 0

    def test_kse_trend_from_history(self):
        kse = self.metrics[1]["props"]
        self.assertEqual(kse["trend"], "up")  # 173001 > 162994

    def test_nss_uses_behbood_rate(self):
        nss = self.metrics[4]["props"]
        self.assertEqual(nss["value"], 12.72)
        self.assertEqual(nss["valueSuffix"], "%")

    def test_pick_rotation_is_deterministic(self):
        # yday 1 -> index 1 % 5 == 1 -> kse100
        self.assertEqual(bd.pick(self.metrics, 1)["key"], "kse100")
        self.assertEqual(bd.pick(self.metrics, 5)["key"], "gold")  # 5 % 5 == 0

    def test_caption_is_honest_and_has_number(self):
        md = bd.caption_md("2026-06-22", self.metrics[0])
        self.assertIn("Not financial advice", md)
        self.assertIn("## LinkedIn", md)
        self.assertIn("## YouTube Short", md)
        self.assertIn("4,45,500", md)  # Pakistani grouping in caption text


if __name__ == "__main__":
    unittest.main()
