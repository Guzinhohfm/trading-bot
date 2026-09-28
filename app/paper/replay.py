"""Paper local: o mesmo backtest, com o gateway de ordem desligado."""

from datetime import datetime

from app.config.settings import Settings
from app.execution.gateway import DisabledGateway
from app.strategies.base import Strategy
from backtesting.engine import IndicatorSeries, run_backtest
from backtesting.metrics import BacktestReport
from app.market.candles import Candle


def run_paper(
    candles: list[Candle],
    strategy: Strategy,
    settings: Settings,
    *,
    symbol: str,
    indicators: IndicatorSeries | None = None,
    trade_from: datetime | None = None,
    journal: list | None = None,
) -> BacktestReport:
    gateway = DisabledGateway()
    del gateway
    return run_backtest(
        candles,
        strategy,
        settings,
        symbol=symbol,
        indicators=indicators,
        trade_from=trade_from,
        journal=journal,
    )
