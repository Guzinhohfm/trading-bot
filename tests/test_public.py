import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.config.settings import Mode
from app.main import main
from app.market.candles import Candle, IndicatorSnapshot
from app.paper.resident import next_closed_hour, run_resident
from app.market.public_klines import fetch_closed_klines, parse_closed_klines
from app.storage.paper_store import connection_kwargs
from app.paper.records import note_from_decision
from app.strategies.base import Decision, RuleCheck, Signal


def _kline(open_ms: int, step: int, close: str = "100") -> list:
    return [open_ms, close, close, close, close, "1", open_ms + step - 1, "0", 1, "0", "0", "0"]


def test_database_password_keeps_an_at_sign() -> None:
    parsed = connection_kwargs("postgresql+psycopg://trading:segredo@2026@db:5432/trading")
    assert parsed["host"] == "db"
    assert parsed["user"] == "trading"
    assert parsed["password"] == "segredo@2026"
    assert parsed["port"] == 5432
    assert parsed["dbname"] == "trading"


def test_open_candle_is_dropped() -> None:
    step = 60 * 60 * 1000
    start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    now = datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc)
    payload = [_kline(start, step, "10"), _kline(start + step, step, "11"), _kline(start + 2 * step, step, "12")]
    candles = parse_closed_klines(payload, now=now, interval="1h")
    assert [candle.close for candle in candles] == [Decimal("10"), Decimal("11")]


def test_public_fetch_uses_klines_and_no_order(monkeypatch) -> None:
    seen: list[str] = []
    step = 60 * 60 * 1000
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    open_ms = int(start.timestamp() * 1000)

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            if len(seen) > 1:
                return b"[]"
            return json.dumps([_kline(open_ms, step)]).encode()

    def _open(url, timeout):
        del timeout
        seen.append(url)
        return _Response()

    candles = fetch_closed_klines(
        "BTCUSDT",
        "1h",
        start,
        start + timedelta(hours=3),
        now=start + timedelta(hours=3),
        urlopen=_open,
    )
    assert candles[0].close == Decimal("100")
    assert "/api/v3/klines?" in seen[0]
    assert "signature" not in seen[0]
    assert "/api/v3/order" not in seen[0]


def test_note_marks_trend_without_a_volume_filter() -> None:
    candle = Candle(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=Decimal("2"),
    )
    snapshot = IndicatorSnapshot(
        ema_fast=Decimal("100"),
        ema_slow=Decimal("90"),
        rsi=Decimal("48"),
        atr=Decimal("1"),
        avg_volume=Decimal("2"),
        ema50_4h=Decimal("110"),
        atr_4h=Decimal("3"),
    )
    decision = Decision(
        Signal.BUY,
        (
            RuleCheck("ema50_acima_ema200", True),
            RuleCheck("close_4h_acima_ema200", True),
            RuleCheck("ema50_subindo", True),
            RuleCheck("rsi_na_faixa", True),
            RuleCheck("pullback_toca_ema20", True),
            RuleCheck("close_acima_ema20", True),
            RuleCheck("close_acima_maxima", True),
        ),
    )
    note = note_from_decision(candle, snapshot, decision)
    assert note.trend_ok is True
    assert note.volume_ok is True
    assert note.atr == Decimal("3")
    assert note.price_distance == Decimal("0.01")


def test_sync_public_stores_the_run_and_sends_no_order(capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(
            timestamp=start + timedelta(hours=index),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1"),
        )
        for index in range(4)
    ]
    saved: dict = {}

    def _fetch(*args, **kwargs):
        del args, kwargs
        return candles

    def _save(*args, **kwargs):
        del args
        saved.update(kwargs)
        return {"candles": len(kwargs["candles"]), "decisions": len(kwargs["notes"]), "trades": len(kwargs["trades"])}

    monkeypatch.setattr("app.main.fetch_closed_klines", _fetch)
    monkeypatch.setattr("app.main.public_window", lambda days, now: (start, start + timedelta(hours=4), start))
    monkeypatch.setattr("app.main.save_public_run", _save)
    monkeypatch.setattr("app.main.notify_new_operations", lambda *args, **kwargs: 0)
    code = main(["sync-public", "--symbol", "BTCUSDT", "--days", "1", "--capital", "5000"])
    text = capsys.readouterr().out
    assert code == 0
    assert saved["symbol"] == "BTCUSDT"
    assert saved["notes"]
    assert "Paper: nenhuma ordem enviada." in text
    assert "Banco:" in text


def test_next_closed_hour_waits_fifteen_seconds_after_the_hour() -> None:
    assert next_closed_hour(datetime(2026, 9, 28, 5, 49, tzinfo=timezone.utc)) == datetime(
        2026, 9, 28, 6, 0, 15, tzinfo=timezone.utc
    )
    assert next_closed_hour(datetime(2026, 9, 28, 6, 0, 10, tzinfo=timezone.utc)) == datetime(
        2026, 9, 28, 6, 0, 15, tzinfo=timezone.utc
    )
    assert next_closed_hour(datetime(2026, 9, 28, 6, 0, 15, tzinfo=timezone.utc)) == datetime(
        2026, 9, 28, 6, 0, 15, tzinfo=timezone.utc
    )
    assert next_closed_hour(datetime(2026, 9, 28, 6, 0, 16, tzinfo=timezone.utc)) == datetime(
        2026, 9, 28, 7, 0, 15, tzinfo=timezone.utc
    )


def test_resident_runs_the_same_sync_after_the_wait() -> None:
    start = datetime(2026, 9, 28, 5, 49, tzinfo=timezone.utc)
    seen: list[float] = []

    def sync() -> int:
        return 0

    code = run_resident(sync, clock=lambda: start, sleep=seen.append, cycles=1)
    assert code == 0
    assert seen == [675]


def test_resident_flag_keeps_paper_on_btc(monkeypatch) -> None:
    seen: dict = {}

    def _sync(settings, args) -> int:
        seen["symbol"] = args.symbol
        seen["mode"] = settings.mode
        return 0

    monkeypatch.setattr("app.main._sync_public", _sync)
    monkeypatch.setattr("app.main.run_resident", lambda sync: sync())
    code = main(["sync-public", "--resident", "--symbol", "BTCUSDT", "--capital", "5000"])
    assert code == 0
    assert seen["symbol"] == "BTCUSDT"
    assert seen["mode"] is Mode.PAPER


def test_resident_refuses_live(monkeypatch) -> None:
    from app.config.settings import Settings

    monkeypatch.setattr(
        "app.main.Settings",
        lambda: Settings(_env_file=None, mode=Mode.LIVE),
    )
    with pytest.raises(SystemExit, match="MODE=live"):
        main(["sync-public", "--resident", "--symbol", "BTCUSDT"])
