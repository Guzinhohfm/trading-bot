from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from app.config.settings import Mode, Settings


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class Order:
    client_order_id: str
    side: str
    quantity: Decimal
    market_price: Decimal
    effective_price: Decimal
    fee: Decimal
    slippage_cost: Decimal
    status: OrderStatus
    created_at: datetime


@dataclass
class OpenPosition:
    quantity: Decimal
    entry_market: Decimal
    entry_effective: Decimal
    entry_fee: Decimal
    stop: Decimal
    take_profit: Decimal
    opened_at: datetime


@dataclass(frozen=True)
class ClosedTrade:
    quantity: Decimal
    entry_market: Decimal
    exit_market: Decimal
    gross_pnl: Decimal
    fees: Decimal
    slippage: Decimal
    net_pnl: Decimal
    reason: str
    opened_at: datetime
    closed_at: datetime


class BacktestBroker:
    """Simula fills. A ordem nasce CREATED e so vira FILLED apos taxa e slippage."""

    def __init__(self, cash: Decimal, settings: Settings) -> None:
        self.cash = cash
        self.settings = settings
        self.orders: list[Order] = []

    def equity(self, position: OpenPosition | None, mark: Decimal) -> Decimal:
        if position is None:
            return self.cash
        return self.cash + mark * position.quantity

    def open_long(
        self,
        market_price: Decimal,
        quantity: Decimal,
        stop: Decimal,
        take_profit: Decimal,
        at: datetime,
    ) -> tuple[OpenPosition, Order]:
        effective = market_price * (Decimal(1) + self.settings.slippage)
        notional = effective * quantity
        fee = notional * self.settings.fee_rate
        slippage_cost = (effective - market_price) * quantity
        order = Order(
            client_order_id=uuid4().hex,
            side="BUY",
            quantity=quantity,
            market_price=market_price,
            effective_price=effective,
            fee=fee,
            slippage_cost=slippage_cost,
            status=OrderStatus.CREATED,
            created_at=at,
        )
        order.status = OrderStatus.SUBMITTED
        self.cash -= notional + fee
        order.status = OrderStatus.FILLED
        self.orders.append(order)
        position = OpenPosition(
            quantity=quantity,
            entry_market=market_price,
            entry_effective=effective,
            entry_fee=fee,
            stop=stop,
            take_profit=take_profit,
            opened_at=at,
        )
        return position, order

    def close_long(
        self,
        position: OpenPosition,
        market_price: Decimal,
        at: datetime,
        reason: str,
    ) -> ClosedTrade:
        effective = market_price * (Decimal(1) - self.settings.slippage)
        notional = effective * position.quantity
        fee = notional * self.settings.fee_rate
        exit_slippage = (market_price - effective) * position.quantity
        order = Order(
            client_order_id=uuid4().hex,
            side="SELL",
            quantity=position.quantity,
            market_price=market_price,
            effective_price=effective,
            fee=fee,
            slippage_cost=exit_slippage,
            status=OrderStatus.CREATED,
            created_at=at,
        )
        order.status = OrderStatus.SUBMITTED
        self.cash += notional - fee
        order.status = OrderStatus.FILLED
        self.orders.append(order)
        gross = (market_price - position.entry_market) * position.quantity
        slippage = (position.entry_effective - position.entry_market) * position.quantity + exit_slippage
        fees = position.entry_fee + fee
        net = gross - fees - slippage
        return ClosedTrade(
            quantity=position.quantity,
            entry_market=position.entry_market,
            exit_market=market_price,
            gross_pnl=gross,
            fees=fees,
            slippage=slippage,
            net_pnl=net,
            reason=reason,
            opened_at=position.opened_at,
            closed_at=at,
        )


def resolve_intrabar(
    open_price: Decimal,
    high: Decimal,
    low: Decimal,
    stop: Decimal,
    take_profit: Decimal,
) -> tuple[Decimal, str] | None:
    """Se stop e take profit caem no mesmo candle, o stop sai na frente."""
    if low <= stop:
        price = open_price if open_price < stop else stop
        return price, "stop"
    if high >= take_profit:
        price = open_price if open_price > take_profit else take_profit
        return price, "take_profit"
    return None
