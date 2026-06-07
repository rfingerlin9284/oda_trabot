from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeatureSnapshot:
    pair: str
    direction: str
    observed_at: datetime
    spread_pips: float
    trend_score: float
    momentum_score: float
    retest_score: float
    breakout_score: float
    scalp_score: float
    volatility_score: float
    broker_tradable: bool = True
    top_down_bias_score: float = 0.0
    entry_timeframe_alignment_score: float = 0.0
    ema_9_distance: float = 0.0
    ema_9_reclaim_score: float = 0.0
    first_touch_quality: float = 0.0
    late_touch_penalty: float = 0.0
    range_width_score: float = 0.0
    support_rejection_score: float = 0.0
    resistance_rejection_score: float = 0.0
    chop_penalty: float = 0.0
    break_followthrough_score: float = 0.0
    failed_break_risk: float = 0.0
    post_break_acceptance_score: float = 0.0
    level_touch_count: float = 0.0
    two_r_available: float = 0.0

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "FeatureSnapshot":
        trend_score = float(raw["trend_score"])
        momentum_score = float(raw["momentum_score"])
        retest_score = float(raw["retest_score"])
        breakout_score = float(raw["breakout_score"])
        scalp_score = float(raw["scalp_score"])
        volatility_score = float(raw["volatility_score"])
        return cls(
            pair=str(raw["pair"]),
            direction=str(raw["direction"]),
            observed_at=datetime.fromisoformat(str(raw["observed_at"])),
            spread_pips=float(raw["spread_pips"]),
            trend_score=trend_score,
            momentum_score=momentum_score,
            retest_score=retest_score,
            breakout_score=breakout_score,
            scalp_score=scalp_score,
            volatility_score=volatility_score,
            broker_tradable=bool(raw.get("broker_tradable", True)),
            top_down_bias_score=float(raw.get("top_down_bias_score", trend_score)),
            entry_timeframe_alignment_score=float(raw.get("entry_timeframe_alignment_score", trend_score)),
            ema_9_distance=float(raw.get("ema_9_distance", 0.0)),
            ema_9_reclaim_score=float(raw.get("ema_9_reclaim_score", retest_score)),
            first_touch_quality=float(raw.get("first_touch_quality", retest_score)),
            late_touch_penalty=float(raw.get("late_touch_penalty", 0.0)),
            range_width_score=float(raw.get("range_width_score", volatility_score)),
            support_rejection_score=float(raw.get("support_rejection_score", retest_score)),
            resistance_rejection_score=float(raw.get("resistance_rejection_score", retest_score)),
            chop_penalty=float(raw.get("chop_penalty", max(0.0, 1.0 - trend_score))),
            break_followthrough_score=float(raw.get("break_followthrough_score", breakout_score)),
            failed_break_risk=float(raw.get("failed_break_risk", 0.0)),
            post_break_acceptance_score=float(raw.get("post_break_acceptance_score", breakout_score)),
            level_touch_count=float(raw.get("level_touch_count", 0.0)),
            two_r_available=float(raw.get("two_r_available", volatility_score)),
        )
