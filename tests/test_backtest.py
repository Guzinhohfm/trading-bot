from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Signal
from backtesting.broker import BacktestBroker, ClosedTrade, resolve_intrabar
from backtesting.engine import IndicatorSeries, run_backtest
from backtesting.metrics import build_report, format_report, max_drawdown, profit_factor


class _ExitOnTrend:
    def analyze(self, candle: Candle, indicators: IndicatorSnapshot, position_open: bool) -> Signal:
        if position_open:
            return Signal.SELL
        if candle.close == Decimal("10"):
            return Signal.BUY
        return Signal.HOLD


class _Scripted:
    def __init__(self, buy_closes: set[Decimal]) -> None:
        self.buy_closes = buy_closes

    def analyze(self, candle: Candle, indicators: IndicatorSnapshot, position_open: bool) -> Signal:
        if position_open:
            return Signal.HOLD
        if candle.close in self.buy_closes:
            return Signal.BUY
        return Signal.HOLD


def _flat_indicators(count: int, atr: str = "40") -> IndicatorSeries:
    return IndicatorSeries(
        ema_fast=[Decimal("1")] * count,
        ema_slow=[Decimal("1")] * count,
        rsi=[Decimal("40")] * count,
        atr=[Decimal(atr)] * count,
        avg_volume=[Decimal("1")] * count,
    )


def _candle(index: int, **overrides: str) -> Candle:
    values = {
        "open": "10",
        "high": "10",
        "low": "10",
        "close": "10",
        "volume": "10",
    }
    values.update(overrides)
    moment = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=5 * index)
    return Candle(
        timestamp=moment,
        open=Decimal(values["open"]),
        high=Decimal(values["high"]),
        low=Decimal(values["low"]),
        close=Decimal(values["close"]),
        volume=Decimal(values["volume"]),
    )


def test_stop_has_priority_when_both_levels_are_touched() -> None:
    assert resolve_intrabar(
        Decimal("100"),
        Decimal("105"),
        Decimal("95"),
        Decimal("98"),
        Decimal("104"),
    ) == (Decimal("98"), "stop")


def test_gap_through_stop_fills_at_the_open() -> None:
    assert resolve_intrabar(
        Decimal("90"),
        Decimal("91"),
        Decimal("89"),
        Decimal("98"),
        Decimal("104"),
    ) == (Decimal("90"), "stop")


def test_entry_uses_next_open_and_daily_loss_blocks_the_next_one() -> None:
    candles = [
        _candle(0, close="10"),
        _candle(1, open="100", high="100", low="1", close="20"),
        _candle(2, close="30"),
        _candle(3, open="50", high="50", low="50", close="50"),
    ]
    settings = get_settings(
        capital=Decimal("1000"),
        risk_per_trade=Decimal("0.04"),
        fee_rate=Decimal("0"),
        slippage=Decimal("0"),
        min_notional=Decimal("1"),
    )
    report = run_backtest(
        candles,
        _Scripted({Decimal("10"), Decimal("30")}),
        settings,
        symbol="BTCUSDT",
        indicators=_flat_indicators(len(candles)),
    )
    assert report.trades == 1
    assert report.net_pnl == Decimal("-39.9996")


def test_trend_exit_happens_at_the_close() -> None:
    candles = [
        _candle(0, close="10"),
        _candle(1, open="100", high="101", low="99", close="100"),
    ]
    settings = get_settings(
        capital=Decimal("5000"),
        fee_rate=Decimal("0"),
        slippage=Decimal("0"),
        min_notional=Decimal("1"),
    )
    report = run_backtest(
        candles,
        _ExitOnTrend(),
        settings,
        symbol="ETHUSDT",
        indicators=_flat_indicators(len(candles), atr="1"),
    )
    assert report.trades == 1
    assert report.net_pnl == Decimal("0")


def test_round_trip_splits_fees_and_slippage_from_gross() -> None:
    settings = get_settings(fee_rate=Decimal("0.001"), slippage=Decimal("0.0005"), capital=Decimal("1000"))
    broker = BacktestBroker(Decimal("1000"), settings)
    when = datetime(2025, 1, 1, tzinfo=timezone.utc)
    position, buy = broker.open_long(
        Decimal("100"),
        Decimal("1"),
        Decimal("90"),
        Decimal("120"),
        when,
    )
    assert buy.status == "FILLED"
    trade = broker.close_long(position, Decimal("110"), when, "take_profit")
    assert trade.gross_pnl == Decimal("10")
    assert trade.net_pnl == trade.gross_pnl - trade.fees - trade.slippage
    assert trade.slippage == Decimal("0.105")


def test_profit_factor_expectancy_and_drawdown() -> None:
    moment = datetime(2025, 1, 1, tzinfo=timezone.utc)
    trades = [
        ClosedTrade(
            Decimal("1"),
            Decimal("10"),
            Decimal("110"),
            Decimal("100"),
            Decimal("0"),
            Decimal("0"),
            Decimal("100"),
            "take_profit",
            moment,
            moment,
        ),
        ClosedTrade(
            Decimal("1"),
            Decimal("50"),
            Decimal("10"),
            Decimal("-40"),
            Decimal("0"),
            Decimal("0"),
            Decimal("-40"),
            "stop",
            moment,
            moment,
        ),
    ]
    assert profit_factor(trades) == Decimal("2.5")
    report = build_report(
        symbol="BTCUSDT",
        timeframe="5m",
        start=moment,
        end=moment,
        initial_capital=Decimal("5000"),
        trades=trades,
        equity=[Decimal("100"), Decimal("120"), Decimal("90")],
    )
    assert report.max_drawdown == max_drawdown([Decimal("100"), Decimal("120"), Decimal("90")])
    assert report.max_drawdown == Decimal("0.25")
    assert report.win_rate == Decimal("0.5")
    assert report.expectancy == Decimal("30")
    text = format_report(report)
    assert "BACKTEST — STRATEGY V1" in text
    assert "Profit Factor:" in text
    assert "Max Drawdown:" in text
    assert "Expectancy:" in text
