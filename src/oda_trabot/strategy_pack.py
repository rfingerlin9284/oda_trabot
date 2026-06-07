from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import FeatureSnapshot


DEFAULT_STRATEGY_PACK_NAME = "legacy_phase1"
STRATEGY_PACK_ENV = "ODA_TRABOT_STRATEGY_PACK"


@dataclass(frozen=True)
class CheckRule:
    label: str
    field: str
    operator: str
    value: float | str | bool

    def passes(self, snapshot: FeatureSnapshot) -> bool:
        actual = _snapshot_value(snapshot, self.field)
        return _compare(actual, self.operator, self.value)


@dataclass(frozen=True)
class ConfidenceTerm:
    weight: float
    field: str | None = None
    operator: str | None = None
    value: float | str | bool | None = None
    constant: float | None = None

    def score(self, snapshot: FeatureSnapshot) -> float:
        if self.constant is not None:
            return _clamp(float(self.constant))
        if self.field is None:
            raise ValueError("confidence term needs either field or constant")
        actual = _snapshot_value(snapshot, self.field)
        if self.operator is not None:
            return 1.0 if _compare(actual, self.operator, self.value) else 0.0
        return _clamp(float(actual))


@dataclass(frozen=True)
class WorkflowStrategy:
    workflow: str
    min_votes: int
    min_confidence: float
    checks: tuple[CheckRule, ...]
    confidence_terms: tuple[ConfidenceTerm, ...]

    def evaluate(self, snapshot: FeatureSnapshot) -> "StrategyEvaluation | None":
        passed = tuple(check for check in self.checks if check.passes(snapshot))
        votes = len(passed)
        confidence = self.confidence(snapshot)
        if votes < self.min_votes:
            return None
        if confidence < self.min_confidence:
            return None
        return StrategyEvaluation(
            workflow=self.workflow,
            votes=votes,
            confidence=round(confidence, 4),
            rationale=tuple(check.label for check in passed),
        )

    def confidence(self, snapshot: FeatureSnapshot) -> float:
        return sum(term.weight * term.score(snapshot) for term in self.confidence_terms)


@dataclass(frozen=True)
class StrategyEvaluation:
    workflow: str
    votes: int
    confidence: float
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class ExitProfileSpec:
    profile_name: str
    stop_pips: float
    target_pips: float
    green_lock_pips: float
    green_lock_min_profit_pips: float


@dataclass(frozen=True)
class SizingTier:
    units_multiplier: float
    min_confidence: float = 0.0
    min_votes: int = 0

    def matches(self, confidence: float, votes: int) -> bool:
        return confidence >= self.min_confidence and votes >= self.min_votes


@dataclass(frozen=True)
class StrategyPack:
    pack_id: str
    label: str
    workflows: dict[str, WorkflowStrategy]
    workflow_priority: dict[str, float]
    exit_profiles: dict[str, ExitProfileSpec]
    workflow_exit_profiles: dict[str, str]
    position_sizing: tuple[SizingTier, ...]
    metadata: dict[str, Any]
    source_path: Path | None = None

    def evaluate(self, workflow: str, snapshot: FeatureSnapshot) -> StrategyEvaluation | None:
        strategy = self.workflows.get(workflow)
        if strategy is None:
            return None
        return strategy.evaluate(snapshot)

    def priority_for(self, workflow: str) -> float:
        return float(self.workflow_priority.get(workflow, 0.0))

    def units_multiplier_for(self, confidence: float, votes: int) -> float:
        for tier in self.position_sizing:
            if tier.matches(confidence, votes):
                return tier.units_multiplier
        return 1.0

    def exit_profile_for_workflow(self, workflow: str) -> ExitProfileSpec:
        profile_name = self.workflow_exit_profiles.get(workflow)
        if profile_name is None:
            profile_name = self.workflow_exit_profiles.get("*", "default")
        return self.exit_profile_named(profile_name)

    def exit_profile_named(self, profile_name: str) -> ExitProfileSpec:
        profile = self.exit_profiles.get(profile_name)
        if profile is not None:
            return profile
        return self.exit_profiles["default"]


def load_strategy_pack(path_or_name: str | Path | None = None) -> StrategyPack:
    path = resolve_strategy_pack_path(path_or_name)
    payload = json.loads(path.read_text())
    pack = StrategyPack(
        pack_id=str(payload["pack_id"]),
        label=str(payload.get("label", payload["pack_id"])),
        workflows=_load_workflows(payload.get("workflows", {})),
        workflow_priority={str(k): float(v) for k, v in payload.get("workflow_priority", {}).items()},
        exit_profiles=_load_exit_profiles(payload.get("exit_profiles", {})),
        workflow_exit_profiles={str(k): str(v) for k, v in payload.get("workflow_exit_profiles", {}).items()},
        position_sizing=_load_position_sizing(payload.get("position_sizing", ())),
        metadata=dict(payload.get("metadata", {})),
        source_path=path,
    )
    _validate_strategy_pack(pack)
    return pack


def resolve_strategy_pack_path(path_or_name: str | Path | None = None) -> Path:
    selected = path_or_name if path_or_name is not None else os.getenv(STRATEGY_PACK_ENV, DEFAULT_STRATEGY_PACK_NAME)
    if str(selected).strip() == "":
        selected = DEFAULT_STRATEGY_PACK_NAME
    candidate = Path(selected)
    if candidate.suffix == ".json" or candidate.is_absolute() or len(candidate.parts) > 1:
        return candidate.expanduser().resolve()
    return (_repo_root() / "configs" / "strategy_packs" / f"{candidate}.json").resolve()


def _load_workflows(raw_workflows: dict[str, Any]) -> dict[str, WorkflowStrategy]:
    workflows: dict[str, WorkflowStrategy] = {}
    for workflow, raw in raw_workflows.items():
        checks = tuple(
            CheckRule(
                label=str(item["label"]),
                field=str(item["field"]),
                operator=str(item["operator"]),
                value=item["value"],
            )
            for item in raw.get("checks", ())
        )
        terms = tuple(
            ConfidenceTerm(
                weight=float(item["weight"]),
                field=str(item["field"]) if "field" in item else None,
                operator=str(item["operator"]) if "operator" in item else None,
                value=item.get("value"),
                constant=float(item["constant"]) if "constant" in item else None,
            )
            for item in raw.get("confidence_terms", ())
        )
        workflows[str(workflow)] = WorkflowStrategy(
            workflow=str(workflow),
            min_votes=int(raw.get("min_votes", 1)),
            min_confidence=float(raw.get("min_confidence", 0.0)),
            checks=checks,
            confidence_terms=terms,
        )
    return workflows


def _load_exit_profiles(raw_profiles: dict[str, Any]) -> dict[str, ExitProfileSpec]:
    profiles: dict[str, ExitProfileSpec] = {}
    for key, raw in raw_profiles.items():
        profile_name = str(raw.get("profile_name", key))
        profiles[str(key)] = ExitProfileSpec(
            profile_name=profile_name,
            stop_pips=float(raw["stop_pips"]),
            target_pips=float(raw["target_pips"]),
            green_lock_pips=float(raw["green_lock_pips"]),
            green_lock_min_profit_pips=float(raw["green_lock_min_profit_pips"]),
        )
    return profiles


def _load_position_sizing(raw_tiers: Any) -> tuple[SizingTier, ...]:
    return tuple(
        SizingTier(
            units_multiplier=float(item["units_multiplier"]),
            min_confidence=float(item.get("min_confidence", 0.0)),
            min_votes=int(item.get("min_votes", 0)),
        )
        for item in raw_tiers
    )


def _validate_strategy_pack(pack: StrategyPack) -> None:
    if "default" not in pack.exit_profiles:
        raise ValueError(f"strategy pack {pack.pack_id} must define a default exit profile")
    if not pack.position_sizing:
        raise ValueError(f"strategy pack {pack.pack_id} must define at least one position sizing tier")


def _snapshot_value(snapshot: FeatureSnapshot, field: str) -> float | str | bool:
    if not hasattr(snapshot, field):
        raise ValueError(f"strategy pack requested unknown feature field: {field}")
    value = getattr(snapshot, field)
    if isinstance(value, (float, int, str, bool)):
        return value
    raise ValueError(f"strategy pack field {field} is not scalar")


def _compare(actual: float | str | bool, operator: str, expected: float | str | bool | None) -> bool:
    if operator == "gte":
        return float(actual) >= float(expected)
    if operator == "gt":
        return float(actual) > float(expected)
    if operator == "lte":
        return float(actual) <= float(expected)
    if operator == "lt":
        return float(actual) < float(expected)
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    raise ValueError(f"unsupported strategy pack operator: {operator}")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
