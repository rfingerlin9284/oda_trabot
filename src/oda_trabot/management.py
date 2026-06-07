from __future__ import annotations

from dataclasses import dataclass

from .planning import TradePlan
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class ExitPlan:
    stop_pips: float
    target_pips: float
    green_lock_pips: float
    green_lock_min_profit_pips: float
    profile_name: str


@dataclass(frozen=True)
class ManagedPosition:
    pair: str
    direction: str
    entry_price: float
    current_price: float
    stop_price: float
    target_price: float


@dataclass(frozen=True)
class ManagementDecision:
    action: str
    reason: str
    suggested_stop_price: float | None = None

    @property
    def should_close(self) -> bool:
        return self.action.startswith("close")


def build_exit_plan(plan: TradePlan, strategy_pack: StrategyPack | None = None) -> ExitPlan:
    pack = strategy_pack or load_strategy_pack()
    return exit_plan_from_profile(pack.exit_profile_for_workflow(plan.workflow))


def build_exit_plan_for_profile(profile_name: str, strategy_pack: StrategyPack | None = None) -> ExitPlan:
    pack = strategy_pack or load_strategy_pack()
    return exit_plan_from_profile(pack.exit_profile_named(profile_name))


def exit_plan_from_profile(profile) -> ExitPlan:
    return ExitPlan(
        stop_pips=profile.stop_pips,
        target_pips=profile.target_pips,
        green_lock_pips=profile.green_lock_pips,
        green_lock_min_profit_pips=profile.green_lock_min_profit_pips,
        profile_name=profile.profile_name,
    )


def manage_position(position: ManagedPosition, exit_plan: ExitPlan) -> ManagementDecision:
    pip = _pip_size(position.pair)
    profit_pips = _profit_pips(position, pip)

    if _hit_target(position):
        return ManagementDecision(action="close_target", reason="target reached")
    if _hit_stop(position):
        return ManagementDecision(action="close_stop", reason="stop reached")
    if profit_pips >= exit_plan.green_lock_min_profit_pips:
        lock_stop = _green_lock_stop(position, exit_plan.green_lock_pips, pip)
        improved_stop = _is_improved_stop(position, lock_stop)
        if improved_stop:
            return ManagementDecision(
                action="move_stop",
                reason="green lock armed",
                suggested_stop_price=round(lock_stop, 5 if pip == 0.0001 else 3),
            )
    return ManagementDecision(action="hold", reason="trade is still inside the working range")


def _profit_pips(position: ManagedPosition, pip: float) -> float:
    if position.direction == "BUY":
        return (position.current_price - position.entry_price) / pip
    return (position.entry_price - position.current_price) / pip


def _green_lock_stop(position: ManagedPosition, green_lock_pips: float, pip: float) -> float:
    if position.direction == "BUY":
        return position.entry_price + (green_lock_pips * pip)
    return position.entry_price - (green_lock_pips * pip)


def _is_improved_stop(position: ManagedPosition, candidate_stop: float) -> bool:
    if position.direction == "BUY":
        return candidate_stop > position.stop_price
    return candidate_stop < position.stop_price


def _hit_target(position: ManagedPosition) -> bool:
    if position.direction == "BUY":
        return position.current_price >= position.target_price
    return position.current_price <= position.target_price


def _hit_stop(position: ManagedPosition) -> bool:
    if position.direction == "BUY":
        return position.current_price <= position.stop_price
    return position.current_price >= position.stop_price


def _pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 0.0001
