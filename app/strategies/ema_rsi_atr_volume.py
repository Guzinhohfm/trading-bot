from decimal import Decimal

from app.config.settings import Settings, get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Decision, RuleCheck, Signal


class EmaRsiAtrVolumeStrategy:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position_open: bool,
    ) -> Signal:
        return self.explain(candle, indicators, position_open).signal

    def explain(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position_open: bool,
    ) -> Decision:
        del position_open
        checks = self._checks(candle, indicators)
        signal = Signal.BUY if all(check.passed for check in checks) else Signal.HOLD
        return Decision(signal, checks)

    def _checks(self, candle: Candle, indicators: IndicatorSnapshot) -> tuple[RuleCheck, ...]:
        settings = self.settings
        ema20 = indicators.ema_fast
        ema50 = indicators.ema50_4h
        ema200 = indicators.ema200_4h
        above_ema = ema20 is not None and ema20 != 0 and candle.close > ema20
        rsi_ok = (
            indicators.rsi is not None and settings.rsi_min <= indicators.rsi <= settings.rsi_max
        )
        return (
            RuleCheck("ema50_acima_ema200", _above(ema50, ema200)),
            RuleCheck("close_4h_acima_ema200", _above(indicators.close_4h, ema200)),
            RuleCheck("ema50_subindo", _above(ema50, indicators.ema50_4h_prior)),
            RuleCheck("pullback_toca_ema20", _touched(indicators.previous_low, indicators.previous_ema20)),
            RuleCheck("rsi_na_faixa", rsi_ok),
            *_trigger_checks(candle, indicators, above_ema, settings.entry_trigger),
            *_volume_checks(candle, indicators, settings),
            *_resistance_checks(candle, indicators, settings),
            *_regime_checks(candle, indicators, settings),
        )


def _above(left: Decimal | None, right: Decimal | None) -> bool:
    return left is not None and right is not None and left > right


def _touched(low: Decimal | None, ema: Decimal | None) -> bool:
    return low is not None and ema is not None and low <= ema


def _trigger_checks(
    candle: Candle,
    indicators: IndicatorSnapshot,
    above_ema: bool,
    trigger: str,
) -> tuple[RuleCheck, ...]:
    above = RuleCheck("close_acima_ema20", above_ema)
    if trigger == "ema20":
        return (above,)
    if trigger == "bullish":
        return (above, RuleCheck("candle_positivo", candle.close > candle.open))
    if trigger != "previous_high":
        raise ValueError(f"Gatilho desconhecido: {trigger}")
    broke_high = indicators.previous_high is not None and candle.close > indicators.previous_high
    return (above, RuleCheck("close_acima_maxima", broke_high))


def _volume_checks(candle: Candle, indicators: IndicatorSnapshot, settings: Settings) -> tuple[RuleCheck, ...]:
    if not settings.require_volume:
        return ()
    average = indicators.avg_volume
    passed = average is not None and candle.volume >= average * settings.volume_factor
    return (RuleCheck("volume_acima_media", passed),)


def _regime_checks(candle: Candle, indicators: IndicatorSnapshot, settings: Settings) -> tuple[RuleCheck, ...]:
    checks: list[RuleCheck] = []
    if settings.require_daily_trend:
        checks.append(RuleCheck("tendencia_diaria", indicators.trend_daily))
    if settings.trend_separation_min > 0:
        gap = _ratio_change(indicators.ema50_4h, indicators.ema200_4h)
        checks.append(RuleCheck("separacao_ema", gap is not None and gap >= settings.trend_separation_min))
    if settings.ema_slope_min > 0:
        slope = _ratio_change(indicators.ema50_4h, indicators.ema50_4h_prior)
        checks.append(RuleCheck("inclinacao_minima", slope is not None and slope >= settings.ema_slope_min))
    if settings.require_rsi_rising:
        rising = (
            indicators.rsi is not None
            and indicators.previous_rsi is not None
            and indicators.rsi > indicators.previous_rsi
        )
        checks.append(RuleCheck("rsi_subindo", rising))
    quality = _candle_quality_check(candle, settings.candle_quality)
    if quality is not None:
        checks.append(quality)
    if settings.atr_pct_min is not None or settings.atr_pct_max is not None:
        atr_pct = _share(indicators.atr_4h, indicators.close_4h)
        low_ok = settings.atr_pct_min is None or (atr_pct is not None and atr_pct >= settings.atr_pct_min)
        high_ok = settings.atr_pct_max is None or (atr_pct is not None and atr_pct <= settings.atr_pct_max)
        checks.append(RuleCheck("atr_na_faixa", atr_pct is not None and low_ok and high_ok))
    return tuple(checks)


def _candle_quality_check(candle: Candle, mode: str) -> RuleCheck | None:
    if mode == "off":
        return None
    if mode == "positive":
        return RuleCheck("candle_positivo", candle.close > candle.open)
    limits = {"top30": Decimal("0.30"), "top20": Decimal("0.20")}
    if mode not in limits:
        raise ValueError(f"Qualidade de candle desconhecida: {mode}")
    span = candle.high - candle.low
    upper = (candle.high - candle.close) / span if span > 0 else None
    return RuleCheck("fechamento_no_topo", upper is not None and upper <= limits[mode])


def _ratio_change(current: Decimal | None, base: Decimal | None) -> Decimal | None:
    if current is None or base is None or base == 0:
        return None
    return (current - base) / base


def _share(part: Decimal | None, whole: Decimal | None) -> Decimal | None:
    if part is None or whole is None or whole == 0:
        return None
    return part / whole


def _resistance_checks(candle: Candle, indicators: IndicatorSnapshot, settings: Settings) -> tuple[RuleCheck, ...]:
    if not settings.require_resistance:
        return ()
    room = candle.close * (Decimal(1) + settings.stop_pct * settings.reward_multiple)
    resistance = indicators.resistance
    passed = resistance is not None and resistance >= room
    return (RuleCheck("espaco_ate_alvo", passed),)
