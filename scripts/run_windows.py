"""Treino 2024-2025 congelado, validacao 2026. Nao busca parametros."""

from datetime import timedelta
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import run_backtest
from backtesting.metrics import BacktestReport, format_report

TRAIN = ("2024-01-01", "2025-12-31")
VALIDATE = ("2026-01-01", "2026-09-25")
SYMBOL = "BTCUSDT"


def _run(settings, strategy, start: str, end: str) -> BacktestReport:
    start_at, end_at = parse_range(start, end)
    warmup = None if start_at is None else start_at - timedelta(days=120)
    candles = aggregate_hours(load_candles(f"data/{SYMBOL}-5m.csv", warmup, end_at))
    return run_backtest(
        candles,
        strategy,
        settings,
        symbol=SYMBOL,
        trade_from=start_at,
    )


def main() -> int:
    settings = get_settings(capital=Decimal("5000"))
    strategy = EmaRsiAtrVolumeStrategy(settings)
    train = _run(settings, strategy, *TRAIN)
    validate = _run(settings, strategy, *VALIDATE)
    print("TREINO (regra congelada)")
    print(format_report(train))
    print()
    print("VALIDACAO")
    print(format_report(validate))
    print()
    if validate.net_pnl <= 0:
        print(
            "Validacao negativa. Nao avance para paper nem testnet. "
            "VALIDATION_PASSED continua false."
        )
        return 1
    print(
        "Validacao positiva com a regra congelada. "
        "So entao VALIDATION_PASSED=true libera paper ou testnet."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
