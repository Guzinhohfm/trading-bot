"""Lista os trades da curva continua e resume regime, RSI, ATR e horario. Nao muda a regra."""

from datetime import timedelta
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.broker import ClosedTrade
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import run_backtest


def _run():
    settings = get_settings(capital=Decimal("5000"))
    start_at, end_at = parse_range("2024-01-01", "2026-09-25")
    warmup = start_at - timedelta(days=120) if start_at else None
    candles = aggregate_hours(load_candles("data/BTCUSDT-5m.csv", warmup, end_at))
    return run_backtest(
        candles,
        EmaRsiAtrVolumeStrategy(settings),
        settings,
        symbol="BTCUSDT",
        trade_from=start_at,
    )


def _pct(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{(value * Decimal(100)):.2f}%"


def _num(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _mean(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _bucket(value: Decimal | None, edges: tuple[Decimal, ...]) -> str:
    if value is None:
        return "sem dado"
    for edge in edges:
        if value < edge:
            return f"< {edge * 100:.2f}%"
    return f">= {edges[-1] * 100:.2f}%"


def _summarize(title: str, groups: dict[str, list[ClosedTrade]]) -> None:
    print(title)
    print(f"{'Grupo':<16} {'N':>4} {'Liquido':>10} {'Acerto':>8} {'Separacao':>10} {'Inclinacao':>10} {'ATR':>8}")
    for name, rows in groups.items():
        nets = [trade.net_pnl for trade in rows]
        wins = sum(1 for trade in rows if trade.net_pnl > 0)
        rate = Decimal(wins) / Decimal(len(rows)) if rows else Decimal("0")
        notes = [trade.note for trade in rows if trade.note is not None]
        print(
            f"{name:<16} {len(rows):4d} {sum(nets, Decimal('0')):10.2f} {_pct(rate):>8} "
            f"{_pct(_mean([note.ema_separation for note in notes if note.ema_separation is not None])):>10} "
            f"{_pct(_mean([note.ema_slope for note in notes if note.ema_slope is not None])):>10} "
            f"{_pct(_mean([note.atr_pct for note in notes if note.atr_pct is not None])):>8}"
        )
    print()


def main() -> int:
    report = _run()
    trades = list(report.closed_trades)
    print(f"{'#':>3} {'Entrada':<17} {'H':>2} {'Saida':<6} {'Liquido':>8} {'RSI':>6} {'Sobe':>4} {'Sep':>7} {'Slope':>7} {'ATR':>6} {'DD':>6}")
    for index, trade in enumerate(trades, start=1):
        note = trade.note
        rising = "-"
        if note and note.rsi is not None and note.rsi_previous is not None:
            rising = "sim" if note.rsi > note.rsi_previous else "nao"
        hours = int((trade.closed_at - trade.opened_at).total_seconds() // 3600)
        print(
            f"{index:3d} {trade.opened_at:%Y-%m-%d %H:%M} {note.hour if note else '-':>2} "
            f"{trade.reason:<6} {trade.net_pnl:8.2f} {_num(note.rsi if note else None):>6} {rising:>4} "
            f"{_pct(note.ema_separation if note else None):>7} {_pct(note.ema_slope if note else None):>7} "
            f"{_pct(note.atr_pct if note else None):>6} {_pct(note.drawdown if note else None):>6} {hours:>4}h"
        )
    print()
    winners = [trade for trade in trades if trade.net_pnl > 0]
    losers = [trade for trade in trades if trade.net_pnl <= 0]
    _summarize("Resultado", {"ganhos": winners, "perdas": losers})
    by_year: dict[str, list[ClosedTrade]] = {}
    for trade in trades:
        by_year.setdefault(str(trade.opened_at.year), []).append(trade)
    _summarize("Ano", by_year)
    edges = (Decimal("0.005"), Decimal("0.01"), Decimal("0.02"))
    by_sep: dict[str, list[ClosedTrade]] = {}
    by_slope: dict[str, list[ClosedTrade]] = {}
    by_rsi: dict[str, list[ClosedTrade]] = {"RSI sobe": [], "RSI cai": []}
    for trade in trades:
        note = trade.note
        if note is None:
            continue
        by_sep.setdefault(_bucket(note.ema_separation, edges), []).append(trade)
        by_slope.setdefault(_bucket(note.ema_slope, (Decimal("0.001"), Decimal("0.0025"), Decimal("0.005"))), []).append(trade)
        if note.rsi is not None and note.rsi_previous is not None:
            key = "RSI sobe" if note.rsi > note.rsi_previous else "RSI cai"
            by_rsi[key].append(trade)
    _summarize("Separacao EMA50/200", by_sep)
    _summarize("Inclinacao EMA50", by_slope)
    _summarize("Direcao do RSI", by_rsi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
