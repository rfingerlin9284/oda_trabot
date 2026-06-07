from __future__ import annotations

from oda_trabot import (
    dominant_workflows,
    load_counterfactual_windows,
    summarize_windows,
    top_receipts_by_symbol,
)


APRIL14_PATH = (
    "/home/rfing/READ_ONLY_LEGACY/backups/"
    "RESTORED_PRE10AM_TRANSFER_READY_20260430_025439/repos/"
    "OAD_DEV/analysis/oanda_loss_manager_counterfactual_apr14_session_20260421.json"
)
V1C002_PATH = (
    "/home/rfing/READ_ONLY_LEGACY/V1C002_APRIL14_EDGE_REBUILD_20260508/"
    "evidence/candidate_current_session_counterfactuals.json"
)


def print_summary(label: str, path: str) -> None:
    windows = load_counterfactual_windows(path)
    summary = summarize_windows(windows)
    receipts = top_receipts_by_symbol(windows)

    print(label)
    print()
    print(f"Windows loaded: {summary.window_count}")
    print(f"Best window: {summary.best_window_label}")
    print(f"Best window P&L: ${summary.best_window_pnl_usd:.2f}")
    if summary.best_trade:
        print(
            "Best trade: "
            f"{summary.best_trade.symbol} {summary.best_trade.strategy} "
            f"${summary.best_trade.pnl_usd:.2f} at {summary.best_trade.entry_time_et}"
        )
    print()
    print("P&L by strategy:")
    for strategy, pnl in summary.pnl_by_strategy.items():
        print(f"- {strategy}: ${pnl:.2f}")
    print()
    print("Top symbols by P&L:")
    for symbol, pnl in summary.pnl_by_symbol.items():
        print(f"- {symbol}: ${pnl:.2f}")
    print()
    print("Winning workflow counts:")
    for workflow, count in dominant_workflows(windows).items():
        print(f"- {workflow}: {count}")
    print()
    print("Best receipts by symbol:")
    for symbol, trades in receipts.items():
        best = trades[0]
        print(
            f"- {symbol}: {best.strategy} ${best.pnl_usd:.2f} "
            f"at {best.entry_time_et} ({best.source_variant})"
        )
    print()


def main() -> None:
    print("ODA_TRABOT EVIDENCE SUMMARY")
    print()
    print_summary("APRIL 14 BASELINE", APRIL14_PATH)
    print_summary("V1C002 CHALLENGER", V1C002_PATH)


if __name__ == "__main__":
    main()
