"""petrol.py parsers must extract the four OGRA fuel rates from real captured
responses: PakWheels (primary, all four + w.e.f date) and PetrolPrice.com.pk
(fallback, the two headline fuels + effective date). LPG/HOBC rows on the page
must never be mistaken for a listed fuel."""
from pathlib import Path

import pytest

from fetchers import petrol

FIX = Path(__file__).parent / "fixtures"


def _read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_pakwheels_parses_all_four_new_prices():
    out = petrol.parse_pakwheels(_read("pakwheels_fuel.html"))
    # New Price column (current rate), exactly as on the captured page.
    assert out["petrol"] == 315.71
    assert out["hsd"] == 353.3
    assert out["ldo"] == 199.98        # PakWheels labels LDO "Light Speed Diesel"
    assert out["kerosene"] == 233.71
    assert out["as_of"] == "2026-07-18"


def test_pakwheels_ignores_lpg_and_old_price():
    out = petrol.parse_pakwheels(_read("pakwheels_fuel.html"))
    assert "lpg" not in out
    # 241.43 is LPG's new price, 310.71 is petrol's OLD price — neither should leak.
    assert 241.43 not in out.values()
    assert out["petrol"] != 310.71


def test_pakwheels_hero_sentence_fallback():
    html = ('<p class="fs18 mb30">Current and Latest Petrol Price in Pakistan is '
            'Rs. 300.5/Ltr, High Speed Diesel is Rs. 310.9/Ltr</p>'
            '<p class="fs16">Prices w.e.f 01-August-2026</p>')
    out = petrol.parse_pakwheels(html)
    assert out == {"petrol": 300.5, "hsd": 310.9, "as_of": "2026-08-01"}


def test_pakwheels_missing_raises():
    with pytest.raises(ValueError):
        petrol.parse_pakwheels("<html><body>no fuel table here</body></html>")


def test_petrolprice_fallback_headline_fuels():
    out = petrol.parse_petrolprice(_read("petrolprice_fuel.html"))
    assert out["petrol"] == 310.71
    assert out["hsd"] == 323.3
    assert out["as_of"] == "2026-07-11"


def test_value_keeps_four_fuels_rounded_and_drops_asof():
    v = petrol._value({"petrol": 315.712, "hsd": 353.3, "ldo": 199.98,
                       "kerosene": 233.71, "as_of": "2026-07-18", "lpg": 241.43})
    assert v == {"petrol": 315.71, "hsd": 353.3, "kerosene": 233.71, "ldo": 199.98}


def test_guard_rejects_absurd_price():
    with pytest.raises(ValueError):
        petrol._guard({"petrol": 31571})   # missed a decimal — must be caught
