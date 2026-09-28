"""Mede a V1 numa amostra maior e a matriz da V2. Nao troca a regra padrao."""

from datetime import datetime, timedelta
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import compute_indicators, run_backtest

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
WINDOWS = (
    ("busca 2018-2021", "2018-01-01", "2021-12-31"),
    ("confirma 2022-2023", "2022-01-01", "2023-12-31"),
    ("ja visto 2024-2026", "2024-01-01", "2026-09-25"),
)
SEPARATIONS = (
    Decimal("0"),
    Decimal("0.0025"),
    Decimal("0.005"),
    Decimal("0.01"),
    Decimal("0.02"),
)
SLOPES = (
    Decimal("0"),
    Decimal("0.001"),
    Decimal("0.0025"),
    Decimal("0.005"),
)


def _variant(name: str, **overrides: object) -> tuple[str, dict[str, object]]:
    return name, overrides


ONE_WAY = (
    _variant("V1"),
    *[_variant(f"sep {value * 100:.2f}%", trend_separation_min=value) for value in SEPARATIONS if value > 0],
    *[_variant(f"slope {value * 100:.2f}%", ema_slope_min=value) for value in SLOPES if value > 0],
    _variant("RSI sobe", require_rsi_rising=True),
    _variant("candle positivo", candle_quality="positive"),
    _variant("topo 30%", candle_quality="top30"),
    _variant("topo 20%", candle_quality="top20"),
    _variant("ATR >= 1%", atr_pct_min=Decimal("0.01")),
    _variant("ATR <= 2.5%", atr_pct_max=Decimal("0.025")),
    _variant("ATR 1-2.5%", atr_pct_min=Decimal("0.01"), atr_pct_max=Decimal("0.025")),
    _variant("tendencia diaria", trend_hours=24),
)


def _hours() -> list:
    return aggregate_hours(load_candles("data/BTCUSDT-5m.csv"))


def _slice(candles: list, start: str, end: str, warmup_days: int) -> tuple[list, datetime]:
    start_at, end_at = parse_range(start, end)
    assert start_at is not None and end_at is not None
    warmup = start_at - timedelta(days=warmup_days)
    selected = [candle for candle in candles if warmup <= candle.timestamp <= end_at]
    return selected, start_at


_SERIES: dict[tuple[int, int], object] = {}


def _series(candles: list, overrides: dict[str, object]):
    hours = int(overrides.get("trend_hours", 4))
    key = (candles[0].timestamp, candles[-1].timestamp, len(candles), hours)
    cached = _SERIES.get(key)
    if cached is None:
        cached = compute_indicators(candles, get_settings(capital=Decimal("5000"), trend_hours=hours))
        _SERIES[key] = cached
    return cached


def _run(candles: list, start_at: datetime, overrides: dict[str, object]):
    settings = get_settings(capital=Decimal("5000"), **overrides)
    return run_backtest(
        candles,
        EmaRsiAtrVolumeStrategy(settings),
        settings,
        symbol="BTCUSDT",
        indicators=_series(candles, overrides),
        trade_from=start_at,
    )


def _line(label: str, window: str, report) -> str:
    factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
    return (
        f"{label:<16} {window:<20} {report.trades:6d} {report.net_pnl:10.2f} "
        f"{report.total_return * 100:7.2f}% {factor:>6} {report.expectancy:8.2f} "
        f"{report.max_drawdown * 100:7.2f}%"
    )


def _positive(report) -> bool:
    return (
        report.net_pnl > 0
        and report.profit_factor is not None
        and report.profit_factor > 1
        and report.expectancy > 0
    )


def main() -> int:
    candles = _hours()
    print(f"Candles de 1h: {len(candles)}  de {candles[0].timestamp:%Y-%m-%d} ate {candles[-1].timestamp:%Y-%m-%d}")
    print(f"{'Regra':<16} {'Janela':<20} {'Trades':>6} {'Liquido':>10} {'Retorno':>8} {'PF':>6} {'Esp':>8} {'DD':>8}")
    print("V1 por ano")
    for name, start, end in YEARS:
        selected, start_at = _slice(candles, start, end, 120)
        if not selected or selected[-1].timestamp < start_at:
            print(f"{'V1':<16} {name:<20} sem dados")
            continue
        print(_line("V1", name, _run(selected, start_at, {})))

    print()
    print("Um fator por vez, e a tendencia diaria separada")
    remembered: dict[tuple[str, str], object] = {}
    for name, start, end in WINDOWS:
        for label, overrides in ONE_WAY:
            warmup = 250 if overrides.get("trend_hours") == 24 else 120
            selected, start_at = _slice(candles, start, end, warmup)
            report = _run(selected, start_at, overrides)
            remembered[(label, name)] = report
            print(_line(label, name, report))
        print()

    print("Matriz separacao x inclinacao. Celula: trades / liquido / PF")
    for name, start, end in WINDOWS:
        selected, start_at = _slice(candles, start, end, 120)
        series_settings = get_settings(capital=Decimal("5000"))
        series = compute_indicators(selected, series_settings)
        print(name)
        header = "sep\\slope".ljust(12) + "".join(f"{value * 100:>16.2f}%" for value in SLOPES)
        print(header)
        for separation in SEPARATIONS:
            cells = []
            for slope in SLOPES:
                settings = get_settings(
                    capital=Decimal("5000"),
                    trend_separation_min=separation,
                    ema_slope_min=slope,
                )
                report = run_backtest(
                    selected,
                    EmaRsiAtrVolumeStrategy(settings),
                    settings,
                    symbol="BTCUSDT",
                    indicators=series,
                    trade_from=start_at,
                )
                factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
                mark = "*" if _positive(report) else " "
                cells.append(f"{report.trades}/{report.net_pnl:.0f}/{factor}{mark}")
            print(f"{separation * 100:5.2f}%".ljust(12) + "".join(f"{cell:>17}" for cell in cells))
        print()

    print("Criterio: liquido > 0, PF > 1 e expectativa > 0 na busca e na confirmacao.")
    search = "busca 2018-2021"
    confirm = "confirma 2022-2023"
    for label, _overrides in ONE_WAY:
        left = remembered[(label, search)]
        right = remembered[(label, confirm)]
        if _positive(left) and _positive(right):
            print(f"positivo nas duas: {label}  busca {left.trades} trades  confirma {right.trades} trades")
    print("Nenhuma linha acima substitui a V1. 2024-2026 continua janela ja vista.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
