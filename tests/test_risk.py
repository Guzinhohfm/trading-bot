from decimal import Decimal

from app.config.settings import get_settings
from app.risk.limits import SymbolFilters
from app.risk.manager import AccountState, RiskManager


FILTERS = SymbolFilters(
    tick_size=Decimal("0.01"),
    step_size=Decimal("0.00001"),
    min_qty=Decimal("0.00001"),
    min_notional=Decimal("5"),
)


def _account(**overrides: object) -> AccountState:
    values: dict[str, object] = {
        "capital": Decimal("5000"),
        "available_capital": Decimal("5000"),
        "daily_pnl": Decimal("0"),
        "day_start_equity": Decimal("5000"),
        "position_open": False,
        "kill_switch": False,
    }
    values.update(overrides)
    return AccountState(**values)  # type: ignore[arg-type]


def test_calculate_trade_matches_spec_example() -> None:
    plan = RiskManager(get_settings()).calculate_trade(
        Decimal("100000"),
        Decimal("800"),
        Decimal("5000"),
    )
    assert plan.stop == Decimal("98800")
    assert plan.take_profit == Decimal("102400")
    assert plan.risk_amount == Decimal("50")
    assert plan.position_size == Decimal("5000000") / Decimal("1200")


def test_position_size_is_capped_by_available_capital() -> None:
    plan = RiskManager(get_settings()).calculate_trade(
        Decimal("100000"),
        Decimal("800"),
        Decimal("5000"),
        available_capital=Decimal("1000"),
    )
    assert plan.position_size == Decimal("1000")


def test_rejections() -> None:
    risk = RiskManager(get_settings())
    entry = Decimal("100000")
    atr = Decimal("800")
    assert risk.approve_entry(entry, atr, _account(position_open=True), FILTERS).reason == "position_open"
    assert risk.approve_entry(entry, atr, _account(kill_switch=True), FILTERS).reason == "kill_switch"
    assert (
        risk.approve_entry(entry, atr, _account(daily_pnl=Decimal("-150")), FILTERS).reason
        == "daily_loss"
    )
    assert risk.approve_entry(entry, atr, _account(available_capital=Decimal("0")), FILTERS).reason == "no_capital"
    assert risk.approve_entry(entry, Decimal("0"), _account(), FILTERS).reason == "no_capital"


def test_invalid_stop_when_tick_aligns_through_entry() -> None:
    risk = RiskManager(get_settings(stop_atr_multiplier=Decimal("0")))
    verdict = risk.approve_entry(
        Decimal("100"),
        Decimal("1"),
        _account(),
        SymbolFilters(Decimal("1"), Decimal("0.00001"), Decimal("0.00001"), Decimal("5")),
    )
    assert verdict.accepted is False
    assert verdict.reason == "invalid_stop"


def test_accepts_spec_example_and_floors_quantity() -> None:
    verdict = RiskManager(get_settings()).approve_entry(
        Decimal("100000"),
        Decimal("800"),
        _account(),
        FILTERS,
    )
    assert verdict.accepted
    assert verdict.plan is not None
    assert verdict.plan.stop == Decimal("98800")
    assert verdict.plan.take_profit == Decimal("102400")
    assert verdict.plan.quantity == (verdict.plan.position_size / Decimal("100000")).quantize(Decimal("0.00001"))
