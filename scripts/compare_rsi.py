"""Compara faixas de RSI. A regra congelada continua 40-55."""

from datetime import timedelta
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import run_backtest

WINDOWS = (
    ("2024", "2024-01-01", "2024-12-31"),
    ("2025", "2025-01-01", "2025-12-31"),
    ("2026", "2026-01-01", "2026-09-25"),
    ("continuo", "2024-01-01", "2026-09-25"),
)
BANDS = (
    ("40-55", Decimal("40"), Decimal("55")),
    ("35-55", Decimal("35"), Decimal("55")),
    ("35-60", Decimal("35"), Decimal("60")),
    ("40-60", Decimal("40"), Decimal("60")),
)


def _run(settings, strategy, start: str, end: str):
    start_at, end_at = parse_range(start, end)
    warmup = None if start_at is None else start_at - timedelta(days=120)
    candles = aggregate_hours(load_candles("data/BTCUSDT-5m.csv", warmup, end_at))
    return run_backtest(candles, strategy, settings, symbol="BTCUSDT", trade_from=start_at)


def main() -> int:
    print(f"{'RSI':<8} {'Janela':<12} {'Trades':>6} {'Liquido':>10} {'Retorno':>8} {'PF':>6} {'Sinais':>7}")
    for label, low, high in BANDS:
        settings = get_settings(capital=Decimal("5000"), rsi_min=low, rsi_max=high)
        strategy = EmaRsiAtrVolumeStrategy(settings)
        for window, start, end in WINDOWS:
            report = _run(settings, strategy, start, end)
            factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
            print(
                f"{label:<8} {window:<12} {report.trades:6d} "
                f"{report.net_pnl:10.2f} {report.total_return * 100:7.2f}% {factor:>6} {report.buy_signals:7d}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
