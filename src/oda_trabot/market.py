from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import FeatureSnapshot
from .oanda import OandaPriceSnapshot


@dataclass(frozen=True)
class MidCandle:
    time: datetime
    open: float
    high: float
    low: float
    close: float


def parse_oanda_mid_candles(raw_candles: tuple[dict, ...]) -> tuple[MidCandle, ...]:
    candles: list[MidCandle] = []
    for item in raw_candles:
        if not item.get("complete", False):
            continue
        mid = item.get("mid")
        if not isinstance(mid, dict):
            continue
        candles.append(
            MidCandle(
                time=datetime.fromisoformat(str(item["time"]).replace("Z", "+00:00")),
                open=float(mid["o"]),
                high=float(mid["h"]),
                low=float(mid["l"]),
                close=float(mid["c"]),
            )
        )
    return tuple(candles)


def build_feature_snapshot_from_candles(
    pair: str,
    price: OandaPriceSnapshot,
    candles: tuple[MidCandle, ...],
) -> FeatureSnapshot | None:
    if len(candles) < 16:
        return None

    closes = [c.close for c in candles]
    last = closes[-1]
    first = closes[-12]
    micro_first = closes[-4]
    recent_high = max(c.high for c in candles[-8:])
    recent_low = min(c.low for c in candles[-8:])
    avg_close = sum(closes[-8:]) / 8.0
    avg_range = sum(c.high - c.low for c in candles[-8:]) / 8.0
    latest_range = candles[-1].high - candles[-1].low
    pip = _pip_size(pair)

    bullish = last >= avg_close
    direction = "BUY" if bullish else "SELL"

    trend_move = _signed_distance(last, first, bullish)
    momentum_move = _signed_distance(last, micro_first, bullish)
    breakout_move = _breakout_score(last, recent_high, recent_low, bullish)
    retest_score = _retest_score(last, avg_close, bullish)
    scalp_score = _clamp(latest_range / max(avg_range, 1e-9))
    volatility_score = _clamp(avg_range / pip / 12.0)
    turbo = _turboscribe_features(candles, bullish, pip, trend_move, momentum_move, breakout_move, retest_score)

    return FeatureSnapshot(
        pair=pair,
        direction=direction,
        observed_at=candles[-1].time,
        spread_pips=price.spread_pips,
        trend_score=trend_move,
        momentum_score=momentum_move,
        retest_score=retest_score,
        breakout_score=breakout_move,
        scalp_score=scalp_score,
        volatility_score=volatility_score,
        broker_tradable=True,
        top_down_bias_score=turbo["top_down_bias_score"],
        entry_timeframe_alignment_score=turbo["entry_timeframe_alignment_score"],
        ema_9_distance=turbo["ema_9_distance"],
        ema_9_reclaim_score=turbo["ema_9_reclaim_score"],
        first_touch_quality=turbo["first_touch_quality"],
        late_touch_penalty=turbo["late_touch_penalty"],
        range_width_score=turbo["range_width_score"],
        support_rejection_score=turbo["support_rejection_score"],
        resistance_rejection_score=turbo["resistance_rejection_score"],
        chop_penalty=turbo["chop_penalty"],
        break_followthrough_score=turbo["break_followthrough_score"],
        failed_break_risk=turbo["failed_break_risk"],
        post_break_acceptance_score=turbo["post_break_acceptance_score"],
        level_touch_count=turbo["level_touch_count"],
        two_r_available=turbo["two_r_available"],
    )


def _turboscribe_features(
    candles: tuple[MidCandle, ...],
    bullish: bool,
    pip: float,
    trend_score: float,
    momentum_score: float,
    breakout_score: float,
    retest_score: float,
) -> dict[str, float]:
    closes = [c.close for c in candles]
    last = candles[-1]
    previous = candles[-2]
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, min(21, len(closes)))
    ema_slow = _ema(closes, min(50, len(closes)))
    prev_ema9 = _ema(closes[:-1], 9)

    ema_stack_score = _ema_stack_score(closes[-1], ema9, ema21, ema_slow, bullish)
    ema_slope_score = _directional_pip_score(ema9 - prev_ema9, bullish, pip, target_pips=3.0)
    top_down_bias_score = _clamp((0.50 * ema_stack_score) + (0.30 * trend_score) + (0.20 * ema_slope_score))
    entry_timeframe_alignment_score = _clamp((0.40 * top_down_bias_score) + (0.30 * momentum_score) + (0.30 * retest_score))

    ema_distance_pips = abs(closes[-1] - ema9) / pip
    ema_near_score = 1.0 - min(ema_distance_pips / 8.0, 1.0)
    correct_side = closes[-1] >= ema9 if bullish else closes[-1] <= ema9
    previous_wrong_or_near = previous.close <= prev_ema9 or abs(previous.close - prev_ema9) / pip <= 5.0
    if not bullish:
        previous_wrong_or_near = previous.close >= prev_ema9 or abs(previous.close - prev_ema9) / pip <= 5.0
    reclaim_bonus = 1.0 if correct_side and previous_wrong_or_near else 0.0
    ema_9_reclaim_score = _clamp((0.55 * ema_near_score) + (0.45 * reclaim_bonus))

    touch_count = _ema_touch_count(candles[-10:], ema9, pip)
    late_touch_penalty = _clamp(max(touch_count - 1.0, 0.0) / 4.0)
    first_touch_quality = _clamp((0.60 * ema_stack_score) + (0.40 * (1.0 - late_touch_penalty)))

    recent = candles[-16:] if len(candles) >= 16 else candles
    prior = candles[-9:-1] if len(candles) >= 9 else candles[:-1]
    recent_high = max(c.high for c in recent)
    recent_low = min(c.low for c in recent)
    prior_high = max(c.high for c in prior)
    prior_low = min(c.low for c in prior)
    avg_range = sum(c.high - c.low for c in recent) / max(len(recent), 1)
    range_width_pips = (recent_high - recent_low) / pip
    avg_range_pips = avg_range / pip
    range_width_score = _clamp(range_width_pips / max(avg_range_pips * 6.0, 1.0))

    support_rejection_score, resistance_rejection_score = _rejection_scores(last, recent_high, recent_low, pip)
    chop_penalty = _chop_penalty(recent, trend_score, range_width_score)
    break_followthrough_score = _break_followthrough_score(last, prior_high, prior_low, avg_range, bullish)
    failed_break_risk = _failed_break_risk(last, prior_high, prior_low, avg_range, bullish)
    post_break_acceptance_score = _clamp((0.65 * break_followthrough_score) + (0.35 * breakout_score) - (0.35 * failed_break_risk))
    level_touch_count = float(_level_touch_count(recent, recent_high, recent_low, pip))
    two_r_available = _clamp((avg_range_pips * 2.0) / 20.0)

    return {
        "top_down_bias_score": top_down_bias_score,
        "entry_timeframe_alignment_score": entry_timeframe_alignment_score,
        "ema_9_distance": round(ema_distance_pips, 4),
        "ema_9_reclaim_score": ema_9_reclaim_score,
        "first_touch_quality": first_touch_quality,
        "late_touch_penalty": late_touch_penalty,
        "range_width_score": range_width_score,
        "support_rejection_score": support_rejection_score,
        "resistance_rejection_score": resistance_rejection_score,
        "chop_penalty": chop_penalty,
        "break_followthrough_score": break_followthrough_score,
        "failed_break_risk": failed_break_risk,
        "post_break_acceptance_score": post_break_acceptance_score,
        "level_touch_count": level_touch_count,
        "two_r_available": two_r_available,
    }


def _signed_distance(current: float, past: float, bullish: bool) -> float:
    if past == 0:
        return 0.0
    raw = (current - past) / abs(past)
    directional = raw if bullish else -raw
    return _clamp(directional * 180.0)


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    period = max(1, min(period, len(values)))
    alpha = 2.0 / (period + 1.0)
    ema = values[0]
    for value in values[1:]:
        ema = (value * alpha) + (ema * (1.0 - alpha))
    return ema


def _ema_stack_score(last: float, ema9: float, ema21: float, ema_slow: float, bullish: bool) -> float:
    if bullish:
        checks = (last >= ema9, ema9 >= ema21, ema21 >= ema_slow)
    else:
        checks = (last <= ema9, ema9 <= ema21, ema21 <= ema_slow)
    return sum(1 for passed in checks if passed) / len(checks)


def _directional_pip_score(move: float, bullish: bool, pip: float, target_pips: float) -> float:
    directional = move if bullish else -move
    return _clamp((directional / pip) / target_pips)


def _ema_touch_count(candles: tuple[MidCandle, ...], ema_value: float, pip: float) -> float:
    touches = 0
    tolerance = 5.0 * pip
    for candle in candles:
        if candle.low - tolerance <= ema_value <= candle.high + tolerance:
            touches += 1
    return float(touches)


def _rejection_scores(candle: MidCandle, recent_high: float, recent_low: float, pip: float) -> tuple[float, float]:
    candle_range = max(candle.high - candle.low, 1e-9)
    lower_wick = max(min(candle.open, candle.close) - candle.low, 0.0) / candle_range
    upper_wick = max(candle.high - max(candle.open, candle.close), 0.0) / candle_range
    close_position = (candle.close - candle.low) / candle_range
    near_support = 1.0 - min(abs(candle.low - recent_low) / (8.0 * pip), 1.0)
    near_resistance = 1.0 - min(abs(candle.high - recent_high) / (8.0 * pip), 1.0)
    support = _clamp((0.45 * lower_wick) + (0.35 * close_position) + (0.20 * near_support))
    resistance = _clamp((0.45 * upper_wick) + (0.35 * (1.0 - close_position)) + (0.20 * near_resistance))
    return support, resistance


def _chop_penalty(candles: tuple[MidCandle, ...], trend_score: float, range_width_score: float) -> float:
    if len(candles) < 4:
        return 0.0
    moves = [candles[idx].close - candles[idx - 1].close for idx in range(1, len(candles))]
    non_zero_moves = [move for move in moves if abs(move) > 1e-12]
    if len(non_zero_moves) < 2:
        flip_ratio = 0.0
    else:
        flips = sum(
            1
            for idx in range(1, len(non_zero_moves))
            if (non_zero_moves[idx] > 0) != (non_zero_moves[idx - 1] > 0)
        )
        flip_ratio = flips / (len(non_zero_moves) - 1)
    return _clamp((0.45 * (1.0 - trend_score)) + (0.35 * flip_ratio) + (0.20 * (1.0 - range_width_score)))


def _break_followthrough_score(
    candle: MidCandle,
    prior_high: float,
    prior_low: float,
    avg_range: float,
    bullish: bool,
) -> float:
    body = abs(candle.close - candle.open)
    body_score = _clamp(body / max(avg_range, 1e-9))
    if bullish:
        extension = candle.close - prior_high
    else:
        extension = prior_low - candle.close
    extension_score = _clamp(extension / max(avg_range, 1e-9))
    return _clamp((0.65 * extension_score) + (0.35 * body_score))


def _failed_break_risk(
    candle: MidCandle,
    prior_high: float,
    prior_low: float,
    avg_range: float,
    bullish: bool,
) -> float:
    candle_range = max(candle.high - candle.low, 1e-9)
    body_score = _clamp(abs(candle.close - candle.open) / max(avg_range, 1e-9))
    if bullish:
        broke = candle.high > prior_high
        closed_back_inside = candle.close <= prior_high
        wick_rejection = max(candle.high - max(candle.open, candle.close), 0.0) / candle_range
    else:
        broke = candle.low < prior_low
        closed_back_inside = candle.close >= prior_low
        wick_rejection = max(min(candle.open, candle.close) - candle.low, 0.0) / candle_range
    if not broke:
        return 0.0
    return _clamp((0.55 if closed_back_inside else 0.0) + (0.30 * wick_rejection) + (0.15 * (1.0 - body_score)))


def _level_touch_count(candles: tuple[MidCandle, ...], recent_high: float, recent_low: float, pip: float) -> int:
    tolerance = 4.0 * pip
    return sum(
        1
        for candle in candles
        if abs(candle.high - recent_high) <= tolerance or abs(candle.low - recent_low) <= tolerance
    )


def _breakout_score(current: float, recent_high: float, recent_low: float, bullish: bool) -> float:
    if bullish:
        distance = (current - recent_low) / max(recent_high - recent_low, 1e-9)
    else:
        distance = (recent_high - current) / max(recent_high - recent_low, 1e-9)
    return _clamp(distance)


def _retest_score(current: float, avg_close: float, bullish: bool) -> float:
    if avg_close == 0:
        return 0.0
    distance = abs(current - avg_close) / abs(avg_close)
    score = 1.0 - min(distance * 150.0, 1.0)
    return _clamp(score)


def _pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 0.0001


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
