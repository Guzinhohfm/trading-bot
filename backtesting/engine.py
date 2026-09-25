from dataclasses import dataclass
from datetime import date, datetime
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

    def at(self, index: int) -> IndicatorSnapshot:
        return IndicatorSnapshot(
            ema_fast=self.ema_fast[index],
            ema_slow=self.ema_slow[index],
            rsi=self.rsi[index],
            atr=self.atr[index],
            avg_volume=self.avg_volume[index],
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
    )


def run_backtest(
    candles: list[Candle],
    strategy: Strategy,
    settings: Settings,
    *,
    symbol: str,
    indicators: IndicatorSeries | None = None,
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
    pending_atr: Decimal | None = None
    closed: list[ClosedTrade] = []
    equity: list[Decimal] = []
    day: date | None = None
    day_start = settings.capital
    realized_today = Decimal("0")

    for index, candle in enumerate(candles):
        candle_day = candle.timestamp.date()
        if day != candle_day:
            day = candle_day
            day_start = broker.equity(position, candle.open)
            realized_today = Decimal("0")

        if pending_atr is not None and position is None:
            account = _account(
                broker,
                settings,
                position,
                candle.open,
                day_start,
                realized_today,
            )
            verdict = risk.approve_entry(candle.open, pending_atr, account, filters)
            pending_atr = None
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
        elif signal is Signal.BUY and position is None and pending_atr is None and snapshot.atr is not None:
            pending_atr = snapshot.atr

        equity.append(broker.equity(position, candle.close))

    return build_report(
        symbol=symbol,
        timeframe=settings.timeframe,
        start=candles[0].timestamp if candles else None,
        end=candles[-1].timestamp if candles else None,
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
