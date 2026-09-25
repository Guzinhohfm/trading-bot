from enum import Enum
from typing import Protocol

from app.market.candles import Candle, IndicatorSnapshot


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy(Protocol):
    def analyze(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position_open: bool,
    ) -> Signal:
        """Le somente mercado. Risco, saldo e ordens ficam fora daqui."""
