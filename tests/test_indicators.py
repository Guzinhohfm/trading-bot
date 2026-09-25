from decimal import Decimal

import pytest

from app.market.indicators import atr, average_volume, ema, rsi, true_range


def test_ema20_matches_recurrence_after_flat_seed() -> None:
    closes = [Decimal("100")] * 20 + [Decimal("121")]
    series = ema(closes, 20)
    assert series[18] is None
    assert series[19] == Decimal("100")
    assert series[20] == Decimal("2142") / Decimal("21")


def test_ema50_alpha_on_two_steps() -> None:
    closes = [Decimal("50")] * 50 + [Decimal("101")]
    series = ema(closes, 50)
    alpha = Decimal(2) / Decimal(51)
    expected = alpha * Decimal("101") + (Decimal(1) - alpha) * Decimal("50")
    assert series[50] == expected


def test_short_series_is_all_missing() -> None:
    closes = [Decimal("1"), Decimal("2"), Decimal("3")]
    assert ema(closes, 20) == [None, None, None]
    assert rsi(closes, 14) == [None, None, None]
    assert average_volume([Decimal("1")], 20) == [None]


def test_rsi_wilder_stays_between_zero_and_hundred() -> None:
    closes = [Decimal(str(value)) for value in (10, 12, 11, 13, 9, 15, 14, 16)]
    series = rsi(closes, 2)
    present = [value for value in series if value is not None]
    assert present
    assert all(Decimal("0") <= value <= Decimal("100") for value in present)
    assert series[2] == Decimal("200") / Decimal("3")


def test_atr_uses_true_range_and_wilder_smoothing() -> None:
    highs = [Decimal("10"), Decimal("11"), Decimal("12"), Decimal("10")]
    lows = [Decimal("8"), Decimal("9"), Decimal("8"), Decimal("7")]
    closes = [Decimal("9"), Decimal("10"), Decimal("9"), Decimal("8")]
    assert true_range(Decimal("11"), Decimal("9"), Decimal("9")) == Decimal("2")
    assert true_range(Decimal("12"), Decimal("8"), Decimal("10")) == Decimal("4")
    series = atr(highs, lows, closes, 2)
    assert series[0] is None
    assert series[1] is None
    assert series[2] == Decimal("3")
    assert series[3] == Decimal("3")


def test_average_volume_includes_current_candle() -> None:
    volumes = [Decimal(str(value)) for value in range(1, 21)]
    series = average_volume(volumes, 20)
    assert series[18] is None
    assert series[19] == Decimal("210") / Decimal("20")


def test_atr_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        atr([Decimal("1")], [Decimal("1"), Decimal("1")], [Decimal("1")], 14)
