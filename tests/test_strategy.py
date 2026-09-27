from datetime import datetime, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Signal
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy


def _candle(close: str = "110000", volume: str = "1250") -> Candle:
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
        "ema_fast": Decimal("109800"),
        "ema_slow": Decimal("100000"),
        "rsi": Decimal("48"),
        "atr": Decimal("2000"),
        "avg_volume": Decimal("1050"),
        "trend_4h": True,
        "previous_high": Decimal("109700"),
        "resistance": Decimal("121000"),
    }
    values.update(overrides)
    return IndicatorSnapshot(**values)  # type: ignore[arg-type]


def test_buy_when_the_four_hour_and_one_hour_rules_pass() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(), position_open=True) is Signal.BUY


def test_each_failed_rule_returns_hold() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(trend_4h=False), False) is Signal.HOLD
    assert strategy.analyze(_candle(close="120000"), _indicators(), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("39")), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("56")), False) is Signal.HOLD
    assert strategy.analyze(_candle(volume="1154"), _indicators(), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(previous_high=Decimal("110000")), False) is Signal.HOLD
    assert strategy.analyze(_candle(), _indicators(resistance=Decimal("120000")), False) is Signal.HOLD


def test_rsi_and_volume_boundaries_are_inclusive() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("40")), False) is Signal.BUY
    assert strategy.analyze(_candle(), _indicators(rsi=Decimal("55")), False) is Signal.BUY
    assert strategy.analyze(_candle(volume="1155"), _indicators(), False) is Signal.BUY


def test_strategy_does_not_sell() -> None:
    strategy = EmaRsiAtrVolumeStrategy(get_settings())
    assert strategy.analyze(_candle(), _indicators(trend_4h=False), position_open=True) is Signal.HOLD
