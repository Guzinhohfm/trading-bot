from datetime import datetime, timezone
from decimal import Decimal

from app.config.settings import get_settings
from app.notify.telegram import (
    baseline_keys,
    notify_new_operations,
    pending_notices,
    send_message,
)
from backtesting.broker import ClosedTrade, OpenPosition
from backtesting.metrics import build_report


def _trade() -> ClosedTrade:
    return ClosedTrade(
        quantity=Decimal("0.01"),
        entry_market=Decimal("100"),
        exit_market=Decimal("110"),
        gross_pnl=Decimal("0.10"),
        fees=Decimal("0.01"),
        slippage=Decimal("0.01"),
        net_pnl=Decimal("0.08"),
        reason="take_profit",
        opened_at=datetime(2026, 8, 29, 15, tzinfo=timezone.utc),
        closed_at=datetime(2026, 9, 21, 13, tzinfo=timezone.utc),
    )


def _report(position: OpenPosition | None = None):
    trade = _trade()
    return build_report(
        symbol="BTCUSDT",
        timeframe="1h",
        start=trade.opened_at,
        end=trade.closed_at,
        initial_capital=Decimal("5000"),
        trades=[trade],
        equity=[Decimal("5000")],
        closed_trades=(trade,),
        open_position=position,
    )


def test_first_reading_does_not_repeat_an_existing_trade() -> None:
    report = _report()
    assert pending_notices("BTCUSDT", report, set()) == []
    known = set(baseline_keys("BTCUSDT", report))
    assert pending_notices("BTCUSDT", report, known) == []


def test_a_new_entry_is_sent_once() -> None:
    position = OpenPosition(
        quantity=Decimal("0.02"),
        entry_market=Decimal("200"),
        entry_effective=Decimal("200.1"),
        entry_fee=Decimal("0.01"),
        stop=Decimal("190"),
        take_profit=Decimal("220"),
        opened_at=datetime(2026, 9, 24, 13, tzinfo=timezone.utc),
    )
    report = _report(position)
    known = set(baseline_keys("BTCUSDT", _report()))
    fresh = pending_notices("BTCUSDT", report, known)
    assert [notice.key for notice in fresh] == ["open:BTCUSDT:2026-09-24T13:00:00+00:00"]
    assert pending_notices("BTCUSDT", report, known | {fresh[0].key}) == []


def test_send_uses_telegram_and_not_a_binance_order() -> None:
    seen: list[str] = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _open(request, timeout):
        del timeout
        seen.append(request.full_url)
        return _Response()

    send_message("tok", "99", "ola", urlopen=_open)
    assert seen[0].startswith("https://api.telegram.org/bot")
    assert seen[0].endswith("/sendMessage")
    assert "/api/v3/order" not in seen[0]


def test_blank_token_skips_telegram(monkeypatch) -> None:
    def _boom(*args, **kwargs):
        del args, kwargs
        raise AssertionError("nao devia consultar o banco")

    monkeypatch.setattr("app.storage.paper_store.load_notice_keys", _boom)
    sent = notify_new_operations(
        get_settings(telegram_bot_token="", telegram_chat_id=""),
        "BTCUSDT",
        _report(),
    )
    assert sent == 0


def test_first_sync_marks_the_diary_and_sends_only_the_ready_note(monkeypatch) -> None:
    stored: list[str] = []
    sent: list[str] = []
    monkeypatch.setattr("app.storage.paper_store.load_notice_keys", lambda settings: set())
    monkeypatch.setattr(
        "app.storage.paper_store.save_notice_keys",
        lambda settings, keys: stored.extend(keys),
    )
    monkeypatch.setattr(
        "app.notify.telegram.send_message",
        lambda token, chat_id, text, urlopen=None: sent.append(text),
    )
    count = notify_new_operations(
        get_settings(telegram_bot_token="tok", telegram_chat_id="99"),
        "BTCUSDT",
        _report(),
    )
    assert count == 0
    assert len(sent) == 1
    assert "ligado" in sent[0]
    assert "ready:BTCUSDT" in stored
    assert any(key.startswith("close:") for key in stored)
