from __future__ import annotations

from dataclasses import dataclass

from .contract import TradingContract
from .pipeline import PipelineSignal
from .portfolio import PortfolioState
from .selection import RankedSignal, SelectionResult, SignalSelector
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class TradePlan:
    pair: str
    direction: str
    workflow: str
    units: int
    confidence: float
    votes: int
    rank_score: float
    rationale: tuple[str, ...]


class PositionSizer:
    def __init__(self, contract: TradingContract, strategy_pack: StrategyPack | None = None) -> None:
        self._contract = contract
        self._strategy_pack = strategy_pack or load_strategy_pack()

    def units_for(self, signal: PipelineSignal) -> int:
        multiplier = self._strategy_pack.units_multiplier_for(signal.confidence, signal.votes)
        return int(self._contract.base_units * multiplier)


class TradePlanner:
    def __init__(self, contract: TradingContract, strategy_pack: StrategyPack | None = None) -> None:
        self._contract = contract
        self._strategy_pack = strategy_pack or load_strategy_pack()
        self._selector = SignalSelector(contract, strategy_pack=self._strategy_pack)
        self._sizer = PositionSizer(contract, strategy_pack=self._strategy_pack)

    def plan(
        self,
        signals: tuple[PipelineSignal, ...],
        portfolio: PortfolioState,
    ) -> tuple[TradePlan, ...]:
        open_slots = min(
            portfolio.open_slots(self._contract),
            self._contract.max_new_trades_per_cycle,
        )
        selection = self._selector.select(
            signals,
            open_pairs=portfolio.open_pairs,
            open_slots=open_slots,
        )
        return tuple(self._to_trade_plan(ranked) for ranked in selection.selected)

    def selection_result(
        self,
        signals: tuple[PipelineSignal, ...],
        portfolio: PortfolioState,
    ) -> SelectionResult:
        open_slots = min(
            portfolio.open_slots(self._contract),
            self._contract.max_new_trades_per_cycle,
        )
        return self._selector.select(
            signals,
            open_pairs=portfolio.open_pairs,
            open_slots=open_slots,
        )

    def _to_trade_plan(self, ranked: RankedSignal) -> TradePlan:
        signal = ranked.signal
        return TradePlan(
            pair=signal.pair,
            direction=signal.direction,
            workflow=signal.workflow,
            units=self._sizer.units_for(signal),
            confidence=signal.confidence,
            votes=signal.votes,
            rank_score=ranked.rank_score,
            rationale=signal.rationale,
        )
