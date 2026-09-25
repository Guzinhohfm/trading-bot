from decimal import Decimal

from app.config.settings import Settings, get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Signal


class EmaRsiAtrVolumeStrategy:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position_open: bool,
    ) -> Signal:
        if (
            position_open
            and indicators.ema_fast is not None
            and indicators.ema_slow is not None
            and indicators.ema_fast < indicators.ema_slow
        ):
            return Signal.SELL

        if self._buy_rules(candle, indicators):
            return Signal.BUY
        return Signal.HOLD

    def _buy_rules(self, candle: Candle, indicators: IndicatorSnapshot) -> bool:
        if (
            indicators.ema_fast is None
            or indicators.ema_slow is None
            or indicators.rsi is None
            or indicators.avg_volume is None
        ):
            return False
        settings = self.settings
        trend_ok = indicators.ema_fast > indicators.ema_slow
        rsi_ok = settings.rsi_min <= indicators.rsi <= settings.rsi_max
        volume_ok = candle.volume > indicators.avg_volume
        if indicators.ema_fast == 0:
            return False
        distance = abs(candle.close - indicators.ema_fast) / indicators.ema_fast
        price_ok = distance <= settings.price_distance_max
        return trend_ok and rsi_ok and volume_ok and price_ok
