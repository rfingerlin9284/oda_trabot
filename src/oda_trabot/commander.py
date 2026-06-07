from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum

from .contract import SessionName, TradingContract
from .models import FeatureSnapshot
from .oanda import OandaAccountSnapshot, OandaPriceSnapshot
from .planning import TradePlan
from .router import SessionRouter, to_eastern
from .strategy_pack import StrategyPack, load_strategy_pack


class TradeMode(StrEnum):
    A_GRADE = "A-grade momentum continuation"
    B_GRADE = "B-grade TurboScribe filtered trend"
    C_GRADE = "C-grade controlled scalp"
    NO_TRADE = "NO_TRADE"


class CommanderAction(StrEnum):
    APPROVE = "APPROVE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class CommanderPolicy:
    market_open_sunday_hour_et: int = 17
    market_close_friday_hour_et: int = 17
    core_edge_start_et: int = 3
    core_edge_end_et: int = 9
    max_average_spread_pips: float = 5.0
    max_trade_spread_pips: float = 2.2
    max_scalp_spread_pips: float = 1.8
    min_a_grade_confidence: float = 0.80
    min_a_grade_votes: int = 3
    min_b_grade_confidence: float = 0.66
    min_b_grade_votes: int = 3
    min_c_grade_confidence: float = 0.68
    min_c_grade_votes: int = 2
    min_scalp_two_r_available: float = 0.60
    max_unrealized_loss_usd: float | None = None
    verified_momentum_pairs: tuple[str, ...] = (
        "USD_CHF",
        "GBP_USD",
        "NZD_USD",
        "EUR_USD",
        "USD_CAD",
        "AUD_USD",
        "USD_JPY",
    )
    verified_post9_continuation_pairs: tuple[str, ...] = (
        "AUD_USD",
        "EUR_USD",
        "NZD_USD",
        "USD_CAD",
        "USD_CHF",
    )


@dataclass(frozen=True)
class CommanderDecision:
    action: CommanderAction
    mode: TradeMode
    pair: str
    direction: str
    workflow: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CommanderCycleDecision:
    market_open: bool
    bad_spread_regime: bool
    status: TradeMode
    reasons: tuple[str, ...]
    plan_decisions: tuple[CommanderDecision, ...]
    approved_plans: tuple[TradePlan, ...]

    @property
    def blocked_plans(self) -> tuple[CommanderDecision, ...]:
        return tuple(
            decision
            for decision in self.plan_decisions
            if decision.action == CommanderAction.BLOCK
        )


class AutonomyCommander:
    def __init__(
        self,
        contract: TradingContract,
        *,
        strategy_pack: StrategyPack | None = None,
        policy: CommanderPolicy | None = None,
    ) -> None:
        self._contract = contract
        self._router = SessionRouter(contract)
        self._strategy_pack = strategy_pack or load_strategy_pack()
        self._policy = policy or CommanderPolicy()

    def evaluate(
        self,
        *,
        planned_trades: tuple[TradePlan, ...],
        snapshots: tuple[FeatureSnapshot, ...],
        prices: tuple[OandaPriceSnapshot, ...],
        observed_at: datetime,
        account: OandaAccountSnapshot | None = None,
    ) -> CommanderCycleDecision:
        observed_at_et = to_eastern(observed_at)
        market_open = self.market_is_open(observed_at_et)
        bad_spread_regime = self._bad_spread_regime(prices)
        cycle_reasons = self._cycle_reasons(market_open, bad_spread_regime, account)

        snapshot_map = {snapshot.pair: snapshot for snapshot in snapshots}
        price_map = {price.pair: price for price in prices}
        plan_decisions: list[CommanderDecision] = []
        approved_plans: list[TradePlan] = []

        for plan in planned_trades:
            decision = self._evaluate_plan(
                plan=plan,
                snapshot=snapshot_map.get(plan.pair),
                price=price_map.get(plan.pair),
                observed_at=observed_at_et,
                cycle_reasons=cycle_reasons,
            )
            plan_decisions.append(decision)
            if decision.action == CommanderAction.APPROVE:
                approved_plans.append(plan)

        if approved_plans:
            status = self._strongest_mode(tuple(plan_decisions))
            reasons = ("approved verified edge plan",)
        elif planned_trades:
            status = TradeMode.NO_TRADE
            reasons = ("planned trades existed, but commander blocked them",)
        else:
            status = TradeMode.NO_TRADE
            reasons = cycle_reasons or ("no verified setup planned this cycle",)

        return CommanderCycleDecision(
            market_open=market_open,
            bad_spread_regime=bad_spread_regime,
            status=status,
            reasons=reasons,
            plan_decisions=tuple(plan_decisions),
            approved_plans=tuple(approved_plans),
        )

    def market_is_open(self, moment: datetime) -> bool:
        current = to_eastern(moment)
        weekday = current.weekday()
        current_time = current.time()
        if weekday == 5:
            return False
        if weekday == 6:
            return current_time >= time(self._policy.market_open_sunday_hour_et, 0)
        if weekday == 4:
            return current_time < time(self._policy.market_close_friday_hour_et, 0)
        return True

    def _cycle_reasons(
        self,
        market_open: bool,
        bad_spread_regime: bool,
        account: OandaAccountSnapshot | None,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if not market_open:
            reasons.append("forex market is closed")
        if bad_spread_regime:
            reasons.append("average spread regime is too wide")
        if (
            account is not None
            and self._policy.max_unrealized_loss_usd is not None
            and account.unrealized_pl <= -abs(self._policy.max_unrealized_loss_usd)
        ):
            reasons.append("unrealized loss lock is active")
        return tuple(reasons)

    def _evaluate_plan(
        self,
        *,
        plan: TradePlan,
        snapshot: FeatureSnapshot | None,
        price: OandaPriceSnapshot | None,
        observed_at: datetime,
        cycle_reasons: tuple[str, ...],
    ) -> CommanderDecision:
        reasons = list(cycle_reasons)
        route = self._router.route(snapshot.observed_at if snapshot is not None else observed_at)

        if snapshot is None:
            reasons.append("missing feature snapshot for planned trade")
        if price is None:
            reasons.append("missing live price for planned trade")
        if not route.can_trade:
            reasons.append("session is not enabled for new entries")
        if plan.pair not in route.allowed_pairs:
            reasons.append(f"pair {plan.pair} is not allowed in this session")
        if plan.workflow not in route.active_workflows:
            reasons.append(f"workflow {plan.workflow} is not active in this session")
        if price is not None and price.spread_pips > self._policy.max_trade_spread_pips:
            reasons.append(
                f"spread too wide: got {price.spread_pips:.2f} pips, "
                f"max {self._policy.max_trade_spread_pips:.2f}"
            )

        mode = TradeMode.NO_TRADE
        if snapshot is not None and price is not None:
            mode, grade_reasons = self._grade_plan(plan, snapshot, price, route.detected_session)
            reasons.extend(grade_reasons)

        action = CommanderAction.APPROVE if not reasons and mode != TradeMode.NO_TRADE else CommanderAction.BLOCK
        return CommanderDecision(
            action=action,
            mode=mode,
            pair=plan.pair,
            direction=plan.direction,
            workflow=plan.workflow,
            reasons=tuple(reasons) if reasons else (f"{mode.value} criteria passed",),
        )

    def _grade_plan(
        self,
        plan: TradePlan,
        snapshot: FeatureSnapshot,
        price: OandaPriceSnapshot,
        session: SessionName,
    ) -> tuple[TradeMode, tuple[str, ...]]:
        if self._is_a_grade(plan, snapshot):
            return TradeMode.A_GRADE, ()
        if self._is_b_grade(plan, snapshot):
            return TradeMode.B_GRADE, ()
        if self._is_c_grade(plan, snapshot, price, session):
            return TradeMode.C_GRADE, ()
        return TradeMode.NO_TRADE, ("no verified A/B/C edge grade matched",)

    def _is_a_grade(self, plan: TradePlan, snapshot: FeatureSnapshot) -> bool:
        if self._strategy_pack.pack_id == "april14_momentum_3am_9am":
            return self._is_april14_momentum(plan, snapshot)
        if self._strategy_pack.pack_id == "post_9am_ema_fib_momentum_continuation":
            return self._is_post9_ema_fib_continuation(plan, snapshot)
        return self._is_legacy_a_grade(plan, snapshot)

    def _is_april14_momentum(self, plan: TradePlan, snapshot: FeatureSnapshot) -> bool:
        observed = to_eastern(snapshot.observed_at)
        return (
            time(3, 0) <= observed.time() <= time(8, 30, 59, 999999)
            and plan.pair in self._policy.verified_momentum_pairs
            and plan.workflow == "momentum"
            and plan.confidence >= self._policy.min_a_grade_confidence
            and plan.votes >= self._policy.min_a_grade_votes
            and snapshot.momentum_score >= 0.70
            and snapshot.trend_score >= 0.70
        )

    def _is_post9_ema_fib_continuation(self, plan: TradePlan, snapshot: FeatureSnapshot) -> bool:
        observed = to_eastern(snapshot.observed_at)
        return (
            time(9, 0) <= observed.time() < time(11, 30)
            and plan.pair in self._policy.verified_post9_continuation_pairs
            and plan.workflow == "continuation"
            and plan.confidence >= self._policy.min_a_grade_confidence
            and plan.votes >= 4
            and snapshot.trend_score >= 0.72
            and snapshot.momentum_score >= 0.68
            and snapshot.retest_score >= 0.55
            and snapshot.post_break_acceptance_score >= 0.62
            and snapshot.top_down_bias_score >= 0.70
            and snapshot.ema_9_reclaim_score >= 0.58
            and snapshot.failed_break_risk <= 0.35
            and snapshot.chop_penalty <= 0.45
        )

    def _is_legacy_a_grade(self, plan: TradePlan, snapshot: FeatureSnapshot) -> bool:
        observed = to_eastern(snapshot.observed_at)
        return (
            self._policy.core_edge_start_et <= observed.hour < self._policy.core_edge_end_et
            and plan.pair in self._policy.verified_momentum_pairs
            and plan.workflow in {"momentum", "continuation", "second_chance", "fashionably_late"}
            and plan.confidence >= self._policy.min_a_grade_confidence
            and plan.votes >= self._policy.min_a_grade_votes
            and snapshot.momentum_score >= 0.70
            and snapshot.trend_score >= 0.70
        )

    def _is_b_grade(self, plan: TradePlan, snapshot: FeatureSnapshot) -> bool:
        return (
            self._strategy_pack.pack_id.startswith("turboscribe")
            and plan.workflow in {"continuation", "second_chance", "fashionably_late"}
            and plan.confidence >= self._policy.min_b_grade_confidence
            and plan.votes >= self._policy.min_b_grade_votes
            and snapshot.top_down_bias_score >= 0.62
            and snapshot.ema_9_reclaim_score >= 0.55
            and snapshot.failed_break_risk <= 0.45
            and snapshot.chop_penalty <= 0.55
        )

    def _is_c_grade(
        self,
        plan: TradePlan,
        snapshot: FeatureSnapshot,
        price: OandaPriceSnapshot,
        session: SessionName,
    ) -> bool:
        return (
            plan.workflow == "scalp"
            and session in {SessionName.LONDON, SessionName.OVERLAP, SessionName.NEW_YORK}
            and plan.confidence >= self._policy.min_c_grade_confidence
            and plan.votes >= self._policy.min_c_grade_votes
            and price.spread_pips <= self._policy.max_scalp_spread_pips
            and snapshot.two_r_available >= self._policy.min_scalp_two_r_available
            and snapshot.failed_break_risk <= 0.55
        )

    def _bad_spread_regime(self, prices: tuple[OandaPriceSnapshot, ...]) -> bool:
        if not prices:
            return True
        average_spread = sum(price.spread_pips for price in prices) / len(prices)
        return average_spread > self._policy.max_average_spread_pips

    @staticmethod
    def _strongest_mode(decisions: tuple[CommanderDecision, ...]) -> TradeMode:
        approved_modes = [
            decision.mode
            for decision in decisions
            if decision.action == CommanderAction.APPROVE
        ]
        for mode in (TradeMode.A_GRADE, TradeMode.B_GRADE, TradeMode.C_GRADE):
            if mode in approved_modes:
                return mode
        return TradeMode.NO_TRADE
