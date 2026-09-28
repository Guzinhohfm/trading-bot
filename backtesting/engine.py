from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.config.settings import Settings
from app.market.candles import Candle, IndicatorSnapshot
from app.paper.records import note_from_decision
from app.market.indicators import atr, average_volume, ema, rsi
from app.risk.limits import SymbolFilters
from app.risk.manager import AccountState, RiskManager
from app.strategies.base import Signal, Strategy
from backtesting.broker import BacktestBroker, ClosedTrade, OpenPosition, TradeNote, resolve_intrabar
from backtesting.metrics import BacktestReport, build_report


@dataclass(frozen=True)
class IndicatorSeries:
    ema_fast: list[Decimal | None]
    ema_slow: list[Decimal | None]
    rsi: list[Decimal | None]
    atr: list[Decimal | None]
    avg_volume: list[Decimal | None]
    trend_4h: list[bool] | None = None
    previous_high: list[Decimal | None] | None = None
    previous_low: list[Decimal | None] | None = None
    previous_ema20: list[Decimal | None] | None = None
    ema50_4h: list[Decimal | None] | None = None
    ema200_4h: list[Decimal | None] | None = None
    close_4h: list[Decimal | None] | None = None
    ema50_4h_prior: list[Decimal | None] | None = None
    resistance: list[Decimal | None] | None = None
    previous_rsi: list[Decimal | None] | None = None
    atr_4h: list[Decimal | None] | None = None
    trend_daily: list[bool] | None = None

    def at(self, index: int) -> IndicatorSnapshot:
        trend = False if self.trend_4h is None else self.trend_4h[index]
        previous = None if self.previous_high is None else self.previous_high[index]
        return IndicatorSnapshot(
            ema_fast=self.ema_fast[index],
            ema_slow=self.ema_slow[index],
            rsi=self.rsi[index],
            atr=self.atr[index],
            avg_volume=self.avg_volume[index],
            trend_4h=trend,
            previous_high=previous,
            previous_low=_at(self.previous_low, index),
            previous_ema20=_at(self.previous_ema20, index),
            ema50_4h=_at(self.ema50_4h, index),
            ema200_4h=_at(self.ema200_4h, index),
            close_4h=_at(self.close_4h, index),
            ema50_4h_prior=_at(self.ema50_4h_prior, index),
            resistance=_at(self.resistance, index),
            previous_rsi=_at(self.previous_rsi, index),
            atr_4h=_at(self.atr_4h, index),
            trend_daily=False if self.trend_daily is None else self.trend_daily[index],
        )


def compute_indicators(candles: list[Candle], settings: Settings) -> IndicatorSeries:
    closes = [candle.close for candle in candles]
    context = four_hour_context(candles, settings)
    ema_fast = ema(closes, settings.ema_fast)
    rsi_values = rsi(closes, settings.rsi_period)
    return IndicatorSeries(
        ema_fast=ema_fast,
        ema_slow=ema(closes, settings.ema_slow),
        rsi=rsi_values,
        atr=atr(
            [candle.high for candle in candles],
            [candle.low for candle in candles],
            closes,
            settings.atr_period,
        ),
        avg_volume=average_volume([candle.volume for candle in candles], settings.volume_period),
        trend_4h=context.trend,
        previous_high=context.previous_high,
        previous_low=[None, *[candle.low for candle in candles[:-1]]],
        previous_ema20=[None, *ema_fast[:-1]],
        ema50_4h=context.ema50,
        ema200_4h=context.ema200,
        close_4h=context.close,
        ema50_4h_prior=context.ema50_prior,
        resistance=context.resistance,
        previous_rsi=[None, *rsi_values[:-1]],
        atr_4h=context.atr,
        trend_daily=four_hour_context(candles, settings.model_copy(update={"trend_hours": 24})).trend,
    )


@dataclass(frozen=True)
class FourHourContext:
    trend: list[bool]
    previous_high: list[Decimal | None]
    ema50: list[Decimal | None]
    ema200: list[Decimal | None]
    close: list[Decimal | None]
    ema50_prior: list[Decimal | None]
    resistance: list[Decimal | None]
    atr: list[Decimal | None]


def four_hour_context(candles: list[Candle], settings: Settings) -> FourHourContext:
    """Leitura do ultimo candle de 4h ja fechado, uma linha por candle de entrada."""
    buckets: list[datetime] = []
    closes: list[Decimal] = []
    highs: list[Decimal] = []
    lows: list[Decimal] = []
    index_of: dict[datetime, int] = {}
    for candle in candles:
        bucket = _four_hour_open(candle.timestamp, settings.trend_hours)
        if bucket not in index_of:
            index_of[bucket] = len(buckets)
            buckets.append(bucket)
            closes.append(candle.close)
            highs.append(candle.high)
            lows.append(candle.low)
        else:
            closes[-1] = candle.close
            highs[-1] = max(highs[-1], candle.high)
            lows[-1] = min(lows[-1], candle.low)
    ema50 = ema(closes, settings.ema_trend)
    ema200 = ema(closes, settings.ema_trend_slow)
    atr_4h = atr(highs, lows, closes, settings.atr_period)
    lookback = settings.ema_slope_lookback
    trend_flags: list[bool] = []
    ema50_values: list[Decimal | None] = []
    ema200_values: list[Decimal | None] = []
    close_values: list[Decimal | None] = []
    prior_values: list[Decimal | None] = []
    resistance_values: list[Decimal | None] = []
    atr_values: list[Decimal | None] = []
    previous = [None, *[candle.high for candle in candles[:-1]]]
    for candle in candles:
        completed = _completed_four_hour_index(candle.timestamp, index_of, settings.trend_hours)
        if completed is None:
            trend_flags.append(False)
            ema50_values.append(None)
            ema200_values.append(None)
            close_values.append(None)
            prior_values.append(None)
            resistance_values.append(None)
            atr_values.append(None)
            continue
        fast = ema50[completed]
        slow = ema200[completed]
        earlier = ema50[completed - lookback] if completed >= lookback else None
        close = closes[completed]
        ema50_values.append(fast)
        ema200_values.append(slow)
        close_values.append(close)
        prior_values.append(earlier)
        if completed + 1 < 20:
            resistance_values.append(None)
        else:
            resistance_values.append(max(highs[completed - 19 : completed + 1]))
        atr_values.append(atr_4h[completed])
        trend_flags.append(
            fast is not None
            and slow is not None
            and earlier is not None
            and fast > slow
            and close > slow
            and fast > earlier
        )
    return FourHourContext(
        trend_flags,
        previous,
        ema50_values,
        ema200_values,
        close_values,
        prior_values,
        resistance_values,
        atr_values,
    )


def _four_hour_open(timestamp: datetime, hours: int = 4) -> datetime:
    moment = timestamp.astimezone(timezone.utc)
    if hours >= 24:
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)
    hour = moment.hour - (moment.hour % hours)
    return moment.replace(hour=hour, minute=0, second=0, microsecond=0)


def _completed_four_hour_index(
    timestamp: datetime,
    index_of: dict[datetime, int],
    hours: int = 4,
) -> int | None:
    moment = timestamp.astimezone(timezone.utc)
    bucket = _four_hour_open(moment, hours)
    closing_hour = (bucket.hour + hours - 1) % 24
    if moment.hour == closing_hour:
        return index_of[bucket]
    previous = bucket - timedelta(hours=hours)
    return index_of.get(previous)


def run_backtest(
    candles: list[Candle],
    strategy: Strategy,
    settings: Settings,
    *,
    symbol: str,
    indicators: IndicatorSeries | None = None,
    trade_from: datetime | None = None,
    journal: list | None = None,
) -> BacktestReport:
    series = indicators or compute_indicators(candles, settings)
    risk = RiskManager(settings)
    broker = BacktestBroker(settings.capital, settings)
    filters = SymbolFilters(
        tick_size=settings.tick_size,
        step_size=settings.step_size,
        min_qty=settings.min_qty,
        min_notional=settings.min_notional,
    )
    position: OpenPosition | None = None
    pending_buy = False
    cooldown_until: datetime | None = None
    closed: list[ClosedTrade] = []
    equity: list[Decimal] = []
    day: date | None = None
    day_start = settings.capital
    realized_today = Decimal("0")
    explain = getattr(strategy, "explain", None)
    failures: dict[str, int] = {}
    funnel = {name: 0 for name, _codes in _FUNNEL}
    candles_seen = 0
    buy_signals = 0
    entries_opened = 0
    pending_snapshot: IndicatorSnapshot | None = None
    peak = settings.capital

    for index, candle in enumerate(candles):
        if trade_from is not None and candle.timestamp < trade_from:
            continue
        candle_day = candle.timestamp.date()
        if day != candle_day:
            day = candle_day
            day_start = broker.equity(position, candle.open)
            realized_today = Decimal("0")

        snapshot = series.at(index)
        if pending_buy and position is None:
            cooled = cooldown_until is not None and candle.timestamp < cooldown_until
            account = _account(
                broker,
                settings,
                position,
                candle.open,
                day_start,
                realized_today,
            )
            atr_value = snapshot.atr if snapshot.atr is not None else Decimal("0")
            verdict = risk.approve_entry(candle.open, atr_value, account, filters)
            saved = pending_snapshot
            pending_snapshot = None
            pending_buy = False
            if cooled:
                if journal:
                    journal[-1].risk_decision = "rejected"
                    journal[-1].risk_reason = "cooldown"
                if explain is not None:
                    _bump(failures, "cooldown")
            elif verdict.accepted and verdict.plan is not None:
                if journal:
                    journal[-1].risk_decision = "accepted"
                    journal[-1].risk_reason = "accepted"
                cash = broker.cash
                drawdown = (peak - cash) / peak if peak > 0 and cash < peak else Decimal("0")
                position, _order = broker.open_long(
                    candle.open,
                    verdict.plan.quantity,
                    verdict.plan.stop,
                    verdict.plan.take_profit,
                    candle.timestamp,
                    _planned_risk(verdict.plan),
                    _trade_note(saved, candle, drawdown),
                )
                entries_opened += 1
            elif explain is not None:
                if journal:
                    journal[-1].risk_decision = "rejected"
                    journal[-1].risk_reason = verdict.reason
                _bump(failures, verdict.reason)

        if position is not None:
            exit_fill = resolve_intrabar(
                candle.open,
                candle.high,
                candle.low,
                position.stop,
                position.take_profit,
            )
            if exit_fill is not None:
                price, reason = exit_fill
                trade = broker.close_long(position, price, candle.timestamp, reason)
                realized_today += trade.net_pnl
                closed.append(trade)
                position = None
                if reason == "stop":
                    cooldown_until = candle.timestamp + timedelta(hours=settings.cooldown_hours)

        cooled = cooldown_until is not None and candle.timestamp < cooldown_until
        if explain is not None:
            candles_seen += 1
            decision = explain(candle, snapshot, position is not None)
            signal = decision.signal
            for code in decision.failed:
                _bump(failures, code)
            _advance_funnel(funnel, decision)
            if journal is not None:
                journal.append(note_from_decision(candle, snapshot, decision))
        else:
            signal = strategy.analyze(candle, snapshot, position is not None)
        if signal is Signal.SELL and position is not None:
            trade = broker.close_long(position, candle.close, candle.timestamp, "trend")
            realized_today += trade.net_pnl
            closed.append(trade)
            position = None
        elif signal is Signal.BUY:
            if explain is not None:
                buy_signals += 1
            if position is not None:
                if explain is not None:
                    _bump(failures, "posicao_aberta")
            elif cooled:
                if explain is not None:
                    _bump(failures, "cooldown")
            elif not pending_buy:
                pending_buy = True
                pending_snapshot = snapshot

        marked = broker.equity(position, candle.close)
        equity.append(marked)
        if marked > peak:
            peak = marked

    traded = [candle for candle in candles if trade_from is None or candle.timestamp >= trade_from]
    return build_report(
        symbol=symbol,
        timeframe=settings.timeframe,
        start=traded[0].timestamp if traded else None,
        end=traded[-1].timestamp if traded else None,
        initial_capital=settings.capital,
        trades=closed,
        equity=equity,
        candles_seen=candles_seen,
        buy_signals=buy_signals,
        closed_trades=tuple(closed),
        rule_failures=_ordered_failures(failures),
        funnel=_funnel_rows(funnel, entries_opened, candles_seen),
    )


_FUNNEL = (
    ("trend_4h", ("ema50_acima_ema200", "close_4h_acima_ema200", "ema50_subindo")),
    ("pullback", ("pullback_toca_ema20",)),
    ("rsi", ("rsi_na_faixa",)),
    ("recovery", ("close_acima_ema20", "close_acima_maxima")),
)


def _advance_funnel(funnel: dict[str, int], decision) -> None:
    passed = {check.code for check in decision.checks if check.passed}
    present = {check.code for check in decision.checks}
    recovery = tuple(
        code
        for code in ("close_acima_ema20", "candle_positivo", "close_acima_maxima")
        if code in present
    )
    stages = [
        ("trend_4h", ("ema50_acima_ema200", "close_4h_acima_ema200", "ema50_subindo")),
        ("pullback", ("pullback_toca_ema20",)),
        ("rsi", ("rsi_na_faixa",)),
        ("recovery", recovery),
    ]
    if "volume_acima_media" in present:
        funnel.setdefault("volume", 0)
        stages.append(("volume", ("volume_acima_media",)))
    if "espaco_ate_alvo" in present:
        funnel.setdefault("resistance", 0)
        stages.append(("resistance", ("espaco_ate_alvo",)))
    for name, codes in stages:
        if not codes or not all(code in passed for code in codes):
            return
        funnel[name] += 1


def _funnel_rows(funnel: dict[str, int], entries: int, candles_seen: int) -> tuple[tuple[str, int], ...]:
    if candles_seen == 0 and entries == 0:
        return ()
    rows = [(name, funnel[name]) for name, _codes in _FUNNEL]
    if "volume" in funnel:
        rows.append(("volume", funnel["volume"]))
    if "resistance" in funnel:
        rows.append(("resistance", funnel["resistance"]))
    rows.append(("entries", entries))
    return tuple(rows)


def _trade_note(snapshot: IndicatorSnapshot | None, candle: Candle, drawdown: Decimal) -> TradeNote | None:
    if snapshot is None:
        return None
    return TradeNote(
        rsi=snapshot.rsi,
        rsi_previous=snapshot.previous_rsi,
        ema_separation=_change(snapshot.ema50_4h, snapshot.ema200_4h),
        ema_slope=_change(snapshot.ema50_4h, snapshot.ema50_4h_prior),
        atr_pct=_share(snapshot.atr_4h, snapshot.close_4h),
        drawdown=drawdown,
        hour=candle.timestamp.astimezone(timezone.utc).hour,
    )


def _change(current: Decimal | None, base: Decimal | None) -> Decimal | None:
    if current is None or base is None or base == 0:
        return None
    return (current - base) / base


def _share(part: Decimal | None, whole: Decimal | None) -> Decimal | None:
    if part is None or whole is None or whole == 0:
        return None
    return part / whole


def _planned_risk(plan) -> Decimal:
    if plan.entry <= 0:
        return Decimal("0")
    return (plan.entry - plan.stop) / plan.entry * plan.position_size


def _at(values: list[Decimal | None] | None, index: int) -> Decimal | None:
    if values is None:
        return None
    return values[index]


def _bump(failures: dict[str, int], code: str) -> None:
    failures[code] = failures.get(code, 0) + 1


def _ordered_failures(failures: dict[str, int]) -> tuple[tuple[str, int], ...]:
    ordered = [code for code in _FAILURE_ORDER if failures.get(code)]
    ordered.extend(code for code in failures if code not in _FAILURE_ORDER and failures[code])
    return tuple((code, failures[code]) for code in ordered)


_FAILURE_ORDER = (
    "ema50_acima_ema200",
    "close_4h_acima_ema200",
    "ema50_subindo",
    "tendencia_diaria",
    "pullback_toca_ema20",
    "rsi_na_faixa",
    "close_acima_ema20",
    "candle_positivo",
    "close_acima_maxima",
    "separacao_ema",
    "inclinacao_minima",
    "rsi_subindo",
    "fechamento_no_topo",
    "atr_na_faixa",
    "volume_acima_media",
    "espaco_ate_alvo",
    "posicao_aberta",
    "cooldown",
    "daily_loss",
    "daily_profit",
    "kill_switch",
    "no_capital",
    "invalid_stop",
)


def _account(
    broker: BacktestBroker,
    settings: Settings,
    position: OpenPosition | None,
    mark: Decimal,
    day_start: Decimal,
    realized_today: Decimal,
) -> AccountState:
    unrealized = Decimal("0")
    if position is not None:
        unrealized = (mark - position.entry_effective) * position.quantity
    return AccountState(
        capital=settings.capital,
        available_capital=broker.cash,
        daily_pnl=realized_today + unrealized,
        day_start_equity=day_start,
        position_open=position is not None,
        kill_switch=False,
    )
