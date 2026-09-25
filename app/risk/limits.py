from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class SymbolFilters:
    tick_size: Decimal
    step_size: Decimal
    min_qty: Decimal
    min_notional: Decimal


@dataclass(frozen=True)
class TradePlan:
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    position_size: Decimal
    quantity: Decimal
    risk_amount: Decimal


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise ValueError("step deve ser positivo")
    units = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return units * step


def align_tick(value: Decimal, tick: Decimal) -> Decimal:
    return floor_to_step(value, tick)
