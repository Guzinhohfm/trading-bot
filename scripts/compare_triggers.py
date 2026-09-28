"""Compara tres gatilhos. Nao troca a regra congelada, que continua previous_high."""

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

TRIGGERS = (
    ("A previous_high", "previous_high"),
    ("B ema20", "ema20"),
    ("C bullish", "bullish"),
)


def _run(settings, strategy, start: str, end: str):
    start_at, end_at = parse_range(start, end)
    warmup = None if start_at is None else start_at - timedelta(days=120)
    candles = aggregate_hours(load_candles("data/BTCUSDT-5m.csv", warmup, end_at))
    return run_backtest(candles, strategy, settings, symbol="BTCUSDT", trade_from=start_at)


def main() -> int:
    print(f"{'Gatilho':<18} {'Janela':<12} {'Trades':>6} {'Liquido':>10} {'Retorno':>8} {'PF':>6} {'Sinais':>7}")
    for label, trigger in TRIGGERS:
        settings = get_settings(capital=Decimal("5000"), entry_trigger=trigger)
        strategy = EmaRsiAtrVolumeStrategy(settings)
        for window, start, end in WINDOWS:
            report = _run(settings, strategy, start, end)
            factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
            print(
                f"{label:<18} {window:<12} {report.trades:6d} "
                f"{report.net_pnl:10.2f} {report.total_return * 100:7.2f}% {factor:>6} {report.buy_signals:7d}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
