from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.config.settings import Settings
from app.market.candles import Candle, IndicatorSnapshot
from app.market.indicators import atr, average_volume, ema, rsi
from app.risk.limits import SymbolFilters
from app.risk.manager import AccountState, RiskManager
from app.strategies.base import Signal, Strategy
from backtesting.broker import BacktestBroker, ClosedTrade, OpenPosition, resolve_intrabar
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
    resistance: list[Decimal | None] | None = None

    def at(self, index: int) -> IndicatorSnapshot:
        trend = False if self.trend_4h is None else self.trend_4h[index]
        previous = None if self.previous_high is None else self.previous_high[index]
        resistance = None if self.resistance is None else self.resistance[index]
        return IndicatorSnapshot(
            ema_fast=self.ema_fast[index],
            ema_slow=self.ema_slow[index],
            rsi=self.rsi[index],
            atr=self.atr[index],
            avg_volume=self.avg_volume[index],
            trend_4h=trend,
            previous_high=previous,
            resistance=resistance,
        )


def compute_indicators(candles: list[Candle], settings: Settings) -> IndicatorSeries:
    closes = [candle.close for candle in candles]
    trend, previous, resistance = four_hour_context(candles, settings)
    return IndicatorSeries(
        ema_fast=ema(closes, settings.ema_fast),
        ema_slow=ema(closes, settings.ema_slow),
        rsi=rsi(closes, settings.rsi_period),
        atr=atr(
            [candle.high for candle in candles],
            [candle.low for candle in candles],
            closes,
            settings.atr_period,
        ),
        avg_volume=average_volume([candle.volume for candle in candles], settings.volume_period),
        trend_4h=trend,
        previous_high=previous,
        resistance=resistance,
    )


def four_hour_context(
    candles: list[Candle],
    settings: Settings,
) -> tuple[list[bool], list[Decimal | None], list[Decimal | None]]:
    """Tendencia e resistencia do ultimo candle de 4h ja fechado."""
    buckets: list[datetime] = []
    closes: list[Decimal] = []
    highs: list[Decimal] = []
    index_of: dict[datetime, int] = {}
    for candle in candles:
        bucket = _four_hour_open(candle.timestamp)
        if bucket not in index_of:
            index_of[bucket] = len(buckets)
            buckets.append(bucket)
            closes.append(candle.close)
            highs.append(candle.high)
        else:
            closes[-1] = candle.close
            highs[-1] = max(highs[-1], candle.high)
    ema50 = ema(closes, settings.ema_trend)
    ema200 = ema(closes, settings.ema_trend_slow)
    lookback = settings.ema_slope_lookback
    trend_flags: list[bool] = []
    resistances: list[Decimal | None] = []
    previous = [None, *[candle.high for candle in candles[:-1]]]
    for candle in candles:
        completed = _completed_four_hour_index(candle.timestamp, index_of)
        if completed is None:
            trend_flags.append(False)
            resistances.append(None)
            continue
        fast = ema50[completed]
        slow = ema200[completed]
        earlier = ema50[completed - lookback] if completed >= lookback else None
        close = closes[completed]
        trend_flags.append(
            fast is not None
            and slow is not None
            and earlier is not None
            and fast > slow
            and close > slow
            and fast > earlier
        )
        if completed + 1 < 20:
            resistances.append(None)
        else:
            resistances.append(max(highs[completed - 19 : completed + 1]))
    return trend_flags, previous, resistances


def _four_hour_open(timestamp: datetime) -> datetime:
    moment = timestamp.astimezone(timezone.utc)
    hour = moment.hour - (moment.hour % 4)
    return moment.replace(hour=hour, minute=0, second=0, microsecond=0)


def _completed_four_hour_index(timestamp: datetime, index_of: dict[datetime, int]) -> int | None:
    moment = timestamp.astimezone(timezone.utc)
    bucket = _four_hour_open(moment)
    if moment.hour % 4 == 3:
        return index_of[bucket]
    previous = bucket - timedelta(hours=4)
    return index_of.get(previous)


def run_backtest(
    candles: list[Candle],
    strategy: Strategy,
    settings: Settings,
    *,
    symbol: str,
    indicators: IndicatorSeries | None = None,
    trade_from: datetime | None = None,
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
    pending_resistance: Decimal | None = None
    cooldown_until: datetime | None = None
    closed: list[ClosedTrade] = []
    equity: list[Decimal] = []
    day: date | None = None
    day_start = settings.capital
    realized_today = Decimal("0")

    for index, candle in enumerate(candles):
        if trade_from is not None and candle.timestamp < trade_from:
            continue
        candle_day = candle.timestamp.date()
        if day != candle_day:
            day = candle_day
            day_start = broker.equity(position, candle.open)
            realized_today = Decimal("0")

        if pending_buy and position is None:
            cooled = cooldown_until is not None and candle.timestamp < cooldown_until
            room_ok = (
                pending_resistance is None
                or pending_resistance >= candle.open * (Decimal(1) + settings.stop_pct * settings.reward_multiple)
            )
            account = _account(
                broker,
                settings,
                position,
                candle.open,
                day_start,
                realized_today,
            )
            snapshot = series.at(index)
            atr_value = snapshot.atr if snapshot.atr is not None else Decimal("0")
            verdict = risk.approve_entry(candle.open, atr_value, account, filters)
            pending_buy = False
            pending_resistance = None
            if not cooled and room_ok and verdict.accepted and verdict.plan is not None:
                position, _order = broker.open_long(
                    candle.open,
                    verdict.plan.quantity,
                    verdict.plan.stop,
                    verdict.plan.take_profit,
                    candle.timestamp,
                )

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

        snapshot = series.at(index)
        signal = strategy.analyze(candle, snapshot, position is not None)
        cooled = cooldown_until is not None and candle.timestamp < cooldown_until
        if signal is Signal.SELL and position is not None:
            trade = broker.close_long(position, candle.close, candle.timestamp, "trend")
            realized_today += trade.net_pnl
            closed.append(trade)
            position = None
        elif signal is Signal.BUY and position is None and not pending_buy and not cooled:
            pending_buy = True
            pending_resistance = snapshot.resistance

        equity.append(broker.equity(position, candle.close))

    traded = [candle for candle in candles if trade_from is None or candle.timestamp >= trade_from]
    return build_report(
        symbol=symbol,
        timeframe=settings.timeframe,
        start=traded[0].timestamp if traded else None,
        end=traded[-1].timestamp if traded else None,
        initial_capital=settings.capital,
        trades=closed,
        equity=equity,
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
