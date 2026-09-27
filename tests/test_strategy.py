from datetime import datetime, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Signal
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy


def _candle(close: str = "101", volume: str = "20", low: str = "100") -> Candle:
    close_price = Decimal(close)
    low_price = Decimal(low)
    return Candle(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=close_price,
        high=max(close_price, low_price),
        low=low_price,
        close=close_price,
        volume=Decimal(volume),
    )


def _indicators(**overrides: Decimal | None | bool) -> IndicatorSnapshot:
    values: dict[str, Decimal | None] = {
        "ema_fast": Decimal("100"),
        "ema_slow": Decimal("90"),
        "rsi": Decimal("45"),
        "atr": Decimal("2"),
        "avg_volume": Decimal("10"),
    }
    values.update(overrides)
    return IndicatorSnapshot(**values)


def test_buy_when_all_market_rules_pass_even_with_open_position() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(), position_open=True    ) is Signal.BUY


def test_each_failed_rule_returns_hold() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(volume="10"), _indicators(), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("34.99")), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("55.01")), False) is Signal.HOLD
    assert (
        strategy.analyze(_candle(), _indicators(ema_fast=Decimal("80"), ema_slow=Decimal("90")), False)
        is Signal.HOLD
    )


def test_rsi_boundaries_are_inclusive() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("35")), False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("55")), False) is Signal.BUY


def test_rejection_boundaries() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    edge = _indicators(ema_fast=Decimal("100"), ema_slow=Decimal("90"))
    assert strategy.analyze(_candle(close="101", low="99"), edge, False) is Signal.BUY
    assert strategy.analyze(_candle(close="101", low="98.99"), edge, False) is Signal.HOLD
    assert strategy.analyze(_candle(close="100", low="100"), edge, False) is Signal.HOLD
    assert strategy.analyze(_candle(close="101", low="100.01"), edge, False) is Signal.HOLD


def test_any_utc_hour_can_buy() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    for hour in (0, 15, 23):
        candle = _candle()
        candle = Candle(
            timestamp=datetime(2025, 1, 1, hour, tzinfo=timezone.utc),
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
        assert strategy.analyze(candle, _indicators(), False) is Signal.BUY


def test_trend_flip_does_not_sell() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    snapshot = _indicators(ema_fast=Decimal("90"), ema_slow=Decimal("100"), rsi=Decimal("10"))
    assert strategy.analyze(_candle(), snapshot, position_open=True) is Signal.HOLD
    assert strategy.analyze(_candle(), snapshot, position_open=False) is Signal.HOLD


def test_missing_indicator_holds() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(rsi=None), False) is Signal.HOLD


def test_buy_requires_the_previous_day_trend() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(daily_trend_up=False), False) is Signal.HOLD
