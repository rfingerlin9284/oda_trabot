from __future__ import annotations

import os

from oda_trabot import (
    CycleEngine,
    OpenPosition,
    OrderPreviewBuilder,
    OandaPracticeClient,
    OandaPracticeConfig,
    PHASE1_CONTRACT,
    PortfolioState,
    build_feature_snapshot_from_candles,
    load_strategy_pack,
    load_runtime_state,
    parse_oanda_mid_candles,
    records_from_submission,
    save_runtime_state,
)


def main() -> None:
    strategy_pack = load_strategy_pack()
    client = OandaPracticeClient(OandaPracticeConfig.from_env_file())
    engine = CycleEngine(PHASE1_CONTRACT, strategy_pack=strategy_pack)
    preview_builder = OrderPreviewBuilder(strategy_pack=strategy_pack)
    runtime_state = load_runtime_state()
    prices = client.latest_prices(PHASE1_CONTRACT.trading_pairs)
    price_map = {price.pair: price for price in prices}
    live_positions = _safe_positions(client)
    portfolio = PortfolioState(
        open_positions=tuple(
            OpenPosition(
                pair=position.pair,
                direction=position.direction,
                units=position.units,
                workflow="live_broker_position",
            )
            for position in live_positions
        )
    )

    snapshots = []
    for pair in PHASE1_CONTRACT.trading_pairs:
        candles = parse_oanda_mid_candles(client.candles(pair, granularity="M15", count=40))
        snapshot = build_feature_snapshot_from_candles(pair, price_map[pair], candles)
        if snapshot is not None:
            snapshots.append(snapshot)

    result = engine.run(tuple(snapshots), portfolio=portfolio)
    print("ODA_TRABOT PAPER ORDER SUBMISSION")
    print(f"Strategy pack: {strategy_pack.pack_id}")
    print()
    print(CycleEngine.plain_english_summary(result))
    print()

    armed = os.getenv("ODA_TRABOT_ALLOW_PAPER_ORDERS", "").upper() == "YES"
    if not armed:
        print("Submission mode: PREVIEW ONLY")
        print("Set ODA_TRABOT_ALLOW_PAPER_ORDERS=YES to actually place practice orders.")
        return

    if not result.planned_trades:
        print("Submission mode: ARMED, but there are no planned trades right now.")
        return

    print("Submission mode: ARMED")
    for plan in result.planned_trades:
        preview = preview_builder.build(plan, price_map[plan.pair])
        response = client.place_market_order(preview.to_oanda_payload())
        records = records_from_submission(plan, preview, response, _now_et())
        for record in records:
            runtime_state = runtime_state.upsert(record)
        print(
            f"- submitted {preview.pair} {preview.direction} {preview.units:,} units "
            f"at about {preview.entry_price} with stop {preview.stop_price} "
            f"and target {preview.target_price}"
        )
        print(f"  broker response keys: {', '.join(sorted(response.keys()))}")
        if records:
            print(f"  tracked trade ids: {', '.join(record.trade_id for record in records)}")
    save_runtime_state(runtime_state)


def _safe_positions(client: OandaPracticeClient):
    try:
        return client.open_positions()
    except Exception:
        return ()


def _now_et() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/New_York")).isoformat()


if __name__ == "__main__":
    main()
