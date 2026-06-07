from __future__ import annotations

from oda_trabot import OandaPracticeClient, OandaPracticeConfig, PHASE1_CONTRACT


def main() -> None:
    config = OandaPracticeConfig.from_env_file()
    client = OandaPracticeClient(config)

    account = _safe_call(client.account_summary, "account summary")
    positions = _safe_call(client.open_positions, "open positions")
    prices = _safe_call(
        lambda: client.latest_prices(PHASE1_CONTRACT.trading_pairs),
        "latest prices",
    )

    print("ODA_TRABOT OANDA PRACTICE PROBE")
    print()
    if isinstance(account, Exception):
        print(f"Account summary: FAILED - {account}")
    else:
        print(f"Account: {account.account_id}")
        print(f"Balance: ${account.balance:.2f}")
        print(f"NAV: ${account.nav:.2f}")
        print(f"Unrealized P&L: ${account.unrealized_pl:.2f}")
        print(f"Margin used: ${account.margin_used:.2f}")
        print(f"Margin available: ${account.margin_available:.2f}")
        print(f"Open trades: {account.open_trade_count}")
        print(f"Open positions: {account.open_position_count}")
    print()
    print("Open positions now:")
    if isinstance(positions, Exception):
        print(f"- FAILED - {positions}")
    elif positions:
        for position in positions:
            print(
                f"- {position.pair} {position.direction} {position.units:,} units "
                f"from {position.average_price} | P&L ${position.unrealized_pl:.2f}"
            )
    else:
        print("- none")
    print()
    print("Current spreads:")
    if isinstance(prices, Exception):
        print(f"- FAILED - {prices}")
    else:
        for price in prices:
            print(
                f"- {price.pair}: bid {price.bid} ask {price.ask} "
                f"spread {price.spread_pips:.2f} pips"
            )


def _safe_call(fn, label: str):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return RuntimeError(f"{label} failed: {exc}")


if __name__ == "__main__":
    main()
