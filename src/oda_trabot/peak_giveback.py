from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from .router import to_eastern


DEFAULT_PEAK_GIVEBACK_STATE_PATH = Path(__file__).resolve().parents[2] / "state" / "peak_giveback_state.json"


@dataclass(frozen=True)
class PeakGivebackPolicy:
    arm_gain_usd: float = 350.0
    giveback_from_peak_usd: float = 175.0
    session_roll_hour_et: int = 17


@dataclass(frozen=True)
class PeakGivebackState:
    session_key: str
    baseline_nav: float
    peak_nav: float
    armed: bool


@dataclass(frozen=True)
class PeakGivebackDecision:
    state: PeakGivebackState
    action: str
    reason: str
    session_gain_usd: float
    giveback_from_peak_usd: float

    @property
    def should_flatten(self) -> bool:
        return self.action == "flatten"


def evaluate_peak_giveback(
    state: PeakGivebackState | None,
    *,
    nav: float,
    observed_at: datetime,
    policy: PeakGivebackPolicy | None = None,
) -> PeakGivebackDecision:
    active_policy = policy or PeakGivebackPolicy()
    session_key = session_key_for(observed_at, active_policy)
    if state is None or state.session_key != session_key:
        next_state = PeakGivebackState(
            session_key=session_key,
            baseline_nav=nav,
            peak_nav=nav,
            armed=False,
        )
        return PeakGivebackDecision(
            state=next_state,
            action="reset",
            reason="new session baseline established",
            session_gain_usd=0.0,
            giveback_from_peak_usd=0.0,
        )

    peak_nav = max(state.peak_nav, nav)
    session_gain = peak_nav - state.baseline_nav
    giveback = peak_nav - nav
    armed = state.armed or session_gain >= active_policy.arm_gain_usd
    next_state = PeakGivebackState(
        session_key=session_key,
        baseline_nav=state.baseline_nav,
        peak_nav=peak_nav,
        armed=armed,
    )

    if armed and giveback >= active_policy.giveback_from_peak_usd:
        return PeakGivebackDecision(
            state=next_state,
            action="flatten",
            reason=(
                "peak giveback overlay tripped: "
                f"armed after +${active_policy.arm_gain_usd:.2f}, "
                f"gave back ${giveback:.2f} from peak"
            ),
            session_gain_usd=round(session_gain, 2),
            giveback_from_peak_usd=round(giveback, 2),
        )
    if armed and not state.armed:
        return PeakGivebackDecision(
            state=next_state,
            action="arm",
            reason="peak giveback overlay armed",
            session_gain_usd=round(session_gain, 2),
            giveback_from_peak_usd=round(giveback, 2),
        )
    return PeakGivebackDecision(
        state=next_state,
        action="track",
        reason="peak giveback overlay tracking",
        session_gain_usd=round(session_gain, 2),
        giveback_from_peak_usd=round(giveback, 2),
    )


def session_key_for(moment: datetime, policy: PeakGivebackPolicy | None = None) -> str:
    active_policy = policy or PeakGivebackPolicy()
    current = to_eastern(moment)
    roll = time(active_policy.session_roll_hour_et, 0)
    session_date = current.date()
    if current.time() >= roll:
        session_date += timedelta(days=1)
    return session_date.isoformat()


def load_peak_giveback_state(
    path: str | Path = DEFAULT_PEAK_GIVEBACK_STATE_PATH,
) -> PeakGivebackState | None:
    state_path = Path(path)
    if not state_path.exists():
        return None
    payload = json.loads(state_path.read_text())
    return PeakGivebackState(
        session_key=str(payload["session_key"]),
        baseline_nav=float(payload["baseline_nav"]),
        peak_nav=float(payload["peak_nav"]),
        armed=bool(payload["armed"]),
    )


def save_peak_giveback_state(
    state: PeakGivebackState,
    path: str | Path = DEFAULT_PEAK_GIVEBACK_STATE_PATH,
) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(asdict(state), indent=2))
