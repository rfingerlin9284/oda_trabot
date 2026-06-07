from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SessionName(StrEnum):
    LONDON = "london"
    OVERLAP = "overlap"
    NEW_YORK = "new_york"
    TOKYO = "tokyo"
    OFF_SESSION = "off_session"


@dataclass(frozen=True)
class SessionContract:
    name: SessionName
    enabled: bool
    workflows: tuple[str, ...]


@dataclass(frozen=True)
class TradingContract:
    name: str
    practice_only: bool
    trading_pairs: tuple[str, ...]
    session_start_hour_et: int
    session_end_hour_et: int
    min_votes: int
    min_signal_confidence: float
    base_units: int
    max_positions: int
    max_new_trades_per_cycle: int
    require_oco: bool
    sessions: tuple[SessionContract, ...]

    def session(self, name: SessionName) -> SessionContract:
        for session in self.sessions:
            if session.name == name:
                return session
        raise KeyError(f"Unknown session: {name}")


PHASE1_CONTRACT = TradingContract(
    name="oda_trabot_phase1_april14_core",
    practice_only=True,
    trading_pairs=(
        "EUR_USD",
        "GBP_USD",
        "USD_JPY",
        "USD_CHF",
        "AUD_USD",
        "USD_CAD",
        "NZD_USD",
    ),
    session_start_hour_et=3,
    session_end_hour_et=17,
    min_votes=3,
    min_signal_confidence=0.80,
    base_units=50_000,
    max_positions=4,
    max_new_trades_per_cycle=2,
    require_oco=True,
    sessions=(
        SessionContract(
            name=SessionName.LONDON,
            enabled=True,
            workflows=("momentum", "continuation", "second_chance", "fashionably_late", "scalp"),
        ),
        SessionContract(
            name=SessionName.OVERLAP,
            enabled=True,
            workflows=("momentum", "continuation", "second_chance", "fashionably_late", "scalp"),
        ),
        SessionContract(
            name=SessionName.NEW_YORK,
            enabled=True,
            workflows=("continuation", "second_chance", "scalp"),
        ),
        SessionContract(
            name=SessionName.TOKYO,
            enabled=False,
            workflows=(),
        ),
        SessionContract(
            name=SessionName.OFF_SESSION,
            enabled=False,
            workflows=(),
        ),
    ),
)
