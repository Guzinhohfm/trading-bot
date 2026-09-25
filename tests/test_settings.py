from decimal import Decimal

import pytest

from app.config.settings import Mode, Settings, get_settings


def test_defaults_match_the_spec() -> None:
    settings = get_settings()
    assert settings.symbol_list == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert settings.timeframe == "5m"
    assert settings.ema_fast == 20
    assert settings.ema_slow == 50
    assert settings.slippage == Decimal("0.0005")
    assert settings.max_daily_loss == Decimal("0.03")
    assert settings.capital == Decimal("5000")
    assert settings.database_url.startswith("postgresql+")


def test_live_mode_requires_an_explicit_flag() -> None:
    settings = get_settings(mode=Mode.LIVE, live_enabled=False)
    with pytest.raises(RuntimeError):
        settings.assert_live_allowed()
    get_settings(mode=Mode.LIVE, live_enabled=True).assert_live_allowed()


def test_env_file_is_optional_for_constructed_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAPITAL", "42")
    loaded = Settings(_env_file=None)
    assert loaded.capital == Decimal("42")
