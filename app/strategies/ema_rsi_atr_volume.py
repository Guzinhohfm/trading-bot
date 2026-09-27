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
        del position_open
        if self._buy_rules(candle, indicators):
            return Signal.BUY
        return Signal.HOLD

    def _buy_rules(self, candle: Candle, indicators: IndicatorSnapshot) -> bool:
        ema20 = indicators.ema_fast
        if (
            ema20 is None
            or ema20 == 0
            or indicators.rsi is None
            or indicators.avg_volume is None
            or indicators.previous_high is None
            or indicators.resistance is None
            or not indicators.trend_4h
        ):
            return False
        settings = self.settings
        distance = abs(candle.close - ema20) / ema20
        pullback = distance <= settings.price_distance_max
        rsi_ok = settings.rsi_min <= indicators.rsi <= settings.rsi_max
        volume_ok = candle.volume >= indicators.avg_volume * settings.volume_factor
        momentum = candle.close > indicators.previous_high and candle.close > ema20
        room = indicators.resistance >= candle.close * (Decimal(1) + settings.stop_pct * settings.reward_multiple)
        return pullback and rsi_ok and volume_ok and momentum and room
