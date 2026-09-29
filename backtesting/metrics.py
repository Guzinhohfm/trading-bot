from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from backtesting.broker import ClosedTrade, OpenPosition


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
    max_loss_streak: int
    candles_seen: int = 0
    buy_signals: int = 0
    rule_failures: tuple[tuple[str, int], ...] = ()
    funnel: tuple[tuple[str, int], ...] = ()
    planned_risk: Decimal = Decimal("0")
    realized_loss: Decimal = Decimal("0")
    gap_loss: Decimal = Decimal("0")
    closed_trades: tuple[ClosedTrade, ...] = ()
    open_position: OpenPosition | None = None


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
    candles_seen: int = 0,
    buy_signals: int = 0,
    rule_failures: tuple[tuple[str, int], ...] = (),
    funnel: tuple[tuple[str, int], ...] = (),
    closed_trades: tuple[ClosedTrade, ...] = (),
    open_position: OpenPosition | None = None,
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
        max_loss_streak=_loss_streak(trades),
        candles_seen=candles_seen,
        buy_signals=buy_signals,
        rule_failures=rule_failures,
        closed_trades=closed_trades,
        open_position=open_position,
        funnel=funnel,
        planned_risk=sum((trade.planned_risk for trade in trades), Decimal("0")),
        realized_loss=sum((-trade.net_pnl for trade in trades if trade.net_pnl < 0), Decimal("0")),
        gap_loss=sum((trade.gap_loss for trade in trades), Decimal("0")),
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
        f"Risco planejado:   {_money(report.planned_risk)}",
        f"Perda realizada:   {_money(report.realized_loss)}",
        f"Gap:               {_money(report.gap_loss)}",
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
        f"Maior sequencia:   {report.max_loss_streak} perdas",
        *_rule_lines(report),
        *_funnel_lines(report),
        "══════════════════════════════════",
    ]
    return "\n".join(lines)


_RULE_LABELS = {
    "ema50_acima_ema200": "EMA50 > EMA200",
    "close_4h_acima_ema200": "Close 4h > EMA200",
    "ema50_subindo": "EMA50 subindo",
    "pullback_toca_ema20": "Candle anterior tocou a EMA20",
    "rsi_na_faixa": "RSI 40–55",
    "close_acima_ema20": "Close > EMA20",
    "candle_positivo": "Candle positivo",
    "close_acima_maxima": "Close > máxima anterior",
    "volume_acima_media": "Volume >= 110% da média",
    "espaco_ate_alvo": "Espaço até o alvo de 10%",
    "posicao_aberta": "Posição aberta",
    "cooldown": "Cooldown",
    "daily_loss": "Perda diária",
    "daily_profit": "Meta diária",
    "kill_switch": "Kill switch",
    "no_capital": "Sem capital",
    "invalid_stop": "Stop inválido",
}


_FUNNEL_LABELS = {
    "trend_4h": "Tendência 4h",
    "pullback": "Pullback",
    "rsi": "RSI 40–55",
    "recovery": "Recuperação",
    "volume": "Volume >= 110% da média",
    "resistance": "Espaço até o alvo de 10%",
    "entries": "Risco aceitou",
}


def _funnel_lines(report: BacktestReport) -> list[str]:
    if not report.candles_seen and not report.funnel:
        return []
    lines = ["", "Funil", f"  {'Candles 1h':<24} {report.candles_seen}"]
    for code, count in report.funnel:
        label = _FUNNEL_LABELS.get(code, code)
        lines.append(f"  {label:<24} {count}")
    lines.append(f"  {'Trades':<24} {report.trades}")
    present = {code for code, _count in report.funnel}
    skipped = []
    if "volume" not in present:
        skipped.append("Volume")
    if "resistance" not in present:
        skipped.append("Resistência")
    if len(skipped) == 1:
        lines.append(f"  {skipped[0]} não filtra esta versão.")
    elif skipped:
        lines.append(f"  {' e '.join(skipped)} não filtram esta versão.")
    return lines


def _rule_lines(report: BacktestReport) -> list[str]:
    if not report.candles_seen and not report.rule_failures:
        return []
    lines = [
        "",
        f"Candles lidos:     {report.candles_seen}",
        f"Sinais BUY:        {report.buy_signals}",
    ]
    if report.rule_failures:
        lines.append("")
        lines.append("Condições que falharam:")
        for code, count in report.rule_failures:
            label = _RULE_LABELS.get(code, code)
            lines.append(f"  {label:<24} {count}")
    return lines


def _loss_streak(trades: list[ClosedTrade]) -> int:
    worst = 0
    current = 0
    for trade in trades:
        if trade.net_pnl < 0:
            current += 1
            worst = max(worst, current)
        else:
            current = 0
    return worst


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
