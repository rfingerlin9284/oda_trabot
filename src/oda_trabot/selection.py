from __future__ import annotations

from dataclasses import dataclass

from .approval import CandidateApprover
from .contract import TradingContract
from .pipeline import PipelineSignal, SignalPipelineShell
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class RankedSignal:
    signal: PipelineSignal
    rank_score: float


@dataclass(frozen=True)
class SelectionResult:
    selected: tuple[RankedSignal, ...]
    skipped_reasons: dict[str, str]


class SignalSelector:
    def __init__(self, contract: TradingContract, strategy_pack: StrategyPack | None = None) -> None:
        self._contract = contract
        self._approver = CandidateApprover(contract)
        self._strategy_pack = strategy_pack or load_strategy_pack()

    def rank(self, signal: PipelineSignal) -> RankedSignal:
        workflow_bonus = self._strategy_pack.priority_for(signal.workflow)
        score = (
            signal.confidence * 100.0
            + (signal.votes * 5.0)
            + workflow_bonus
        )
        return RankedSignal(signal=signal, rank_score=round(score, 4))

    def select(
        self,
        signals: tuple[PipelineSignal, ...],
        open_pairs: tuple[str, ...] = (),
        open_slots: int | None = None,
    ) -> SelectionResult:
        available_slots = self._contract.max_positions if open_slots is None else open_slots
        ranked = sorted((self.rank(signal) for signal in signals), key=lambda item: item.rank_score, reverse=True)
        selected: list[RankedSignal] = []
        skipped_reasons: dict[str, str] = {}
        occupied_pairs = set(open_pairs)

        for ranked_signal in ranked:
            signal = ranked_signal.signal
            signal_key = self._signal_key(signal)

            approval = self._approver.evaluate(signal.as_candidate())
            if not approval.approved:
                skipped_reasons[signal_key] = "; ".join(approval.reasons)
                continue

            if len(selected) >= available_slots:
                skipped_reasons[signal_key] = "no open slots remain"
                continue

            if signal.pair in occupied_pairs:
                skipped_reasons[signal_key] = f"pair {signal.pair} is already occupied"
                continue

            occupied_pairs.add(signal.pair)
            selected.append(ranked_signal)

        return SelectionResult(selected=tuple(selected), skipped_reasons=skipped_reasons)

    @staticmethod
    def _signal_key(signal: PipelineSignal) -> str:
        timestamp = signal.observed_at.isoformat()
        return f"{timestamp} {signal.pair} {signal.direction} {signal.workflow}"


def build_cycle_selection(
    contract: TradingContract,
    pipeline: SignalPipelineShell,
    snapshots: tuple,
    open_pairs: tuple[str, ...] = (),
    open_slots: int | None = None,
    strategy_pack: StrategyPack | None = None,
) -> SelectionResult:
    selector = SignalSelector(contract, strategy_pack=strategy_pack)
    signals: list[PipelineSignal] = []
    for snapshot in snapshots:
        signals.extend(pipeline.scan(snapshot))
    return selector.select(tuple(signals), open_pairs=open_pairs, open_slots=open_slots)
