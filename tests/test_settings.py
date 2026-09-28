from decimal import Decimal

import pytest

from app.config.settings import Mode, Settings, get_settings


def test_defaults_match_the_spec() -> None:
    settings = get_settings()
    assert settings.symbol_list == ["BTCUSDT"]
    assert settings.timeframe == "1h"
    assert settings.ema_fast == 20
    assert settings.ema_trend == 50
    assert settings.ema_trend_slow == 200
    assert settings.rsi_min == Decimal("40")
    assert settings.slippage == Decimal("0.0005")
    assert settings.stop_pct == Decimal("0.05")
    assert settings.reward_multiple == Decimal("2")
    assert settings.max_daily_loss == Decimal("0.02")
    assert settings.cooldown_hours == 6
    assert settings.validation_passed is False
    assert settings.capital == Decimal("5000")
    assert settings.database_url.startswith("postgresql+")


def test_forward_modes_require_validation_then_live_flag() -> None:
    get_settings(mode=Mode.PAPER).assert_forward_allowed()
    with pytest.raises(RuntimeError, match="VALIDATION_PASSED"):
        get_settings(mode=Mode.TESTNET).assert_forward_allowed()
    with pytest.raises(RuntimeError, match="VALIDATION_PASSED"):
        get_settings(mode=Mode.LIVE).assert_forward_allowed()
    get_settings(mode=Mode.TESTNET, validation_passed=True).assert_forward_allowed()
    with pytest.raises(RuntimeError, match="LIVE_ENABLED"):
        get_settings(mode=Mode.LIVE, validation_passed=True, live_enabled=False).assert_forward_allowed()
    get_settings(mode=Mode.LIVE, validation_passed=True, live_enabled=True).assert_forward_allowed()
    get_settings(mode=Mode.BACKTEST).assert_forward_allowed()


def test_env_file_is_optional_for_constructed_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAPITAL", "42")
    loaded = Settings(_env_file=None)
    assert loaded.capital == Decimal("42")
