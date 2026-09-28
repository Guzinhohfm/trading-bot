from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.market.candles import Candle, IndicatorSnapshot
from app.strategies.base import Signal
from backtesting.broker import BacktestBroker, ClosedTrade, resolve_intrabar
from backtesting.data import aggregate_hours
from backtesting.engine import IndicatorSeries, four_hour_context, run_backtest
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


def test_five_minute_bars_fold_into_one_hour() -> None:
    bars = [
        _candle(0, open="10", high="12", low="9", close="11", volume="1"),
        _candle(1, open="11", high="15", low="8", close="14", volume="2"),
    ]
    hour = aggregate_hours(bars)
    assert len(hour) == 1
    assert hour[0].timestamp == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert hour[0].open == Decimal("10")
    assert hour[0].high == Decimal("15")
    assert hour[0].low == Decimal("8")
    assert hour[0].close == Decimal("14")
    assert hour[0].volume == Decimal("3")


def test_four_hour_trend_waits_for_the_closed_bucket() -> None:
    settings = get_settings(ema_trend=1, ema_trend_slow=1, ema_slope_lookback=1)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(
            timestamp=start + timedelta(hours=index),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
            volume=Decimal("1"),
        )
        for index in range(4)
    ]
    context = four_hour_context(candles, settings)
    assert context.trend == [False, False, False, False]
    assert context.previous_high[0] is None
    assert context.previous_high[1] == Decimal("11")
    assert context.ema50 == [None, None, None, Decimal("10")]
    assert resolve_intrabar(
        Decimal("100"),
        Decimal("105"),
        Decimal("95"),
        Decimal("98"),
        Decimal("104"),
    ) == (Decimal("98"), "stop")


def test_gap_through_stop_is_reported_apart_from_the_planned_risk() -> None:
    settings = get_settings(fee_rate=Decimal("0"), slippage=Decimal("0"), capital=Decimal("1000"))
    broker = BacktestBroker(Decimal("1000"), settings)
    when = datetime(2025, 1, 1, tzinfo=timezone.utc)
    position, _buy = broker.open_long(
        Decimal("100"),
        Decimal("1"),
        Decimal("95"),
        Decimal("110"),
        when,
        Decimal("5"),
    )
    trade = broker.close_long(position, Decimal("90"), when, "stop")
    assert trade.planned_risk == Decimal("5")
    assert trade.gap_loss == Decimal("5")


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
        max_daily_loss=Decimal("0.03"),
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
    assert report.net_pnl == Decimal("-40.00")


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
        indicators=_flat_indicators(len(candles), atr="2"),
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
    logged = build_report(
        symbol="BTCUSDT",
        timeframe="1h",
        start=moment,
        end=moment,
        initial_capital=Decimal("5000"),
        trades=[],
        equity=[Decimal("5000")],
        candles_seen=4,
        buy_signals=1,
        funnel=(("trend_4h", 2), ("pullback", 1), ("entries", 1)),
    )
    logged_text = format_report(logged)
    assert "Sinais BUY:" in logged_text
    assert "Funil" in logged_text
    assert "Tendência 4h" in logged_text
    assert "Pullback" in logged_text
