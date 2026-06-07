from __future__ import annotations

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
    parse_oanda_mid_candles,
)


def main() -> None:
    strategy_pack = load_strategy_pack()
    client = OandaPracticeClient(OandaPracticeConfig.from_env_file())
    engine = CycleEngine(PHASE1_CONTRACT, strategy_pack=strategy_pack)
    preview_builder = OrderPreviewBuilder(strategy_pack=strategy_pack)
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
    print("ODA_TRABOT LIVE CYCLE PREVIEW")
    print()
    print(f"Strategy pack: {strategy_pack.pack_id}")
    print(f"Live open positions seen: {len(live_positions)}")
    if live_positions:
        for position in live_positions:
            print(
                f"- {position.pair} {position.direction} {position.units:,} units "
                f"| P&L ${position.unrealized_pl:.2f}"
            )
        print()
    print(CycleEngine.plain_english_summary(result))
    if result.planned_trades:
        print()
        print("Order previews:")
        for plan in result.planned_trades:
            preview = preview_builder.build(plan, price_map[plan.pair])
            print(
                f"- {preview.pair} {preview.direction} {preview.units:,} units "
                f"entry {preview.entry_price} stop {preview.stop_price} target {preview.target_price} "
                f"profile {preview.exit_plan.profile_name}"
            )


def _safe_positions(client: OandaPracticeClient):
    try:
        return client.open_positions()
    except Exception:
        return ()


if __name__ == "__main__":
    main()
