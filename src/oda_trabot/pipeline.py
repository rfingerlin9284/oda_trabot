from __future__ import annotations

from dataclasses import dataclass

from .approval import SignalCandidate
from .contract import TradingContract
from .models import FeatureSnapshot
from .router import SessionRouter
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class PipelineSignal:
    pair: str
    direction: str
    workflow: str
    votes: int
    confidence: float
    observed_at: object
    rationale: tuple[str, ...]

    def as_candidate(self) -> SignalCandidate:
        return SignalCandidate(
            pair=self.pair,
            direction=self.direction,
            workflow=self.workflow,
            votes=self.votes,
            confidence=self.confidence,
            observed_at=self.observed_at,
        )


class SignalPipelineShell:
    def __init__(self, contract: TradingContract, strategy_pack: StrategyPack | None = None) -> None:
        self._contract = contract
        self._router = SessionRouter(contract)
        self._strategy_pack = strategy_pack or load_strategy_pack()

    def scan(self, snapshot: FeatureSnapshot) -> tuple[PipelineSignal, ...]:
        route = self._router.route(snapshot.observed_at)
        if not route.can_trade:
            return ()
        if not snapshot.broker_tradable:
            return ()

        signals: list[PipelineSignal] = []
        for workflow in route.active_workflows:
            signal = self._evaluate_workflow(workflow, snapshot)
            if signal is not None:
                signals.append(signal)
        return tuple(signals)

    def _evaluate_workflow(
        self,
        workflow: str,
        snapshot: FeatureSnapshot,
    ) -> PipelineSignal | None:
        evaluation = self._strategy_pack.evaluate(workflow, snapshot)
        if evaluation is None:
            return None
        return PipelineSignal(
            pair=snapshot.pair,
            direction=snapshot.direction,
            workflow=evaluation.workflow,
            votes=evaluation.votes,
            confidence=evaluation.confidence,
            observed_at=snapshot.observed_at,
            rationale=evaluation.rationale,
        )
