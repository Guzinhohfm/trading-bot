from decimal import Decimal
from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Mode(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT"
    timeframe: str = "5m"
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_period: int = 14
    rsi_min: Decimal = Decimal("35")
    rsi_max: Decimal = Decimal("55")
    atr_period: int = 14
    volume_period: int = 20
    price_distance_max: Decimal = Decimal("0.01")
    stop_atr_multiplier: Decimal = Decimal("1.5")
    reward_multiple: Decimal = Decimal("2")
    risk_per_trade: Decimal = Decimal("0.01")
    max_daily_loss: Decimal = Decimal("0.03")
    fee_rate: Decimal = Decimal("0.001")
    slippage: Decimal = Decimal("0.0005")
    mode: Mode = Mode.BACKTEST
    capital: Decimal = Decimal("5000")
    live_enabled: bool = False
    database_url: str = "postgresql+psycopg://trading:change-me@db:5432/trading"
    binance_api_key: str = ""
    binance_secret_key: str = ""
    tick_size: Decimal = Decimal("0.01")
    step_size: Decimal = Decimal("0.00001")
    min_qty: Decimal = Decimal("0.00001")
    min_notional: Decimal = Decimal("5")

    @field_validator(
        "rsi_min",
        "rsi_max",
        "price_distance_max",
        "stop_atr_multiplier",
        "reward_multiple",
        "risk_per_trade",
        "max_daily_loss",
        "fee_rate",
        "slippage",
        "capital",
        "tick_size",
        "step_size",
        "min_qty",
        "min_notional",
        mode="before",
    )
    @classmethod
    def _as_decimal(cls, value: object) -> object:
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, str):
            return Decimal(value)
        return value

    @property
    def symbol_list(self) -> list[str]:
        return [item.strip() for item in self.symbols.split(",") if item.strip()]

    def assert_live_allowed(self) -> None:
        if self.mode is Mode.LIVE and not self.live_enabled:
            raise RuntimeError("Modo live exige LIVE_ENABLED=true.")


def get_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]
