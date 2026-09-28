from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.market.candles import Candle, IndicatorSnapshot


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class RuleCheck:
    code: str
    passed: bool


@dataclass(frozen=True)
class Decision:
    signal: Signal
    checks: tuple[RuleCheck, ...]

    @property
    def failed(self) -> tuple[str, ...]:
        return tuple(check.code for check in self.checks if not check.passed)


class Strategy(Protocol):
    def analyze(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position_open: bool,
    ) -> Signal:
        """Le somente mercado. Risco, saldo e ordens ficam fora daqui."""
