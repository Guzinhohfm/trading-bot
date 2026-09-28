from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class IndicatorSnapshot:
    ema_fast: Decimal | None
    ema_slow: Decimal | None
    rsi: Decimal | None
    atr: Decimal | None
    avg_volume: Decimal | None
    trend_4h: bool = False
    previous_high: Decimal | None = None
    previous_low: Decimal | None = None
    previous_ema20: Decimal | None = None
    ema50_4h: Decimal | None = None
    ema200_4h: Decimal | None = None
    close_4h: Decimal | None = None
    ema50_4h_prior: Decimal | None = None
    resistance: Decimal | None = None
    previous_rsi: Decimal | None = None
    atr_4h: Decimal | None = None
    trend_daily: bool = False
