import argparse
from decimal import Decimal

from app.config.settings import Settings
from backtesting.data import load_candles, parse_range
from backtesting.engine import run_backtest
from backtesting.metrics import format_report
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trading-bot")
    sub = parser.add_subparsers(dest="command", required=True)
    backtest = sub.add_parser("backtest")
    backtest.add_argument("--symbol", required=True)
    backtest.add_argument("--csv", required=True)
    backtest.add_argument("--start")
    backtest.add_argument("--end")
    backtest.add_argument("--capital", type=Decimal)

    args = parser.parse_args(argv)
    settings = Settings()
    settings.assert_live_allowed()
    if args.capital is not None:
        settings = settings.model_copy(update={"capital": args.capital})

    start, end = parse_range(args.start, args.end)
    candles = load_candles(args.csv, start, end)
    if not candles:
        raise SystemExit("Nenhum candle no intervalo informado.")

    report = run_backtest(
        candles,
        EmaRsiAtrVolumeStrategy(settings),
        settings,
        symbol=args.symbol,
    )
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
