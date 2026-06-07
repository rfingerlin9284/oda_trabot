from __future__ import annotations

from dataclasses import dataclass

from .contract import TradingContract


@dataclass(frozen=True)
class OpenPosition:
    pair: str
    direction: str
    units: int
    workflow: str


@dataclass(frozen=True)
class PortfolioState:
    open_positions: tuple[OpenPosition, ...] = ()

    @property
    def open_pairs(self) -> tuple[str, ...]:
        return tuple(position.pair for position in self.open_positions)

    def open_slots(self, contract: TradingContract) -> int:
        return max(0, contract.max_positions - len(self.open_positions))

    def has_pair(self, pair: str) -> bool:
        return pair in self.open_pairs
