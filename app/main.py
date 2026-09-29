import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.config.settings import Mode, Settings
from app.market.public_klines import fetch_closed_klines, public_window
from app.notify.telegram import notify_new_operations
from app.paper.replay import run_paper
from app.paper.resident import run_resident
from app.storage.paper_store import save_public_run
from app.strategies.ema_rsi_atr_volume import EmaRsiAtrVolumeStrategy
from backtesting.data import aggregate_hours, load_candles, parse_range
from backtesting.engine import run_backtest
from backtesting.metrics import format_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trading-bot")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("backtest", "paper"):
        command = sub.add_parser(name)
        command.add_argument("--symbol", required=True)
        command.add_argument("--csv", required=True)
        command.add_argument("--start")
        command.add_argument("--end")
        command.add_argument("--capital", type=Decimal)
    sync = sub.add_parser("sync-public")
    sync.add_argument("--symbol", default="BTCUSDT")
    sync.add_argument("--days", type=int, default=7)
    sync.add_argument("--capital", type=Decimal)
    sync.add_argument(
        "--resident",
        action="store_true",
        help="Repete a mesma leitura a cada hora UTC fechada.",
    )

    args = parser.parse_args(argv)
    settings = Settings()
    if args.capital is not None:
        settings = settings.model_copy(update={"capital": args.capital})
    if args.command in ("paper", "sync-public"):
        if settings.mode is Mode.LIVE:
            raise SystemExit("Paper recusa MODE=live.")
        settings = settings.model_copy(update={"mode": Mode.PAPER})
    settings.assert_forward_allowed()
    if args.command == "sync-public":
        if args.resident:
            return run_resident(lambda: _sync_public(settings, args))
        return _sync_public(settings, args)

    candles, start = _hourly_candles(args)
    strategy = EmaRsiAtrVolumeStrategy(settings)
    runner = run_paper if args.command == "paper" else run_backtest
    report = runner(candles, strategy, settings, symbol=args.symbol, trade_from=start)
    print(format_report(report))
    if args.command == "paper":
        print("Paper: nenhuma ordem enviada.")
    return 0


def _sync_public(settings: Settings, args: argparse.Namespace) -> int:
    now = datetime.now(timezone.utc)
    start, end, trade_from = public_window(args.days, now=now)
    candles = fetch_closed_klines(args.symbol, "1h", start, end, now=now)
    if not candles:
        raise SystemExit("Nenhum candle fechado.")
    journal: list = []
    report = run_paper(
        candles,
        EmaRsiAtrVolumeStrategy(settings),
        settings,
        symbol=args.symbol,
        trade_from=trade_from,
        journal=journal,
    )
    summary = (
        f"paper {args.symbol} candles={len(candles)} decisoes={len(journal)} "
        f"trades={report.trades} liquido={report.net_pnl:.2f}"
    )
    saved = save_public_run(
        settings,
        symbol=args.symbol,
        candles=candles,
        notes=journal,
        trades=report.closed_trades,
        summary=summary,
    )
    print(format_report(report))
    print(
        f"Banco: {saved['candles']} candles, {saved['decisions']} decisoes, {saved['trades']} trades."
    )
    print("Paper: nenhuma ordem enviada.")
    notify_new_operations(settings, args.symbol, report)
    return 0


def _hourly_candles(args: argparse.Namespace):
    start, end = parse_range(args.start, args.end)
    warmup = None if start is None else start - timedelta(days=120)
    raw = load_candles(args.csv, warmup, end)
    in_window = [
        candle
        for candle in raw
        if (start is None or candle.timestamp >= start) and (end is None or candle.timestamp <= end)
    ]
    if not in_window:
        raise SystemExit("Nenhum candle no intervalo informado.")
    return aggregate_hours(raw), start


if __name__ == "__main__":
    raise SystemExit(main())
