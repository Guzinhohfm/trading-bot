"""Compara a V1 com a mesma entrada so quando o diario tambem esta em alta."""

from datetime import timedelta
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import compute_indicators, run_backtest

WINDOWS = (
    ("2018", "2018-01-01", "2018-12-31"),
    ("2019", "2019-01-01", "2019-12-31"),
    ("2020", "2020-01-01", "2020-12-31"),
    ("2021", "2021-01-01", "2021-12-31"),
    ("2022", "2022-01-01", "2022-12-31"),
    ("2023", "2023-01-01", "2023-12-31"),
    ("2024", "2024-01-01", "2024-12-31"),
    ("2025", "2025-01-01", "2025-12-31"),
    ("2026", "2026-01-01", "2026-09-25"),
    ("2018-2026", "2018-01-01", "2026-09-25"),
)


def _slice(candles: list, start: str, end: str) -> tuple[list, object]:
    start_at, end_at = parse_range(start, end)
    warmup = start_at - timedelta(days=250) if start_at is not None else None
    selected = [candle for candle in candles if warmup <= candle.timestamp <= end_at]
    return selected, start_at


def _report(candles: list, start_at, daily: bool):
    settings = get_settings(capital=Decimal("5000"), require_daily_trend=daily)
    return run_backtest(
        candles,
        EmaRsiAtrVolumeStrategy(settings),
        settings,
        symbol="BTCUSDT",
        indicators=compute_indicators(candles, settings),
        trade_from=start_at,
    )


def _cell(report) -> str:
    factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
    return (
        f"{report.trades:4d} {report.net_pnl:9.2f} {report.total_return * 100:7.2f}% "
        f"{factor:>5} {report.expectancy:8.2f} {report.max_drawdown * 100:6.2f}%"
    )


def main() -> int:
    candles = aggregate_hours(load_candles("data/BTCUSDT-5m.csv"))
    first = next(candle for candle in candles if candle.timestamp.year >= 2018)
    last = candles[-1]
    hold = (last.close - first.close) / first.close
    print(f"Comprar e segurar de {first.timestamp:%Y-%m-%d} a {last.timestamp:%Y-%m-%d}: {hold * 100:.2f}%")
    print(f"{'Janela':<12} {'V1':<46} {'V1 + diario'}")
    print(f"{'':<12} {'trades liquido retorno PF esp DD':<46}")
    for name, start, end in WINDOWS:
        selected, start_at = _slice(candles, start, end)
        plain = _report(selected, start_at, False)
        gated = _report(selected, start_at, True)
        print(f"{name:<12} {_cell(plain):<46} {_cell(gated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
