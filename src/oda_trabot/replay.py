from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .approval import ApprovalDecision, CandidateApprover
from .contract import TradingContract
from .models import FeatureSnapshot
from .pipeline import PipelineSignal, SignalPipelineShell
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class ReplayRecord:
    signal: PipelineSignal
    approval: ApprovalDecision


@dataclass(frozen=True)
class ReplaySummary:
    snapshots_seen: int
    raw_signals: int
    approved_signals: int
    rejected_signals: int
    approvals_by_workflow: dict[str, int]
    rejections_by_reason: dict[str, int]


class ReplayEngine:
    def __init__(self, contract: TradingContract, strategy_pack: StrategyPack | None = None) -> None:
        self._strategy_pack = strategy_pack or load_strategy_pack()
        self._pipeline = SignalPipelineShell(contract, strategy_pack=self._strategy_pack)
        self._approver = CandidateApprover(contract)

    def run(self, snapshots: list[FeatureSnapshot]) -> tuple[ReplaySummary, tuple[ReplayRecord, ...]]:
        records: list[ReplayRecord] = []
        approvals_by_workflow: Counter[str] = Counter()
        rejections_by_reason: Counter[str] = Counter()

        for snapshot in snapshots:
            for signal in self._pipeline.scan(snapshot):
                approval = self._approver.evaluate(signal.as_candidate())
                records.append(ReplayRecord(signal=signal, approval=approval))
                if approval.approved:
                    approvals_by_workflow[signal.workflow] += 1
                else:
                    for reason in approval.reasons:
                        rejections_by_reason[reason] += 1

        approved = sum(1 for record in records if record.approval.approved)
        rejected = len(records) - approved
        summary = ReplaySummary(
            snapshots_seen=len(snapshots),
            raw_signals=len(records),
            approved_signals=approved,
            rejected_signals=rejected,
            approvals_by_workflow=dict(approvals_by_workflow),
            rejections_by_reason=dict(rejections_by_reason),
        )
        return summary, tuple(records)

    @staticmethod
    def load_jsonl(path: str | Path) -> list[FeatureSnapshot]:
        lines = Path(path).read_text().splitlines()
        return [FeatureSnapshot.from_dict(json.loads(line)) for line in lines if line.strip()]
