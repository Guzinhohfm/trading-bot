from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.config.settings import Mode, get_settings
from app.execution.gateway import DisabledGateway, OrderRequest
from app.main import main
from app.paper.replay import run_paper
from app.strategies.base import Signal
from backtesting.engine import IndicatorSeries, run_backtest
from app.market.candles import Candle, IndicatorSnapshot


class _Scripted:
    def analyze(self, candle: Candle, indicators: IndicatorSnapshot, position_open: bool) -> Signal:
        del indicators
        if position_open:
            return Signal.HOLD
        if candle.close == Decimal("10"):
            return Signal.BUY
        return Signal.HOLD


def _candles() -> list[Candle]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = [("10", "10", "10"), ("100", "100", "1"), ("30", "30", "30"), ("50", "50", "50")]
    candles = []
    for index, (close, high, low) in enumerate(rows):
        price = Decimal(close)
        candles.append(
            Candle(
                timestamp=start + timedelta(hours=index),
                open=price,
                high=Decimal(high),
                low=Decimal(low),
                close=price,
                volume=Decimal("10"),
            )
        )
    candles[1] = Candle(
        timestamp=start + timedelta(hours=1),
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("1"),
        close=Decimal("20"),
        volume=Decimal("10"),
    )
    return candles


def _indicators(count: int) -> IndicatorSeries:
    return IndicatorSeries(
        ema_fast=[Decimal("1")] * count,
        ema_slow=[Decimal("1")] * count,
        rsi=[Decimal("40")] * count,
        atr=[Decimal("40")] * count,
        avg_volume=[Decimal("1")] * count,
    )


def test_paper_replay_matches_the_backtest() -> None:
    candles = _candles()
    settings = get_settings(
        mode=Mode.PAPER,
        capital=Decimal("1000"),
        risk_per_trade=Decimal("0.04"),
        max_daily_loss=Decimal("0.03"),
        fee_rate=Decimal("0"),
        slippage=Decimal("0"),
        min_notional=Decimal("1"),
    )
    indicators = _indicators(len(candles))
    paper = run_paper(candles, _Scripted(), settings, symbol="BTCUSDT", indicators=indicators)
    backtest = run_backtest(candles, _Scripted(), settings, symbol="BTCUSDT", indicators=indicators)
    assert paper.trades == backtest.trades == 1
    assert paper.net_pnl == backtest.net_pnl


def test_gateway_refuses_to_submit() -> None:
    with pytest.raises(RuntimeError, match="Ordem real bloqueada"):
        DisabledGateway().submit(OrderRequest("BTCUSDT", "BUY", Decimal("0.001")))


def test_paper_command_prints_that_no_order_was_sent(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2025-01-01T00:00:00+00:00,10,10,10,10,1\n"
        "2025-01-01T01:00:00+00:00,10,10,10,10,1\n",
        encoding="utf-8",
    )
    code = main(
        [
            "paper",
            "--symbol",
            "BTCUSDT",
            "--csv",
            str(csv_path),
            "--start",
            "2025-01-01",
            "--end",
            "2025-01-01",
            "--capital",
            "5000",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Paper: nenhuma ordem enviada." in captured.out
