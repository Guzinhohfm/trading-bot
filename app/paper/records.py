"""Linha do diario de paper. Uma por candle avaliado, sem ordem enviada."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Decision


@dataclass
class CandleNote:
    open_time: datetime
    signal: str
    close: Decimal
    volume: Decimal
    ema20: Decimal | None
    ema50: Decimal | None
    rsi: Decimal | None
    atr: Decimal | None
    avg_volume: Decimal | None
    price_distance: Decimal | None
    trend_ok: bool
    rsi_ok: bool
    volume_ok: bool
    price_ok: bool
    risk_decision: str | None = None
    risk_reason: str | None = None


def note_from_decision(candle: Candle, snapshot: IndicatorSnapshot, decision: Decision) -> CandleNote:
    passed = {check.code for check in decision.checks if check.passed}
    present = {check.code for check in decision.checks}
    ema20 = snapshot.ema_fast
    distance = None
    if ema20 is not None and ema20 != 0:
        distance = (candle.close - ema20) / ema20
    trend_codes = ("ema50_acima_ema200", "close_4h_acima_ema200", "ema50_subindo")
    price_codes = ("pullback_toca_ema20", "close_acima_ema20", "close_acima_maxima")
    return CandleNote(
        open_time=candle.timestamp,
        signal=decision.signal.value,
        close=candle.close,
        volume=candle.volume,
        ema20=ema20,
        ema50=snapshot.ema50_4h,
        rsi=snapshot.rsi,
        atr=snapshot.atr_4h if snapshot.atr_4h is not None else snapshot.atr,
        avg_volume=snapshot.avg_volume,
        price_distance=distance,
        trend_ok=all(code in passed for code in trend_codes),
        rsi_ok="rsi_na_faixa" in passed,
        volume_ok=True if "volume_acima_media" not in present else "volume_acima_media" in passed,
        price_ok=all(code in passed for code in price_codes),
    )
