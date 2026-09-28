"""V1 isolada em cada par da fila. Mesma regra do BTC, capital proprio de 5000."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import run_backtest

# tick, step, min qty, min notional. A regra nao muda entre os pares.
ASSETS = (
    ("BNBUSDT", Decimal("0.01"), Decimal("0.001"), Decimal("0.001"), Decimal("5")),
    ("TRXUSDT", Decimal("0.0001"), Decimal("0.1"), Decimal("0.1"), Decimal("5")),
    ("XRPUSDT", Decimal("0.0001"), Decimal("0.1"), Decimal("0.1"), Decimal("5")),
    ("DOGEUSDT", Decimal("0.00001"), Decimal("1"), Decimal("1"), Decimal("1")),
)
END = "2026-09-25"


def _measure_start(first: datetime) -> datetime:
    """Primeiro 1 de janeiro com 120 dias de aquecimento antes dele."""
    year = 2018
    while True:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        if start - timedelta(days=120) >= first:
            return start
        year += 1


def _run(
    symbol: str,
    hourly: list,
    filters: tuple[Decimal, Decimal, Decimal, Decimal],
    start: str,
    end: str,
):
    tick, step, qty, notional = filters
    settings = get_settings(
        capital=Decimal("5000"),
        tick_size=tick,
        step_size=step,
        min_qty=qty,
        min_notional=notional,
    )
    start_at, end_at = parse_range(start, end)
    warmup = start_at - timedelta(days=120)
    window = [candle for candle in hourly if warmup <= candle.timestamp <= end_at]
    return window, run_backtest(
        window,
        EmaRsiAtrVolumeStrategy(settings),
        settings,
        symbol=symbol,
        trade_from=start_at,
    )


def _line(label: str, report) -> str:
    factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
    return (
        f"{label:<12} {report.trades:6d} {report.net_pnl:10.2f} {report.total_return * 100:8.2f}% "
        f"{factor:>6} {report.expectancy:8.2f} {report.max_drawdown * 100:7.2f}% {report.buy_signals:7d}"
    )


def _asset(symbol: str, filters: tuple[Decimal, Decimal, Decimal, Decimal]) -> None:
    candles = aggregate_hours(load_candles(f"data/{symbol}-5m.csv"))
    first = candles[0].timestamp
    start = _measure_start(first)
    years = [(str(year), f"{year}-01-01", f"{year}-12-31") for year in range(start.year, 2026)]
    years.append(("2026", "2026-01-01", END))
    print(symbol)
    print(f"Primeiro candle do arquivo: {first:%Y-%m-%d}")
    print(f"{'Janela':<12} {'Trades':>6} {'Liquido':>10} {'Retorno':>9} {'PF':>6} {'Esp':>8} {'DD':>8} {'Sinais':>7}")
    for label, window_start, window_end in years:
        _candles, report = _run(symbol, candles, filters, window_start, window_end)
        print(_line(label, report))
    span = f"{start:%Y-%m-%d}"
    candles, report = _run(symbol, candles, filters, span, END)
    print(_line(f"{start.year}-2026", report))
    counted = next(candle for candle in candles if candle.timestamp >= start)
    last = candles[-1]
    hold = (last.close - counted.close) / counted.close
    print(
        f"Comprar e segurar {symbol} de {counted.timestamp:%Y-%m-%d} a {last.timestamp:%Y-%m-%d}: {hold * 100:.2f}%"
    )
    print()


def main() -> int:
    for symbol, *filters in ASSETS:
        _asset(symbol, tuple(filters))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
