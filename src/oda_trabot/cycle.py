from __future__ import annotations

from dataclasses import dataclass

from .contract import TradingContract
from .models import FeatureSnapshot
from .pipeline import PipelineSignal, SignalPipelineShell
from .planning import TradePlan, TradePlanner
from .portfolio import PortfolioState
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class CycleResult:
    snapshots_seen: int
    raw_signals: tuple[PipelineSignal, ...]
    planned_trades: tuple[TradePlan, ...]
    skipped_reasons: dict[str, str]


class CycleEngine:
    def __init__(self, contract: TradingContract, strategy_pack: StrategyPack | None = None) -> None:
        self._contract = contract
        self._strategy_pack = strategy_pack or load_strategy_pack()
        self._pipeline = SignalPipelineShell(contract, strategy_pack=self._strategy_pack)
        self._planner = TradePlanner(contract, strategy_pack=self._strategy_pack)

    def run(
        self,
        snapshots: tuple[FeatureSnapshot, ...],
        portfolio: PortfolioState | None = None,
    ) -> CycleResult:
        portfolio_state = portfolio or PortfolioState()
        raw_signals: list[PipelineSignal] = []
        for snapshot in snapshots:
            raw_signals.extend(self._pipeline.scan(snapshot))

        signals_tuple = tuple(raw_signals)
        selection = self._planner.selection_result(signals_tuple, portfolio_state)
        planned = self._planner.plan(signals_tuple, portfolio_state)
        return CycleResult(
            snapshots_seen=len(snapshots),
            raw_signals=signals_tuple,
            planned_trades=planned,
            skipped_reasons=selection.skipped_reasons,
        )

    @staticmethod
    def plain_english_summary(result: CycleResult) -> str:
        lines = [
            "ODA_TRABOT CYCLE SUMMARY",
            "",
            f"Snapshots checked: {result.snapshots_seen}",
            f"Raw signals found: {len(result.raw_signals)}",
            f"Trades planned: {len(result.planned_trades)}",
            "",
            "Planned trades:",
        ]
        if result.planned_trades:
            for plan in result.planned_trades:
                lines.append(
                    f"- {plan.pair} {plan.direction} using {plan.workflow} "
                    f"with {plan.units:,} units "
                    f"(confidence {plan.confidence:.2f}, votes {plan.votes})"
                )
        else:
            lines.append("- none")

        if result.skipped_reasons:
            lines.extend(["", "Skipped ideas:"])
            for key, reason in result.skipped_reasons.items():
                lines.append(f"- {key}: {reason}")

        return "\n".join(lines)
