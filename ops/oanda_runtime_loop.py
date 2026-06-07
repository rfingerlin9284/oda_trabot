from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from oda_trabot import (
    AutonomyCommander,
    CycleEngine,
    CycleResult,
    OpenPosition,
    OrderPreviewBuilder,
    OandaPracticeClient,
    OandaPracticeConfig,
    PHASE1_CONTRACT,
    PortfolioState,
    RuntimeAction,
    TradeMode,
    build_feature_snapshot_from_candles,
    evaluate_peak_giveback,
    evaluate_management_actions,
    load_peak_giveback_state,
    load_management_strategy_pack,
    load_runtime_state,
    parse_oanda_mid_candles,
    reconcile_state_with_broker,
    records_from_submission,
    save_peak_giveback_state,
    save_runtime_state,
    select_active_cartridge,
    sync_records_from_broker,
)

STATE_PATH = Path(__file__).resolve().parents[1] / "state" / "last_runtime_status.json"


def main() -> None:
    sleep_seconds = int(os.getenv("ODA_TRABOT_LOOP_SECONDS", "60"))
    armed = os.getenv("ODA_TRABOT_ALLOW_PAPER_ORDERS", "").upper() == "YES"

    print("ODA_TRABOT RUNTIME LOOP")
    print(f"Loop interval: {sleep_seconds}s")
    print(f"Paper orders armed: {'YES' if armed else 'NO'}")
    print()

    while True:
        try:
            status = run_cycle(armed=armed)
            _write_status(status)
            _print_status(status)
        except Exception as exc:  # noqa: BLE001
            print()
            print(f"[{_now_et()}] runtime error: {exc}")
        time.sleep(sleep_seconds)


def run_cycle(armed: bool) -> dict:
    generated_at_et = _now_et()
    generated_at = datetime.fromisoformat(generated_at_et)
    cartridge = select_active_cartridge(generated_at)
    strategy_pack = cartridge.strategy_pack
    management_strategy_pack = load_management_strategy_pack(cartridge)
    client = OandaPracticeClient(OandaPracticeConfig.from_env_file())
    runtime_state = load_runtime_state()
    prices = client.latest_prices(PHASE1_CONTRACT.trading_pairs)
    price_map = {price.pair: price for price in prices}
    broker_trades = _safe_open_trades(client)
    account = _safe_account_summary(client)
    runtime_state, reconcile_actions = reconcile_state_with_broker(
        runtime_state,
        broker_trades,
        generated_at_et,
    )
    runtime_state = sync_records_from_broker(runtime_state, broker_trades, generated_at_et)
    peak_giveback = None
    peak_giveback_actions = ()
    if account is not None:
        peak_giveback = evaluate_peak_giveback(
            load_peak_giveback_state(),
            nav=account.nav,
            observed_at=generated_at,
        )
        save_peak_giveback_state(peak_giveback.state)
        if peak_giveback.should_flatten:
            runtime_state, peak_giveback_actions = _apply_peak_giveback_flatten(
                client=client,
                runtime_state=runtime_state,
                broker_trades=broker_trades,
                observed_at_et=generated_at_et,
                armed=armed,
                reason=peak_giveback.reason,
            )
            broker_trades = _safe_open_trades(client)
            runtime_state, post_peak_reconcile = reconcile_state_with_broker(
                runtime_state,
                broker_trades,
                generated_at_et,
            )
            runtime_state = sync_records_from_broker(runtime_state, broker_trades, generated_at_et)
            peak_giveback_actions = peak_giveback_actions + post_peak_reconcile
    runtime_state, management_actions = _apply_management_actions(
        client=client,
        runtime_state=runtime_state,
        broker_trades=broker_trades,
        price_map=price_map,
        observed_at_et=generated_at_et,
        armed=armed,
        strategy_pack=management_strategy_pack,
    )

    broker_trades = _safe_open_trades(client)
    runtime_state, post_manage_reconcile = reconcile_state_with_broker(
        runtime_state,
        broker_trades,
        generated_at_et,
    )
    runtime_state = sync_records_from_broker(runtime_state, broker_trades, generated_at_et)
    portfolio = PortfolioState(
        open_positions=tuple(
            OpenPosition(
                pair=trade.pair,
                direction=trade.direction,
                units=trade.units,
                workflow=_workflow_for_trade(runtime_state, trade.trade_id),
            )
            for trade in broker_trades
        )
    )
    snapshots = []
    for pair in PHASE1_CONTRACT.trading_pairs:
        candles = parse_oanda_mid_candles(client.candles(pair, granularity="M15", count=40))
        snapshot = build_feature_snapshot_from_candles(pair, price_map[pair], candles)
        if snapshot is not None:
            snapshots.append(snapshot)

    if strategy_pack is None:
        result = CycleResult(
            snapshots_seen=len(snapshots),
            raw_signals=(),
            planned_trades=(),
            skipped_reasons={"entry_cartridge": cartridge.reason},
        )
        command = None
        previews = []
    else:
        engine = CycleEngine(PHASE1_CONTRACT, strategy_pack=strategy_pack)
        commander = AutonomyCommander(PHASE1_CONTRACT, strategy_pack=strategy_pack)
        preview_builder = OrderPreviewBuilder(strategy_pack=strategy_pack)
        result = engine.run(tuple(snapshots), portfolio=portfolio)
        command = commander.evaluate(
            planned_trades=result.planned_trades,
            snapshots=tuple(snapshots),
            prices=prices,
            observed_at=generated_at,
            account=account,
        )
        previews = [
            preview_builder.build(plan, price_map[plan.pair])
            for plan in command.approved_plans
        ]
    submitted = []
    if armed and command is not None:
        for plan, preview in zip(command.approved_plans, previews, strict=True):
            response = client.place_market_order(preview.to_oanda_payload())
            records = records_from_submission(plan, preview, response, generated_at_et)
            for record in records:
                runtime_state = runtime_state.upsert(record)
            submitted.append(
                {
                    "pair": preview.pair,
                    "direction": preview.direction,
                    "units": preview.units,
                    "trade_ids": [record.trade_id for record in records],
                    "response_keys": sorted(response.keys()),
                }
            )

    save_runtime_state(runtime_state)

    return {
        "generated_at_et": generated_at_et,
        "armed": armed,
        "active_cartridge": {
            "routing_mode": cartridge.routing_mode,
            "entry_allowed": cartridge.entry_allowed,
            "window_id": None if cartridge.window is None else cartridge.window.window_id,
            "reason": cartridge.reason,
        },
        "strategy_pack": {
            "pack_id": cartridge.pack_id,
            "label": cartridge.label,
            "source_path": "" if strategy_pack is None else str(strategy_pack.source_path),
        },
        "management_strategy_pack": {
            "pack_id": management_strategy_pack.pack_id,
            "label": management_strategy_pack.label,
        },
        "open_positions": [asdict(trade) for trade in broker_trades],
        "state_active_trades": [asdict(record) for record in runtime_state.active_trades],
        "cycle_summary": CycleEngine.plain_english_summary(result),
        "commander": {
            "market_open": AutonomyCommander(PHASE1_CONTRACT, strategy_pack=management_strategy_pack).market_is_open(generated_at)
            if command is None
            else command.market_open,
            "bad_spread_regime": False if command is None else command.bad_spread_regime,
            "status": TradeMode.NO_TRADE.value if command is None else command.status.value,
            "reasons": [cartridge.reason] if command is None else list(command.reasons),
            "decisions": [] if command is None else [asdict(decision) for decision in command.plan_decisions],
        },
        "peak_giveback": None if peak_giveback is None else {
            "action": peak_giveback.action,
            "reason": peak_giveback.reason,
            "session_gain_usd": peak_giveback.session_gain_usd,
            "giveback_from_peak_usd": peak_giveback.giveback_from_peak_usd,
            "state": asdict(peak_giveback.state),
        },
        "engine_planned_trades": [asdict(plan) for plan in result.planned_trades],
        "reconcile_actions": [asdict(action) for action in reconcile_actions],
        "post_manage_reconcile": [asdict(action) for action in post_manage_reconcile],
        "management_actions": [asdict(action) for action in management_actions],
        "peak_giveback_actions": [asdict(action) for action in peak_giveback_actions],
        "planned_trades": [
            {
                "pair": preview.pair,
                "direction": preview.direction,
                "units": preview.units,
                "entry_price": preview.entry_price,
                "stop_price": preview.stop_price,
                "target_price": preview.target_price,
                "profile_name": preview.exit_plan.profile_name,
            }
            for preview in previews
        ],
        "submitted": submitted,
    }


def _write_status(status: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(status, indent=2))


def _print_status(status: dict) -> None:
    print()
    print(f"[{status['generated_at_et']}] cycle complete")
    if status.get("active_cartridge"):
        cartridge = status["active_cartridge"]
        print(
            "Active cartridge: "
            f"{cartridge['window_id'] or 'manage_only'} "
            f"({'entries allowed' if cartridge['entry_allowed'] else 'manage only'})"
        )
        print(f"- {cartridge['reason']}")
    print(f"Strategy pack: {status['strategy_pack']['pack_id']}")
    if status.get("management_strategy_pack"):
        print(f"Management pack: {status['management_strategy_pack']['pack_id']}")
    print(status["cycle_summary"])
    if status.get("commander"):
        commander = status["commander"]
        print()
        print(
            "Commander: "
            f"{commander['status']} "
            f"(market_open={'YES' if commander['market_open'] else 'NO'}, "
            f"bad_spread={'YES' if commander['bad_spread_regime'] else 'NO'})"
        )
        for reason in commander["reasons"]:
            print(f"- {reason}")
        if commander["decisions"]:
            print("Commander decisions:")
            for decision in commander["decisions"]:
                reasons = "; ".join(decision["reasons"])
                print(
                    f"- {decision['pair']} {decision['direction']} {decision['workflow']}: "
                    f"{decision['action']} as {decision['mode']} ({reasons})"
                )
    if status.get("peak_giveback"):
        peak = status["peak_giveback"]
        print()
        print(
            "Peak giveback: "
            f"{peak['action']} "
            f"(gain ${peak['session_gain_usd']:.2f}, "
            f"giveback ${peak['giveback_from_peak_usd']:.2f})"
        )
        print(f"- {peak['reason']}")
    if status["reconcile_actions"]:
        print()
        print("Reconcile actions:")
        for action in status["reconcile_actions"]:
            print(f"- {action['pair']} {action['action']}: {action['reason']} -> {action['outcome']}")
    if status.get("peak_giveback_actions"):
        print()
        print("Peak giveback actions:")
        for action in status["peak_giveback_actions"]:
            print(f"- {action['pair']} {action['action']}: {action['reason']} -> {action['outcome']}")
    if status["management_actions"]:
        print()
        print("Management actions:")
        for action in status["management_actions"]:
            print(f"- {action['pair']} {action['action']}: {action['reason']} -> {action['outcome']}")
    if status["planned_trades"]:
        print()
        print("Preview orders:")
        for preview in status["planned_trades"]:
            print(
                f"- {preview['pair']} {preview['direction']} {preview['units']:,} units "
                f"entry {preview['entry_price']} stop {preview['stop_price']} "
                f"target {preview['target_price']} profile {preview['profile_name']}"
            )
    if status["submitted"]:
        print()
        print("Submitted this cycle:")
        for item in status["submitted"]:
            print(
                f"- {item['pair']} {item['direction']} {item['units']:,} units "
                f"response keys: {', '.join(item['response_keys'])}"
            )


def _safe_positions(client: OandaPracticeClient):
    try:
        return client.open_positions()
    except Exception:
        return ()


def _safe_account_summary(client: OandaPracticeClient):
    try:
        return client.account_summary()
    except Exception:
        return None


def _safe_open_trades(client: OandaPracticeClient):
    try:
        return client.open_trades()
    except Exception:
        return ()


def _workflow_for_trade(runtime_state, trade_id: str) -> str:
    record = runtime_state.find(trade_id)
    return "live_broker_position" if record is None else record.workflow


def _apply_management_actions(
    *,
    client: OandaPracticeClient,
    runtime_state,
    broker_trades,
    price_map,
    observed_at_et: str,
    armed: bool,
    strategy_pack,
):
    actions = evaluate_management_actions(runtime_state, broker_trades, price_map, strategy_pack=strategy_pack)
    next_state = runtime_state
    applied = []
    for action in actions:
        record = next_state.find(action.trade_id)
        if record is None:
            applied.append(action)
            continue

        if action.action == "move_stop" and action.suggested_stop_price is not None:
            if armed:
                response = client.replace_stop_loss(record.trade_id, record.pair, action.suggested_stop_price)
                outcome = f"broker stop updated ({', '.join(sorted(response.keys()))})"
                next_state = next_state.upsert(
                    replace(
                        record,
                        stop_price=action.suggested_stop_price,
                        last_synced_at_et=observed_at_et,
                        last_action="move_stop",
                    )
                )
            else:
                outcome = "preview only; broker stop not changed"
                next_state = next_state.upsert(
                    replace(
                        record,
                        last_synced_at_et=observed_at_et,
                        last_action="preview_move_stop",
                    )
                )
            applied.append(
                replace(
                    action,
                    outcome=outcome,
                )
            )
            continue

        if action.action.startswith("close"):
            if armed:
                response = client.close_trade(record.trade_id)
                outcome = f"broker close submitted ({', '.join(sorted(response.keys()))})"
                next_state = next_state.close(record.trade_id, observed_at_et, action.reason)
            else:
                outcome = "preview only; broker trade not closed"
                next_state = next_state.upsert(
                    replace(
                        record,
                        last_synced_at_et=observed_at_et,
                        last_action="preview_close",
                    )
                )
            applied.append(replace(action, outcome=outcome))
            continue

        next_state = next_state.upsert(
            replace(
                record,
                last_synced_at_et=observed_at_et,
                last_action=action.action,
            )
        )
        applied.append(action)
    return next_state, tuple(applied)


def _apply_peak_giveback_flatten(
    *,
    client: OandaPracticeClient,
    runtime_state,
    broker_trades,
    observed_at_et: str,
    armed: bool,
    reason: str,
):
    next_state = runtime_state
    actions = []
    for trade in broker_trades:
        if armed:
            response = client.close_trade(trade.trade_id)
            outcome = f"broker close submitted ({', '.join(sorted(response.keys()))})"
            next_state = next_state.close(trade.trade_id, observed_at_et, reason)
        else:
            outcome = "preview only; broker trade not closed"
        actions.append(
            RuntimeAction(
                trade_id=trade.trade_id,
                pair=trade.pair,
                action="close_peak_giveback",
                reason=reason,
                outcome=outcome,
            )
        )
    return next_state, tuple(actions)


def _now_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).isoformat()


if __name__ == "__main__":
    main()
