from datetime import datetime, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Signal
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy


def _candle(close: str = "100", volume: str = "20") -> Candle:
    return Candle(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal(volume),
    )


def _indicators(**overrides: Decimal | None) -> IndicatorSnapshot:
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
    far = _indicators(ema_fast=Decimal("90"), ema_slow=Decimal("80"))
    assert strategy.analyze(_candle(close="100"), far, False) is Signal.HOLD


def test_rsi_and_distance_boundaries_are_inclusive() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("35")), False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("55")), False) is Signal.BUY
    edge = _indicators(ema_fast=Decimal("100"), ema_slow=Decimal("90"))
    assert strategy.analyze(_candle(close="101"), edge, False) is Signal.BUY


def test_sell_when_position_is_open_and_trend_flips() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    snapshot = _indicators(ema_fast=Decimal("90"), ema_slow=Decimal("100"), rsi=Decimal("10"))
    assert strategy.analyze(_candle(), snapshot, position_open=True) is Signal.SELL
    assert strategy.analyze(_candle(), snapshot, position_open=False) is Signal.HOLD


def test_missing_indicator_holds() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(rsi=None), False) is Signal.HOLD
