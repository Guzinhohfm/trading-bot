"""Tres ativos isolados na mesma janela de 30 dias. Nao mistura o capital."""

from datetime import timedelta
from decimal import Decimal

from app.config.settings import get_settings
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import run_backtest

START = "2026-08-29"
END = "2026-09-25"
ASSETS = (
    ("BTCUSDT", Decimal("0.00001"), Decimal("0.00001")),
    ("ETHUSDT", Decimal("0.0001"), Decimal("0.0001")),
    ("SOLUSDT", Decimal("0.001"), Decimal("0.001")),
)


def main() -> int:
    start_at, end_at = parse_range(START, END)
    warmup = start_at - timedelta(days=120)
    total = Decimal("0")
    trades = 0
    print(f"Janela {START} a {END}. Cada ativo com 5000 proprios.")
    print(f"{'Ativo':<10} {'Trades':>6} {'Liquido':>10} {'Retorno':>8} {'PF':>6}")
    for symbol, step, minimum in ASSETS:
        settings = get_settings(
            capital=Decimal("5000"),
            tick_size=Decimal("0.01"),
            step_size=step,
            min_qty=minimum,
            min_notional=Decimal("5"),
        )
        candles = aggregate_hours(load_candles(f"data/{symbol}-5m.csv", warmup, end_at))
        report = run_backtest(
            candles,
            EmaRsiAtrVolumeStrategy(settings),
            settings,
            symbol=symbol,
            trade_from=start_at,
        )
        factor = "n/a" if report.profit_factor is None else f"{report.profit_factor:.2f}"
        print(
            f"{symbol:<10} {report.trades:6d} {report.net_pnl:10.2f} "
            f"{report.total_return * 100:7.2f}% {factor:>6}"
        )
        for trade in report.closed_trades:
            print(
                f"  {trade.opened_at:%Y-%m-%d %H:%M} -> {trade.closed_at:%Y-%m-%d %H:%M} "
                f"{trade.reason:<12} {trade.net_pnl:8.2f}"
            )
        total += report.net_pnl
        trades += report.trades
    print(f"Soma dos liquidos: {total:.2f} em {trades} trades fechados")
    print(f"Sobre 15000 (tres contas): {total / Decimal('15000') * 100:.2f}%")
    print(f"Sobre 5000 (uma conta so): {total / Decimal('5000') * 100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
