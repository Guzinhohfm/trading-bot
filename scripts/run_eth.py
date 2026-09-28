"""V1 isolada em ETHUSDT. Mesma regra do BTC, capital reinicia em 5000 por ano."""

from datetime import timedelta
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import run_backtest

YEARS = (
    ("2018", "2018-01-01", "2018-12-31"),
    ("2019", "2019-01-01", "2019-12-31"),
    ("2020", "2020-01-01", "2020-12-31"),
    ("2021", "2021-01-01", "2021-12-31"),
    ("2022", "2022-01-01", "2022-12-31"),
    ("2023", "2023-01-01", "2023-12-31"),
    ("2024", "2024-01-01", "2024-12-31"),
    ("2025", "2025-01-01", "2025-12-31"),
    ("2026", "2026-01-01", "2026-09-25"),
)
CONTINUOUS = ("2018-01-01", "2026-09-25")


def _settings():
    return get_settings(
        capital=Decimal("5000"),
        tick_size=Decimal("0.01"),
        step_size=Decimal("0.0001"),
        min_qty=Decimal("0.0001"),
        min_notional=Decimal("5"),
    )


def _run(start: str, end: str):
    settings = _settings()
    start_at, end_at = parse_range(start, end)
    warmup = None if start_at is None else start_at - timedelta(days=120)
    candles = aggregate_hours(load_candles("data/ETHUSDT-5m.csv", warmup, end_at))
    return candles, run_backtest(
        candles,
        EmaRsiAtrVolumeStrategy(settings),
        settings,
        symbol="ETHUSDT",
        trade_from=start_at,
    )


def _line(label: str, report) -> str:
    factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
    return (
        f"{label:<12} {report.trades:6d} {report.net_pnl:10.2f} {report.total_return * 100:8.2f}% "
        f"{factor:>6} {report.expectancy:8.2f} {report.max_drawdown * 100:7.2f}% {report.buy_signals:7d}"
    )


def main() -> int:
    print(f"{'Janela':<12} {'Trades':>6} {'Liquido':>10} {'Retorno':>9} {'PF':>6} {'Esp':>8} {'DD':>8} {'Sinais':>7}")
    for label, start, end in YEARS:
        _candles, report = _run(start, end)
        print(_line(label, report))
    candles, report = _run(*CONTINUOUS)
    print(_line("2018-2026", report))
    first = next(candle for candle in candles if candle.timestamp.year >= 2018)
    last = candles[-1]
    hold = (last.close - first.close) / first.close
    print(
        f"Comprar e segurar ETH de {first.timestamp:%Y-%m-%d} a {last.timestamp:%Y-%m-%d}: {hold * 100:.2f}%"
    )
    print(f"Primeiro candle do arquivo: {candles[0].timestamp:%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
