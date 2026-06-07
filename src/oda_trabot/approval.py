from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .contract import SessionName, TradingContract
from .router import SessionRouter


@dataclass(frozen=True)
class SignalCandidate:
    pair: str
    direction: str
    workflow: str
    votes: int
    confidence: float
    observed_at: datetime


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    reasons: tuple[str, ...]


class CandidateApprover:
    def __init__(self, contract: TradingContract) -> None:
        self._contract = contract
        self._router = SessionRouter(contract)
        self._runtime_overrides = _load_runtime_overrides()

    def evaluate(self, candidate: SignalCandidate) -> ApprovalDecision:
        reasons: list[str] = []
        route = self._router.route(candidate.observed_at)
        min_votes = self._min_votes_for(candidate, route)
        min_confidence = self._min_confidence_for(candidate, route)

        if not route.can_trade:
            reasons.append("trading window is closed for this session")
        if candidate.pair not in route.allowed_pairs:
            reasons.append(f"pair {candidate.pair} is not allowed right now")
        if candidate.workflow not in route.active_workflows:
            reasons.append(f"workflow {candidate.workflow} is not allowed in this session")
        if candidate.votes < min_votes:
            reasons.append(
                f"votes too low: got {candidate.votes}, need {min_votes}"
            )
        if candidate.confidence < min_confidence:
            reasons.append(
                "confidence too low: "
                f"got {candidate.confidence:.2f}, need {min_confidence:.2f}"
            )

        return ApprovalDecision(approved=not reasons, reasons=tuple(reasons))

    def _min_votes_for(self, candidate: SignalCandidate, route) -> int:
        if self._is_day_session_scalp(candidate, route):
            return int(self._runtime_overrides.get("day_scalp_min_votes", self._contract.min_votes))
        if self._is_early_london_scalp(candidate, route):
            return 2
        return self._contract.min_votes

    def _min_confidence_for(self, candidate: SignalCandidate, route) -> float:
        if self._is_early_london_scalp(candidate, route):
            return float(self._runtime_overrides.get("early_london_scalp_min_confidence", 0.70))
        if self._is_day_session_scalp(candidate, route):
            return float(self._runtime_overrides.get("day_scalp_min_confidence", self._contract.min_signal_confidence))
        return self._contract.min_signal_confidence

    @staticmethod
    def _is_early_london_scalp(candidate: SignalCandidate, route) -> bool:
        return (
            route.detected_session == SessionName.LONDON
            and candidate.workflow == "scalp"
            and 3 <= route.current_time_et.hour < 5
        )

    @staticmethod
    def _is_day_session_scalp(candidate: SignalCandidate, route) -> bool:
        return (
            candidate.workflow == "scalp"
            and route.detected_session in {
                SessionName.LONDON,
                SessionName.OVERLAP,
                SessionName.NEW_YORK,
            }
        )


def _load_runtime_overrides() -> dict[str, float | int]:
    env_values = _read_runtime_env()
    data_mode = str(env_values.get("ODA_TRABOT_PAPER_DATA_MODE", "NO")).upper() == "YES"
    if not data_mode:
        return {
            "day_scalp_min_votes": 3,
            "day_scalp_min_confidence": 0.80,
            "early_london_scalp_min_confidence": 0.70,
        }
    return {
        "day_scalp_min_votes": int(env_values.get("ODA_TRABOT_DAY_SCALP_MIN_VOTES", 2)),
        "day_scalp_min_confidence": float(env_values.get("ODA_TRABOT_DAY_SCALP_MIN_CONFIDENCE", 0.68)),
        "early_london_scalp_min_confidence": float(env_values.get("ODA_TRABOT_EARLY_LONDON_SCALP_MIN_CONFIDENCE", 0.66)),
    }


def _read_runtime_env() -> dict[str, str]:
    path = Path(__file__).resolve().parents[2] / "state" / "runtime.env"
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key] = value.strip()
    for key in (
        "ODA_TRABOT_PAPER_DATA_MODE",
        "ODA_TRABOT_DAY_SCALP_MIN_VOTES",
        "ODA_TRABOT_DAY_SCALP_MIN_CONFIDENCE",
        "ODA_TRABOT_EARLY_LONDON_SCALP_MIN_CONFIDENCE",
    ):
        if os.getenv(key):
            values[key] = str(os.getenv(key))
    return values
