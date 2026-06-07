from __future__ import annotations

from pathlib import Path

from oda_trabot import CycleEngine, PHASE1_CONTRACT, SignalSelector, load_strategy_pack
from oda_trabot.replay import ReplayEngine


def main() -> None:
    strategy_pack = load_strategy_pack()
    engine = ReplayEngine(PHASE1_CONTRACT, strategy_pack=strategy_pack)
    cycle_engine = CycleEngine(PHASE1_CONTRACT, strategy_pack=strategy_pack)
    selector = SignalSelector(PHASE1_CONTRACT, strategy_pack=strategy_pack)
    fixture_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "replay_input.jsonl"
    snapshots = engine.load_jsonl(fixture_path)
    summary, records = engine.run(snapshots)
    selection = selector.select(tuple(record.signal for record in records), open_slots=2)
    cycle_result = cycle_engine.run(tuple(snapshots))

    print("ODA_TRABOT REPLAY DEMO")
    print()
    print(f"Strategy pack: {strategy_pack.pack_id}")
    print()
    print(f"Snapshots checked: {summary.snapshots_seen}")
    print(f"Raw signals found: {summary.raw_signals}")
    print(f"Approved signals: {summary.approved_signals}")
    print(f"Rejected signals: {summary.rejected_signals}")
    print()
    print("Approved signals by workflow:")
    if summary.approvals_by_workflow:
        for workflow, count in sorted(summary.approvals_by_workflow.items()):
            print(f"- {workflow}: {count}")
    else:
        print("- none")
    print()
    print("Top selections with 2 open slots:")
    if selection.selected:
        for ranked in selection.selected:
            signal = ranked.signal
            print(
                f"- TAKE {signal.pair} {signal.direction} {signal.workflow} "
                f"| confidence {signal.confidence:.2f} | votes {signal.votes} | rank {ranked.rank_score:.2f}"
            )
    else:
        print("- none")
    print()
    print("Recent signal decisions:")
    for record in records:
        status = "APPROVED" if record.approval.approved else "REJECTED"
        print(
            f"- {record.signal.pair} {record.signal.direction} {record.signal.workflow} "
            f"{record.signal.confidence:.2f} with {record.signal.votes} votes -> {status}"
        )
        if record.approval.reasons:
            for reason in record.approval.reasons:
                print(f"  reason: {reason}")

    print()
    print(CycleEngine.plain_english_summary(cycle_result))


if __name__ == "__main__":
    main()
