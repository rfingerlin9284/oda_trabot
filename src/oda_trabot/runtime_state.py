from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .execution import OrderPreview
from .oanda import OandaTradeSnapshot, extract_trade_ids_from_order_response
from .planning import TradePlan


DEFAULT_RUNTIME_STATE_PATH = Path(__file__).resolve().parents[2] / "state" / "runtime_state.json"


@dataclass(frozen=True)
class ManagedTradeRecord:
    trade_id: str
    pair: str
    direction: str
    units: int
    workflow: str
    confidence: float
    votes: int
    rank_score: float
    rationale: tuple[str, ...]
    profile_name: str
    entry_price: float
    stop_price: float
    target_price: float
    opened_at_et: str
    last_synced_at_et: str
    last_action: str


@dataclass(frozen=True)
class ClosedTradeRecord:
    trade_id: str
    pair: str
    direction: str
    workflow: str
    closed_at_et: str
    close_reason: str
    entry_price: float
    stop_price: float
    target_price: float


@dataclass(frozen=True)
class RuntimeState:
    active_trades: tuple[ManagedTradeRecord, ...] = ()
    closed_trades: tuple[ClosedTradeRecord, ...] = ()

    def trade_ids(self) -> tuple[str, ...]:
        return tuple(record.trade_id for record in self.active_trades)

    def find(self, trade_id: str) -> ManagedTradeRecord | None:
        for record in self.active_trades:
            if record.trade_id == trade_id:
                return record
        return None

    def upsert(self, record: ManagedTradeRecord) -> "RuntimeState":
        active = [item for item in self.active_trades if item.trade_id != record.trade_id]
        active.append(record)
        return RuntimeState(
            active_trades=tuple(sorted(active, key=lambda item: item.opened_at_et)),
            closed_trades=self.closed_trades,
        )

    def close(self, trade_id: str, closed_at_et: str, close_reason: str) -> "RuntimeState":
        record = self.find(trade_id)
        if record is None:
            return self
        active = tuple(item for item in self.active_trades if item.trade_id != trade_id)
        closed = ClosedTradeRecord(
            trade_id=record.trade_id,
            pair=record.pair,
            direction=record.direction,
            workflow=record.workflow,
            closed_at_et=closed_at_et,
            close_reason=close_reason,
            entry_price=record.entry_price,
            stop_price=record.stop_price,
            target_price=record.target_price,
        )
        return RuntimeState(active_trades=active, closed_trades=self.closed_trades + (closed,))


def load_runtime_state(path: str | Path = DEFAULT_RUNTIME_STATE_PATH) -> RuntimeState:
    state_path = Path(path)
    if not state_path.exists():
        return RuntimeState()
    payload = json.loads(state_path.read_text())
    return RuntimeState(
        active_trades=tuple(_record_from_dict(item) for item in payload.get("active_trades", [])),
        closed_trades=tuple(_closed_record_from_dict(item) for item in payload.get("closed_trades", [])),
    )


def save_runtime_state(state: RuntimeState, path: str | Path = DEFAULT_RUNTIME_STATE_PATH) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "active_trades": [asdict(record) for record in state.active_trades],
                "closed_trades": [asdict(record) for record in state.closed_trades],
            },
            indent=2,
        )
    )


def records_from_submission(
    plan: TradePlan,
    preview: OrderPreview,
    response: dict,
    opened_at_et: str,
) -> tuple[ManagedTradeRecord, ...]:
    trade_ids = extract_trade_ids_from_order_response(response)
    return tuple(
        ManagedTradeRecord(
            trade_id=trade_id,
            pair=preview.pair,
            direction=preview.direction,
            units=preview.units,
            workflow=plan.workflow,
            confidence=plan.confidence,
            votes=plan.votes,
            rank_score=plan.rank_score,
            rationale=plan.rationale,
            profile_name=preview.exit_plan.profile_name,
            entry_price=preview.entry_price,
            stop_price=preview.stop_price,
            target_price=preview.target_price,
            opened_at_et=opened_at_et,
            last_synced_at_et=opened_at_et,
            last_action="submitted",
        )
        for trade_id in trade_ids
    )


def adopt_broker_trade(trade: OandaTradeSnapshot, observed_at_et: str) -> ManagedTradeRecord:
    stop_price = trade.stop_price if trade.stop_price is not None else trade.entry_price
    target_price = trade.target_price if trade.target_price is not None else trade.entry_price
    return ManagedTradeRecord(
        trade_id=trade.trade_id,
        pair=trade.pair,
        direction=trade.direction,
        units=trade.units,
        workflow="broker_unknown",
        confidence=0.0,
        votes=0,
        rank_score=0.0,
        rationale=("adopted from broker state",),
        profile_name="broker_unknown",
        entry_price=trade.entry_price,
        stop_price=stop_price,
        target_price=target_price,
        opened_at_et=observed_at_et,
        last_synced_at_et=observed_at_et,
        last_action="adopted",
    )


def _record_from_dict(payload: dict) -> ManagedTradeRecord:
    return ManagedTradeRecord(
        trade_id=str(payload["trade_id"]),
        pair=str(payload["pair"]),
        direction=str(payload["direction"]),
        units=int(payload["units"]),
        workflow=str(payload["workflow"]),
        confidence=float(payload["confidence"]),
        votes=int(payload["votes"]),
        rank_score=float(payload["rank_score"]),
        rationale=tuple(payload.get("rationale", ())),
        profile_name=str(payload["profile_name"]),
        entry_price=float(payload["entry_price"]),
        stop_price=float(payload["stop_price"]),
        target_price=float(payload["target_price"]),
        opened_at_et=str(payload["opened_at_et"]),
        last_synced_at_et=str(payload.get("last_synced_at_et", payload["opened_at_et"])),
        last_action=str(payload.get("last_action", "loaded")),
    )


def _closed_record_from_dict(payload: dict) -> ClosedTradeRecord:
    return ClosedTradeRecord(
        trade_id=str(payload["trade_id"]),
        pair=str(payload["pair"]),
        direction=str(payload["direction"]),
        workflow=str(payload["workflow"]),
        closed_at_et=str(payload["closed_at_et"]),
        close_reason=str(payload["close_reason"]),
        entry_price=float(payload["entry_price"]),
        stop_price=float(payload["stop_price"]),
        target_price=float(payload["target_price"]),
    )
