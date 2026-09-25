from dataclasses import dataclass
from decimal import Decimal

from app.config.settings import Settings, get_settings
from app.risk.limits import SymbolFilters, TradePlan, align_tick, floor_to_step


@dataclass(frozen=True)
class AccountState:
    capital: Decimal
    available_capital: Decimal
    daily_pnl: Decimal
    day_start_equity: Decimal
    position_open: bool
    kill_switch: bool


@dataclass(frozen=True)
class RiskVerdict:
    accepted: bool
    reason: str
    plan: TradePlan | None


class RiskManager:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def calculate_trade(
        self,
        entry_price: Decimal,
        atr: Decimal,
        capital: Decimal,
        available_capital: Decimal | None = None,
    ) -> TradePlan:
        settings = self.settings
        available = capital if available_capital is None else available_capital
        stop_distance = atr * settings.stop_atr_multiplier
        stop_price = entry_price - stop_distance
        risk_amount = capital * settings.risk_per_trade
        stop_distance_pct = stop_distance / entry_price
        raw_size = risk_amount / stop_distance_pct
        position_size = min(raw_size, available)
        take_profit = entry_price + stop_distance * settings.reward_multiple
        quantity = position_size / entry_price
        return TradePlan(
            entry=entry_price,
            stop=stop_price,
            take_profit=take_profit,
            position_size=position_size,
            quantity=quantity,
            risk_amount=risk_amount,
        )

    def daily_loss_breached(self, account: AccountState) -> bool:
        limit = self.settings.max_daily_loss * account.day_start_equity
        return account.daily_pnl <= -limit

    def approve_entry(
        self,
        entry_price: Decimal,
        atr: Decimal,
        account: AccountState,
        filters: SymbolFilters,
    ) -> RiskVerdict:
        if account.kill_switch:
            return RiskVerdict(False, "kill_switch", None)
        if account.position_open:
            return RiskVerdict(False, "position_open", None)
        if self.daily_loss_breached(account):
            return RiskVerdict(False, "daily_loss", None)
        if account.available_capital <= 0 or entry_price <= 0:
            return RiskVerdict(False, "no_capital", None)
        if atr <= 0:
            return RiskVerdict(False, "no_capital", None)
        if atr * self.settings.stop_atr_multiplier <= 0:
            return RiskVerdict(False, "invalid_stop", None)

        raw = self.calculate_trade(
            entry_price,
            atr,
            account.capital,
            account.available_capital,
        )
        stop = align_tick(raw.stop, filters.tick_size)
        take_profit = align_tick(raw.take_profit, filters.tick_size)
        if entry_price <= stop:
            return RiskVerdict(False, "invalid_stop", None)

        quantity = floor_to_step(raw.position_size / entry_price, filters.step_size)
        if quantity < filters.min_qty or quantity * entry_price < filters.min_notional:
            return RiskVerdict(False, "no_capital", None)

        position_size = min(quantity * entry_price, account.available_capital)
        plan = TradePlan(
            entry=entry_price,
            stop=stop,
            take_profit=take_profit,
            position_size=position_size,
            quantity=quantity,
            risk_amount=raw.risk_amount,
        )
        return RiskVerdict(True, "accepted", plan)
