from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .contract import SessionContract, SessionName, TradingContract

EASTERN_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class RoutingDecision:
    current_time_et: datetime
    detected_session: SessionName
    trading_window_open: bool
    session_enabled: bool
    active_workflows: tuple[str, ...]
    allowed_pairs: tuple[str, ...]

    @property
    def can_trade(self) -> bool:
        return self.trading_window_open and self.session_enabled


def to_eastern(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=EASTERN_TZ)
    return moment.astimezone(EASTERN_TZ)


def _in_window(current: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def detect_session(moment: datetime) -> SessionName:
    current = to_eastern(moment).time()
    if _in_window(current, time(8, 0), time(12, 0)):
        return SessionName.OVERLAP
    if _in_window(current, time(3, 0), time(12, 0)):
        return SessionName.LONDON
    if _in_window(current, time(12, 0), time(17, 0)):
        return SessionName.NEW_YORK
    if _in_window(current, time(19, 0), time(3, 0)):
        return SessionName.TOKYO
    return SessionName.OFF_SESSION


def trading_window_open(contract: TradingContract, moment: datetime) -> bool:
    current = to_eastern(moment).time()
    return _in_window(
        current,
        time(contract.session_start_hour_et, 0),
        time(contract.session_end_hour_et, 0),
    )


class SessionRouter:
    def __init__(self, contract: TradingContract) -> None:
        self._contract = contract

    def route(self, moment: datetime) -> RoutingDecision:
        current_time_et = to_eastern(moment)
        session_name = detect_session(current_time_et)
        session = self._contract.session(session_name)
        window_open = trading_window_open(self._contract, current_time_et)
        return RoutingDecision(
            current_time_et=current_time_et,
            detected_session=session_name,
            trading_window_open=window_open,
            session_enabled=session.enabled,
            active_workflows=session.workflows if window_open and session.enabled else (),
            allowed_pairs=self._allowed_pairs(session_name, window_open and session.enabled),
        )

    def is_pair_allowed(self, pair: str, moment: datetime) -> bool:
        decision = self.route(moment)
        return decision.can_trade and pair in decision.allowed_pairs

    def _allowed_pairs(
        self,
        session_name: SessionName,
        can_trade: bool,
    ) -> tuple[str, ...]:
        if not can_trade:
            return ()

        if session_name in {
            SessionName.LONDON,
            SessionName.OVERLAP,
            SessionName.NEW_YORK,
        }:
            return self._contract.trading_pairs

        return ()

    def session_contract(self, name: SessionName) -> SessionContract:
        return self._contract.session(name)
