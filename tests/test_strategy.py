from datetime import datetime, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Signal
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy


def _candle(close: str = "100500", volume: str = "1") -> Candle:
    price = Decimal(close)
    return Candle(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal(volume),
    )


def _indicators(**overrides: object) -> IndicatorSnapshot:
    values: dict[str, object] = {
        "ema_fast": Decimal("100000"),
        "ema_slow": Decimal("90000"),
        "rsi": Decimal("48"),
        "atr": Decimal("2000"),
        "avg_volume": Decimal("1"),
        "trend_4h": True,
        "previous_high": Decimal("100400"),
        "previous_low": Decimal("99000"),
        "previous_ema20": Decimal("100000"),
        "ema50_4h": Decimal("110000"),
        "ema200_4h": Decimal("100000"),
        "close_4h": Decimal("120000"),
        "ema50_4h_prior": Decimal("105000"),
    }
    values.update(overrides)
    return IndicatorSnapshot(**values)  # type: ignore[arg-type]


def test_buy_when_the_four_hour_trend_and_the_one_hour_recovery_pass() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(), position_open=True) is Signal.BUY


def test_previous_candle_must_touch_the_ema() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    missed = _indicators(previous_low=Decimal("100100"), previous_ema20=Decimal("100000"))
    decision = strategy.explain(_candle(), missed, False)
    assert decision.signal is Signal.HOLD
    assert "pullback_toca_ema20" in decision.failed
    touched = _indicators(previous_low=Decimal("100000"), previous_ema20=Decimal("100000"))
    assert strategy.analyze(_candle(close="105000"), touched, False) is Signal.BUY


def test_price_below_the_ema_does_not_confirm_the_recovery() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    candle = _candle(close="99500")
    decision = strategy.explain(candle, _indicators(previous_high=Decimal("99000")), False)
    assert decision.signal is Signal.HOLD
    assert "close_acima_ema20" in decision.failed
    assert "pullback_toca_ema20" not in decision.failed


def test_each_failed_rule_returns_hold() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    cases = [
        _indicators(ema50_4h=Decimal("90000")),
        _indicators(close_4h=Decimal("100000")),
        _indicators(ema50_4h_prior=Decimal("110000")),
        _indicators(rsi=Decimal("39")),
        _indicators(rsi=Decimal("56")),
        _indicators(previous_high=Decimal("100500")),
        _indicators(previous_low=Decimal("100100"), previous_ema20=Decimal("100000")),
    ]
    for indicators in cases:
        assert strategy.analyze(_candle(), indicators, False) is Signal.HOLD


def test_touch_and_rsi_boundaries_are_inclusive() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    touched = _indicators(previous_low=Decimal("100000"), previous_ema20=Decimal("100000"))
    assert strategy.analyze(_candle(), touched, False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("40")), False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("55")), False) is Signal.BUY


def test_wider_rsi_band_uses_the_configured_limits() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings(rsi_min=Decimal("35"), rsi_max=Decimal("60")))
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("35")), False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("60")), False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("34")), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("61")), False) is Signal.HOLD


def test_volume_filter_requires_110_percent_of_the_average() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings(require_volume=True))
    assert strategy.analyze(_candle(volume="1.1"), _indicators(), False) is Signal.BUY
    assert strategy.analyze(_candle(volume="1.09"), _indicators(), False) is Signal.HOLD
    decision = strategy.explain(_candle(), _indicators(avg_volume=None), False)
    assert "volume_acima_media" in decision.failed


def test_resistance_filter_needs_room_for_the_ten_percent_target() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings(require_resistance=True))
    assert strategy.analyze(_candle(), _indicators(resistance=Decimal("110550")), False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(resistance=Decimal("110549")), False) is Signal.HOLD
    decision = strategy.explain(_candle(), _indicators(resistance=None), False)
    assert "espaco_ate_alvo" in decision.failed


def test_explain_names_every_failed_check() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    decision = strategy.explain(
        _candle(close="90000"),
        _indicators(
            ema50_4h=None,
            rsi=Decimal("70"),
            previous_high=None,
            previous_low=Decimal("101000"),
            previous_ema20=Decimal("100000"),
        ),
        False,
    )
    assert decision.failed == (
        "ema50_acima_ema200",
        "ema50_subindo",
        "pullback_toca_ema20",
        "rsi_na_faixa",
        "close_acima_ema20",
        "close_acima_maxima",
    )


def test_ema20_trigger_ignores_the_previous_high() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings(entry_trigger="ema20"))
    blocked = _indicators(previous_high=Decimal("100500"))
    assert strategy.analyze(_candle(), blocked, False) is Signal.BUY


def test_bullish_trigger_needs_a_green_candle_and_not_the_previous_high() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings(entry_trigger="bullish"))
    above_prior_high = _indicators(previous_high=Decimal("200000"))
    assert strategy.analyze(_candle(), above_prior_high, False) is Signal.HOLD
    green = Candle(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100200"),
        high=Decimal("100500"),
        low=Decimal("100200"),
        close=Decimal("100500"),
        volume=Decimal("1"),
    )
    assert strategy.analyze(green, above_prior_high, False) is Signal.BUY


def test_v2_filters_stay_off_unless_asked() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    decision = strategy.explain(_candle(), _indicators(), False)
    codes = {check.code for check in decision.checks}
    assert "separacao_ema" not in codes
    assert "rsi_subindo" not in codes
    assert decision.signal is Signal.BUY


def test_separation_and_slope_need_the_minimum_gap() -> None:
    strategy = EmaRsiAtrVolumeStrategy(
        get_settings(trend_separation_min=Decimal("0.02"), ema_slope_min=Decimal("0.005"))
    )
    weak = _indicators(ema50_4h=Decimal("101000"), ema200_4h=Decimal("100000"), ema50_4h_prior=Decimal("100800"))
    assert strategy.analyze(_candle(), weak, False) is Signal.HOLD
    strong = _indicators(ema50_4h=Decimal("103000"), ema200_4h=Decimal("100000"), ema50_4h_prior=Decimal("102000"))
    assert strategy.analyze(_candle(), strong, False) is Signal.BUY


def test_rising_rsi_and_candle_close_near_the_high() -> None:
    strategy = EmaRsiAtrVolumeStrategy(
        get_settings(require_rsi_rising=True, candle_quality="top30")
    )
    falling = _indicators(previous_rsi=Decimal("50"), rsi=Decimal("48"))
    assert strategy.analyze(_ranged_candle("100200"), falling, False) is Signal.HOLD
    near_high = _ranged_candle("100450", low="100000", high="100500")
    rising = _indicators(previous_rsi=Decimal("47"), rsi=Decimal("48"))
    assert strategy.analyze(near_high, rising, False) is Signal.BUY
    far_from_high = _ranged_candle("100450", low="100000", high="100800")
    assert strategy.analyze(far_from_high, rising, False) is Signal.HOLD


def test_atr_band_uses_the_four_hour_atr() -> None:
    strategy = EmaRsiAtrVolumeStrategy(
        get_settings(atr_pct_min=Decimal("0.01"), atr_pct_max=Decimal("0.025"))
    )
    quiet = _indicators(atr_4h=Decimal("500"))
    tradable = _indicators(atr_4h=Decimal("1800"))
    wild = _indicators(atr_4h=Decimal("4000"))
    assert strategy.analyze(_candle(), quiet, False) is Signal.HOLD
    assert strategy.analyze(_candle(), tradable, False) is Signal.BUY
    assert strategy.analyze(_candle(), wild, False) is Signal.HOLD


def _ranged_candle(close: str, low: str = "100000", high: str = "100500") -> Candle:
    return Candle(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100200"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
    )


def test_daily_trend_blocks_until_the_higher_timeframe_is_up() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings(require_daily_trend=True))
    assert strategy.analyze(_candle(), _indicators(trend_daily=False), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(trend_daily=True), False) is Signal.BUY


def test_strategy_does_not_sell() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(ema50_4h=Decimal("1")), position_open=True) is Signal.HOLD
