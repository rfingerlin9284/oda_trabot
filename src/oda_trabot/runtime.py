from __future__ import annotations

from dataclasses import dataclass, replace

from .management import ManagedPosition, manage_position
from .oanda import OandaPriceSnapshot, OandaTradeSnapshot
from .runtime_state import ManagedTradeRecord, RuntimeState, adopt_broker_trade
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class RuntimeAction:
    trade_id: str
    pair: str
    action: str
    reason: str
    outcome: str
    suggested_stop_price: float | None = None


def reconcile_state_with_broker(
    state: RuntimeState,
    broker_trades: tuple[OandaTradeSnapshot, ...],
    observed_at_et: str,
) -> tuple[RuntimeState, tuple[RuntimeAction, ...]]:
    broker_ids = {trade.trade_id for trade in broker_trades}
    next_state = state
    actions: list[RuntimeAction] = []

    for record in state.active_trades:
        if record.trade_id not in broker_ids:
            next_state = next_state.close(record.trade_id, observed_at_et, "broker trade no longer open")
            actions.append(
                RuntimeAction(
                    trade_id=record.trade_id,
                    pair=record.pair,
                    action="reconcile_close",
                    reason="trade disappeared from broker open-trade list",
                    outcome="removed from active state",
                )
            )

    for trade in broker_trades:
        if next_state.find(trade.trade_id) is None:
            next_state = next_state.upsert(adopt_broker_trade(trade, observed_at_et))
            actions.append(
                RuntimeAction(
                    trade_id=trade.trade_id,
                    pair=trade.pair,
                    action="adopt",
                    reason="broker trade existed with no local runtime record",
                    outcome="adopted into runtime state",
                )
            )

    return next_state, tuple(actions)


def sync_records_from_broker(
    state: RuntimeState,
    broker_trades: tuple[OandaTradeSnapshot, ...],
    observed_at_et: str,
) -> RuntimeState:
    trade_map = {trade.trade_id: trade for trade in broker_trades}
    synced = state
    for record in state.active_trades:
        trade = trade_map.get(record.trade_id)
        if trade is None:
            continue
        synced = synced.upsert(
            replace(
                record,
                units=trade.units,
                entry_price=trade.entry_price,
                stop_price=trade.stop_price if trade.stop_price is not None else record.stop_price,
                target_price=trade.target_price if trade.target_price is not None else record.target_price,
                last_synced_at_et=observed_at_et,
            )
        )
    return synced


def evaluate_management_actions(
    state: RuntimeState,
    broker_trades: tuple[OandaTradeSnapshot, ...],
    price_map: dict[str, OandaPriceSnapshot],
    strategy_pack: StrategyPack | None = None,
) -> tuple[RuntimeAction, ...]:
    pack = strategy_pack or load_strategy_pack()
    trade_map = {trade.trade_id: trade for trade in broker_trades}
    actions: list[RuntimeAction] = []
    for record in state.active_trades:
        trade = trade_map.get(record.trade_id)
        if trade is None:
            continue
        price = price_map.get(record.pair)
        if price is None:
            actions.append(
                RuntimeAction(
                    trade_id=record.trade_id,
                    pair=record.pair,
                    action="hold",
                    reason="missing live price snapshot",
                    outcome="skipped management for this cycle",
                )
            )
            continue
        if trade.stop_price is None or trade.target_price is None:
            actions.append(
                RuntimeAction(
                    trade_id=record.trade_id,
                    pair=record.pair,
                    action="hold",
                    reason="broker trade is missing stop or target",
                    outcome="skipped management for this cycle",
                )
            )
            continue

        current_price = price.bid if trade.direction == "BUY" else price.ask
        managed = ManagedPosition(
            pair=trade.pair,
            direction=trade.direction,
            entry_price=trade.entry_price,
            current_price=current_price,
            stop_price=trade.stop_price,
            target_price=trade.target_price,
        )
        decision = manage_position(
            managed,
            exit_plan=_record_exit_plan(record, pack),
        )
        actions.append(
            RuntimeAction(
                trade_id=record.trade_id,
                pair=record.pair,
                action=decision.action,
                reason=decision.reason,
                outcome="" if decision.suggested_stop_price is None else f"suggested stop {decision.suggested_stop_price}",
                suggested_stop_price=decision.suggested_stop_price,
            )
        )
    return tuple(actions)


def _record_exit_plan(record: ManagedTradeRecord, strategy_pack: StrategyPack):
    from .management import build_exit_plan_for_profile

    return build_exit_plan_for_profile(record.profile_name, strategy_pack=strategy_pack)
