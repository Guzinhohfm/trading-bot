from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from backtesting.broker import ClosedTrade


@dataclass(frozen=True)
class BacktestReport:
    symbol: str
    timeframe: str
    start: datetime | None
    end: datetime | None
    initial_capital: Decimal
    trades: int
    wins: int
    losses: int
    win_rate: Decimal
    gross_pnl: Decimal
    fees: Decimal
    slippage: Decimal
    net_pnl: Decimal
    total_return: Decimal
    max_drawdown: Decimal
    profit_factor: Decimal | None
    avg_trade: Decimal
    avg_winner: Decimal
    avg_loser: Decimal
    expectancy: Decimal


def max_drawdown(equity: list[Decimal]) -> Decimal:
    if not equity:
        return Decimal("0")
    peak = equity[0]
    worst = Decimal("0")
    for value in equity:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak
            if drawdown > worst:
                worst = drawdown
    return worst


def profit_factor(trades: list[ClosedTrade]) -> Decimal | None:
    gross_profit = sum((trade.gross_pnl for trade in trades if trade.gross_pnl > 0), Decimal("0"))
    gross_loss = sum((trade.gross_pnl for trade in trades if trade.gross_pnl < 0), Decimal("0"))
    if gross_loss == 0:
        return None
    return gross_profit / abs(gross_loss)


def build_report(
    *,
    symbol: str,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    initial_capital: Decimal,
    trades: list[ClosedTrade],
    equity: list[Decimal],
) -> BacktestReport:
    wins = [trade for trade in trades if trade.net_pnl > 0]
    losses = [trade for trade in trades if trade.net_pnl < 0]
    count = len(trades)
    gross = sum((trade.gross_pnl for trade in trades), Decimal("0"))
    fees = sum((trade.fees for trade in trades), Decimal("0"))
    slippage = sum((trade.slippage for trade in trades), Decimal("0"))
    net = sum((trade.net_pnl for trade in trades), Decimal("0"))
    avg_winner = _mean(trade.net_pnl for trade in wins)
    avg_loser = _mean(-trade.net_pnl for trade in losses)
    win_rate = (Decimal(len(wins)) / Decimal(count)) if count else Decimal("0")
    loss_rate = (Decimal(len(losses)) / Decimal(count)) if count else Decimal("0")
    avg_trade = (net / Decimal(count)) if count else Decimal("0")
    expectancy = win_rate * avg_winner - loss_rate * avg_loser
    total_return = (net / initial_capital) if initial_capital else Decimal("0")
    return BacktestReport(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        initial_capital=initial_capital,
        trades=count,
        wins=len(wins),
        losses=len(losses),
        win_rate=win_rate,
        gross_pnl=gross,
        fees=fees,
        slippage=slippage,
        net_pnl=net,
        total_return=total_return,
        max_drawdown=max_drawdown(equity if equity else [initial_capital]),
        profit_factor=profit_factor(trades),
        avg_trade=avg_trade,
        avg_winner=avg_winner,
        avg_loser=avg_loser,
        expectancy=expectancy,
    )


def format_report(report: BacktestReport) -> str:
    period = _period(report.start, report.end)
    factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
    lines = [
        "══════════════════════════════════",
        "       BACKTEST — STRATEGY V1",
        "══════════════════════════════════",
        f"Ativo:             {report.symbol}",
        f"Timeframe:         {report.timeframe}",
        f"Período:           {period}",
        "",
        f"Capital inicial:   {_money(report.initial_capital)}",
        "",
        f"Trades:            {report.trades}",
        f"Wins:              {report.wins}",
        f"Losses:            {report.losses}",
        "",
        f"Win Rate:          {_pct(report.win_rate)}",
        "",
        f"Gross P&L:         {_money(report.gross_pnl)}",
        f"Fees:              {_money(report.fees)}",
        f"Slippage:          {_money(report.slippage)}",
        "",
        f"Net P&L:           {_money(report.net_pnl)}",
        "",
        f"Return:            {_pct(report.total_return)}",
        "",
        f"Max Drawdown:      {_pct(report.max_drawdown)}",
        "",
        f"Profit Factor:     {factor}",
        "",
        f"Avg Trade:         {_money(report.avg_trade)}",
        "",
        f"Avg Winner:        {_money(report.avg_winner)}",
        f"Avg Loser:         {_money(report.avg_loser)}",
        f"Expectancy:        {_money(report.expectancy)}",
        "══════════════════════════════════",
    ]
    return "\n".join(lines)


def _mean(values) -> Decimal:
    items = list(values)
    if not items:
        return Decimal("0")
    return sum(items, Decimal("0")) / Decimal(len(items))


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _pct(value: Decimal) -> str:
    return f"{(value * Decimal(100)).quantize(Decimal('0.01'))}%"


def _period(start: datetime | None, end: datetime | None) -> str:
    if start is None or end is None:
        return "-"
    return f"{start:%d/%m/%Y} → {end:%d/%m/%Y}"
