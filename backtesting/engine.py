from dataclasses import dataclass
from datetime import date, datetime, timezone
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
    daily_trend_up: list[bool] | None = None

    def at(self, index: int) -> IndicatorSnapshot:
        trend = True if self.daily_trend_up is None else self.daily_trend_up[index]
        return IndicatorSnapshot(
            ema_fast=self.ema_fast[index],
            ema_slow=self.ema_slow[index],
            rsi=self.rsi[index],
            atr=self.atr[index],
            avg_volume=self.avg_volume[index],
            daily_trend_up=trend,
        )


def compute_indicators(candles: list[Candle], settings: Settings) -> IndicatorSeries:
    closes = [candle.close for candle in candles]
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
        daily_trend_up=daily_trend_flags(candles, settings),
    )


def daily_trend_flags(candles: list[Candle], settings: Settings) -> list[bool]:
    """Tendencia do ultimo dia UTC ja fechado. O dia corrente nao entra."""
    days: list[date] = []
    closes: list[Decimal] = []
    for candle in candles:
        day = candle.timestamp.astimezone(timezone.utc).date()
        if not days or days[-1] != day:
            days.append(day)
            closes.append(candle.close)
        else:
            closes[-1] = candle.close
    fast = ema(closes, settings.ema_fast)
    slow = ema(closes, settings.ema_slow)
    usable: bool | None = None
    by_day: dict[date, bool] = {}
    for index, day in enumerate(days):
        by_day[day] = usable is True
        if fast[index] is not None and slow[index] is not None:
            usable = fast[index] > slow[index]
        else:
            usable = None
    return [
        by_day[candle.timestamp.astimezone(timezone.utc).date()]
        for candle in candles
    ]


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
            account = _account(
                broker,
                settings,
                position,
                candle.open,
                day_start,
                realized_today,
            )
            snapshot = series.at(index)
            atr = snapshot.atr if snapshot.atr is not None else Decimal("0")
            verdict = risk.approve_entry(candle.open, atr, account, filters)
            pending_buy = False
            if verdict.accepted and verdict.plan is not None:
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

        snapshot = series.at(index)
        signal = strategy.analyze(candle, snapshot, position is not None)
        if signal is Signal.SELL and position is not None:
            trade = broker.close_long(position, candle.close, candle.timestamp, "trend")
            realized_today += trade.net_pnl
            closed.append(trade)
            position = None
        elif signal is Signal.BUY and position is None and not pending_buy:
            pending_buy = True

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
