import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from oda_trabot import (
    PHASE1_CONTRACT,
    AutonomyCommander,
    CandidateApprover,
    CommanderAction,
    CommanderPolicy,
    ClosedTradeRecord,
    CycleEngine,
    HistoricalWindow,
    FeatureSnapshot,
    ManagedTradeRecord,
    ManagedPosition,
    MidCandle,
    OpenPosition,
    OrderPreviewBuilder,
    OandaPracticeConfig,
    OandaPriceSnapshot,
    OandaTradeSnapshot,
    PortfolioState,
    PeakGivebackPolicy,
    PeakGivebackState,
    PositionSizer,
    ReplayEngine,
    RuntimeState,
    SignalSelector,
    SessionName,
    SessionRouter,
    SignalCandidate,
    SignalPipelineShell,
    TradePlan,
    TradeMode,
    build_feature_snapshot_from_candles,
    build_exit_plan,
    evaluate_peak_giveback,
    evaluate_management_actions,
    extract_trade_ids_from_order_response,
    load_counterfactual_windows,
    load_runtime_state,
    load_strategy_pack,
    manage_position,
    parse_oanda_mid_candles,
    reconcile_state_with_broker,
    records_from_submission,
    save_runtime_state,
    select_active_cartridge,
    summarize_windows,
    detect_session,
    session_key_for,
)
from oda_trabot.oanda import _read_env_file, _spread_pips

EASTERN_TZ = ZoneInfo("America/New_York")


class Phase1ContractTests(unittest.TestCase):
    def test_uses_proven_seven_pair_universe(self) -> None:
        self.assertEqual(
            PHASE1_CONTRACT.trading_pairs,
            (
                "EUR_USD",
                "GBP_USD",
                "USD_JPY",
                "USD_CHF",
                "AUD_USD",
                "USD_CAD",
                "NZD_USD",
            ),
        )

    def test_is_practice_only(self) -> None:
        self.assertTrue(PHASE1_CONTRACT.practice_only)
        self.assertTrue(PHASE1_CONTRACT.require_oco)

    def test_keeps_london_core_workflows(self) -> None:
        london = PHASE1_CONTRACT.session(SessionName.LONDON)
        self.assertTrue(london.enabled)
        self.assertEqual(
            london.workflows,
            (
                "momentum",
                "continuation",
                "second_chance",
                "fashionably_late",
                "scalp",
            ),
        )


class SessionRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = SessionRouter(PHASE1_CONTRACT)

    def test_detects_overlap_before_other_day_sessions(self) -> None:
        moment = datetime(2026, 6, 4, 9, 30, tzinfo=EASTERN_TZ)
        self.assertEqual(detect_session(moment), SessionName.OVERLAP)

    def test_detects_london_before_overlap_window(self) -> None:
        moment = datetime(2026, 6, 4, 4, 30, tzinfo=EASTERN_TZ)
        self.assertEqual(detect_session(moment), SessionName.LONDON)

    def test_detects_new_york_after_overlap_ends(self) -> None:
        moment = datetime(2026, 6, 4, 13, 0, tzinfo=EASTERN_TZ)
        self.assertEqual(detect_session(moment), SessionName.NEW_YORK)

    def test_detects_tokyo_outside_day_gate(self) -> None:
        moment = datetime(2026, 6, 4, 20, 0, tzinfo=EASTERN_TZ)
        self.assertEqual(detect_session(moment), SessionName.TOKYO)

    def test_router_allows_all_phase1_pairs_during_london(self) -> None:
        moment = datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ)
        decision = self.router.route(moment)
        self.assertTrue(decision.can_trade)
        self.assertEqual(decision.detected_session, SessionName.LONDON)
        self.assertEqual(decision.allowed_pairs, PHASE1_CONTRACT.trading_pairs)

    def test_router_blocks_off_session_even_when_tokyo_exists(self) -> None:
        moment = datetime(2026, 6, 4, 20, 0, tzinfo=EASTERN_TZ)
        decision = self.router.route(moment)
        self.assertFalse(decision.can_trade)
        self.assertEqual(decision.detected_session, SessionName.TOKYO)
        self.assertEqual(decision.active_workflows, ())
        self.assertEqual(decision.allowed_pairs, ())

    def test_pair_gate_rejects_unknown_pair(self) -> None:
        moment = datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ)
        self.assertFalse(self.router.is_pair_allowed("XAU_USD", moment))

    def test_pair_gate_accepts_known_pair_during_day_window(self) -> None:
        moment = datetime(2026, 6, 4, 14, 0, tzinfo=EASTERN_TZ)
        self.assertTrue(self.router.is_pair_allowed("USD_CAD", moment))


class CandidateApproverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approver = CandidateApprover(PHASE1_CONTRACT)

    def test_approves_clean_london_candidate(self) -> None:
        candidate = SignalCandidate(
            pair="GBP_USD",
            direction="BUY",
            workflow="continuation",
            votes=3,
            confidence=0.88,
            observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
        )
        decision = self.approver.evaluate(candidate)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.reasons, ())

    def test_rejects_candidate_with_multiple_plain_reasons(self) -> None:
        candidate = SignalCandidate(
            pair="XAU_USD",
            direction="SELL",
            workflow="big_dog",
            votes=1,
            confidence=0.72,
            observed_at=datetime(2026, 6, 4, 20, 0, tzinfo=EASTERN_TZ),
        )
        decision = self.approver.evaluate(candidate)
        self.assertFalse(decision.approved)
        self.assertIn("trading window is closed for this session", decision.reasons)
        self.assertIn("pair XAU_USD is not allowed right now", decision.reasons)
        self.assertIn(
            "workflow big_dog is not allowed in this session",
            decision.reasons,
        )
        self.assertIn("votes too low: got 1, need 3", decision.reasons)
        self.assertIn("confidence too low: got 0.72, need 0.80", decision.reasons)

    def test_early_london_scalp_can_pass_with_two_votes(self) -> None:
        candidate = SignalCandidate(
            pair="AUD_USD",
            direction="BUY",
            workflow="scalp",
            votes=2,
            confidence=0.71,
            observed_at=datetime(2026, 6, 5, 4, 0, tzinfo=EASTERN_TZ),
        )
        decision = self.approver.evaluate(candidate)
        self.assertTrue(decision.approved)

    def test_day_session_scalp_can_pass_after_early_london_in_paper_data_mode(self) -> None:
        candidate = SignalCandidate(
            pair="AUD_USD",
            direction="BUY",
            workflow="scalp",
            votes=2,
            confidence=0.71,
            observed_at=datetime(2026, 6, 5, 5, 30, tzinfo=EASTERN_TZ),
        )
        decision = self.approver.evaluate(candidate)
        self.assertTrue(decision.approved)

    def test_day_session_scalp_still_rejects_when_confidence_stays_too_low(self) -> None:
        candidate = SignalCandidate(
            pair="AUD_USD",
            direction="BUY",
            workflow="scalp",
            votes=2,
            confidence=0.67,
            observed_at=datetime(2026, 6, 5, 5, 30, tzinfo=EASTERN_TZ),
        )
        decision = self.approver.evaluate(candidate)
        self.assertFalse(decision.approved)
        self.assertIn("confidence too low: got 0.67, need 0.68", decision.reasons)


class SignalPipelineShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = SignalPipelineShell(PHASE1_CONTRACT)

    def test_generates_continuation_signal_for_strong_london_snapshot(self) -> None:
        snapshot = FeatureSnapshot(
            pair="GBP_USD",
            direction="BUY",
            observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
            spread_pips=1.1,
            trend_score=0.91,
            momentum_score=0.87,
            retest_score=0.73,
            breakout_score=0.83,
            scalp_score=0.62,
            volatility_score=0.68,
        )
        workflows = {signal.workflow for signal in self.pipeline.scan(snapshot)}
        self.assertIn("continuation", workflows)

    def test_skips_off_session_snapshot(self) -> None:
        snapshot = FeatureSnapshot(
            pair="USD_JPY",
            direction="SELL",
            observed_at=datetime(2026, 6, 4, 20, 0, tzinfo=EASTERN_TZ),
            spread_pips=1.0,
            trend_score=0.90,
            momentum_score=0.90,
            retest_score=0.75,
            breakout_score=0.80,
            scalp_score=0.82,
            volatility_score=0.70,
        )
        self.assertEqual(self.pipeline.scan(snapshot), ())


class StrategyPackTests(unittest.TestCase):
    def test_april14_momentum_pack_is_selectable_and_momentum_only(self) -> None:
        pack = load_strategy_pack("april14_momentum_3am_9am")

        self.assertEqual(pack.pack_id, "april14_momentum_3am_9am")
        self.assertEqual(pack.metadata["primary_strategy_label"], "momentum")
        self.assertIn("momentum", pack.workflows)
        self.assertNotIn("scalp", pack.workflows)
        self.assertEqual(pack.metadata["active_entry_window_et"], "03:00-08:30")

    def test_post9_ema_fib_pack_is_selectable_and_continuation_only(self) -> None:
        pack = load_strategy_pack("post_9am_ema_fib_momentum_continuation")

        self.assertEqual(pack.pack_id, "post_9am_ema_fib_momentum_continuation")
        self.assertEqual(pack.metadata["primary_strategy_label"], "momentum_continuation")
        self.assertEqual(pack.metadata["active_entry_window_et"], "09:00-11:30")
        self.assertIn("continuation", pack.workflows)
        self.assertNotIn("scalp", pack.workflows)
        self.assertNotIn("reversal", pack.workflows)

        for pair in ("AUD_USD", "EUR_USD", "NZD_USD", "USD_CAD", "USD_CHF"):
            self.assertIn(pair, pack.metadata["proven_pairs"])

    def test_april14_pack_documents_all_evidence_pairs(self) -> None:
        pack = load_strategy_pack("april14_momentum_3am_9am")
        timestamps = "\n".join(pack.metadata["known_winning_timestamps_et"])

        for pair in (
            "USD_CHF",
            "GBP_USD",
            "EUR_USD",
            "NZD_USD",
            "USD_CAD",
            "AUD_USD",
            "USD_JPY",
        ):
            self.assertIn(pair, PHASE1_CONTRACT.trading_pairs)
            self.assertIn(pair, timestamps)

    def test_legacy_pack_keeps_existing_scalp_exit_behavior(self) -> None:
        pack = load_strategy_pack("legacy_phase1")
        plan = TradePlan(
            pair="EUR_USD",
            direction="BUY",
            workflow="scalp",
            units=50_000,
            confidence=0.90,
            votes=4,
            rank_score=95.0,
            rationale=("test",),
        )
        exit_plan = build_exit_plan(plan, strategy_pack=pack)
        self.assertEqual(exit_plan.profile_name, "wick_scratch_3bar")
        self.assertEqual(exit_plan.target_pips, 12.6)

    def test_turboscribe_pack_changes_signal_rationale_and_scalp_exit_behavior(self) -> None:
        pack = load_strategy_pack("turboscribe_phase1")
        pipeline = SignalPipelineShell(PHASE1_CONTRACT, strategy_pack=pack)
        snapshot = FeatureSnapshot(
            pair="GBP_USD",
            direction="BUY",
            observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
            spread_pips=1.1,
            trend_score=0.91,
            momentum_score=0.87,
            retest_score=0.73,
            breakout_score=0.83,
            scalp_score=0.82,
            volatility_score=0.68,
            top_down_bias_score=0.82,
            ema_9_reclaim_score=0.78,
            first_touch_quality=0.74,
            late_touch_penalty=0.10,
            post_break_acceptance_score=0.77,
            failed_break_risk=0.05,
            two_r_available=0.80,
        )
        signals = {signal.workflow: signal for signal in pipeline.scan(snapshot)}

        self.assertIn("continuation", signals)
        self.assertIn("top-down bias proxy aligned", signals["continuation"].rationale)
        self.assertIn("scalp", signals)

        trade_plan = TradePlan(
            pair="GBP_USD",
            direction="BUY",
            workflow="scalp",
            units=50_000,
            confidence=signals["scalp"].confidence,
            votes=signals["scalp"].votes,
            rank_score=100.0,
            rationale=signals["scalp"].rationale,
        )
        exit_plan = build_exit_plan(trade_plan, strategy_pack=pack)
        self.assertEqual(exit_plan.profile_name, "turboscribe_scalp_2r")
        self.assertEqual(exit_plan.target_pips, 20.0)


class CartridgeScheduleTests(unittest.TestCase):
    def test_selects_frozen_morning_cartridge_through_830_minute(self) -> None:
        selection = select_active_cartridge(datetime(2026, 6, 5, 8, 30, 30, tzinfo=EASTERN_TZ))

        self.assertTrue(selection.entry_allowed)
        self.assertEqual(selection.pack_id, "april14_momentum_3am_9am")
        self.assertEqual(selection.window.window_id, "frozen_3am_830am_momentum")

    def test_blocks_transition_between_frozen_and_post9_windows(self) -> None:
        selection = select_active_cartridge(datetime(2026, 6, 5, 8, 31, tzinfo=EASTERN_TZ))

        self.assertFalse(selection.entry_allowed)
        self.assertIsNone(selection.strategy_pack)
        self.assertEqual(selection.pack_id, "NO_ACTIVE_ENTRY_CARTRIDGE")

    def test_selects_post9_cartridge_until_1130_boundary(self) -> None:
        active = select_active_cartridge(datetime(2026, 6, 5, 9, 0, tzinfo=EASTERN_TZ))
        still_active = select_active_cartridge(datetime(2026, 6, 5, 11, 29, 59, tzinfo=EASTERN_TZ))
        closed = select_active_cartridge(datetime(2026, 6, 5, 11, 30, tzinfo=EASTERN_TZ))

        self.assertEqual(active.pack_id, "post_9am_ema_fib_momentum_continuation")
        self.assertEqual(still_active.pack_id, "post_9am_ema_fib_momentum_continuation")
        self.assertFalse(closed.entry_allowed)


class AutonomyCommanderTests(unittest.TestCase):
    def _plan(
        self,
        *,
        pair: str = "GBP_USD",
        workflow: str = "continuation",
        confidence: float = 0.86,
        votes: int = 3,
    ) -> TradePlan:
        return TradePlan(
            pair=pair,
            direction="BUY",
            workflow=workflow,
            units=30_000,
            confidence=confidence,
            votes=votes,
            rank_score=90.0,
            rationale=("test setup",),
        )

    def _snapshot(
        self,
        *,
        pair: str = "GBP_USD",
        workflow_time: datetime | None = None,
        two_r_available: float = 0.80,
    ) -> FeatureSnapshot:
        return FeatureSnapshot(
            pair=pair,
            direction="BUY",
            observed_at=workflow_time or datetime(2026, 6, 5, 4, 15, tzinfo=EASTERN_TZ),
            spread_pips=1.2,
            trend_score=0.88,
            momentum_score=0.84,
            retest_score=0.75,
            breakout_score=0.78,
            scalp_score=0.82,
            volatility_score=0.72,
            top_down_bias_score=0.78,
            ema_9_reclaim_score=0.72,
            first_touch_quality=0.74,
            post_break_acceptance_score=0.76,
            chop_penalty=0.18,
            failed_break_risk=0.10,
            two_r_available=two_r_available,
        )

    def _price(self, pair: str = "GBP_USD", spread_pips: float = 1.2) -> OandaPriceSnapshot:
        return OandaPriceSnapshot(pair=pair, bid=1.3000, ask=1.30012, spread_pips=spread_pips)

    def test_a_grade_momentum_plan_can_trade_in_core_window(self) -> None:
        commander = AutonomyCommander(
            PHASE1_CONTRACT,
            strategy_pack=load_strategy_pack("april14_momentum_3am_9am"),
        )
        plan = self._plan(workflow="momentum")
        decision = commander.evaluate(
            planned_trades=(plan,),
            snapshots=(self._snapshot(),),
            prices=(self._price(),),
            observed_at=datetime(2026, 6, 5, 4, 15, tzinfo=EASTERN_TZ),
        )

        self.assertEqual(decision.status, TradeMode.A_GRADE)
        self.assertEqual(decision.approved_plans, (plan,))
        self.assertEqual(decision.plan_decisions[0].action, CommanderAction.APPROVE)

    def test_april14_momentum_blocks_entries_at_9am(self) -> None:
        commander = AutonomyCommander(
            PHASE1_CONTRACT,
            strategy_pack=load_strategy_pack("april14_momentum_3am_9am"),
        )
        plan = self._plan(workflow="momentum")
        after_window = datetime(2026, 4, 14, 9, 0, tzinfo=EASTERN_TZ)
        decision = commander.evaluate(
            planned_trades=(plan,),
            snapshots=(self._snapshot(workflow_time=after_window),),
            prices=(self._price(),),
            observed_at=after_window,
        )

        self.assertEqual(decision.status, TradeMode.NO_TRADE)
        self.assertEqual(decision.approved_plans, ())
        self.assertIn("no verified A/B/C edge grade matched", decision.plan_decisions[0].reasons)

    def test_post9_ema_fib_continuation_can_trade_inside_its_window(self) -> None:
        commander = AutonomyCommander(
            PHASE1_CONTRACT,
            strategy_pack=load_strategy_pack("post_9am_ema_fib_momentum_continuation"),
        )
        observed_at = datetime(2026, 6, 5, 10, 5, tzinfo=EASTERN_TZ)
        plan = self._plan(pair="EUR_USD", workflow="continuation", confidence=0.86, votes=6)
        decision = commander.evaluate(
            planned_trades=(plan,),
            snapshots=(self._snapshot(pair="EUR_USD", workflow_time=observed_at),),
            prices=(self._price(pair="EUR_USD"),),
            observed_at=observed_at,
        )

        self.assertEqual(decision.status, TradeMode.A_GRADE)
        self.assertEqual(decision.approved_plans, (plan,))

    def test_post9_ema_fib_continuation_blocks_unproven_pair_and_1130_boundary(self) -> None:
        commander = AutonomyCommander(
            PHASE1_CONTRACT,
            strategy_pack=load_strategy_pack("post_9am_ema_fib_momentum_continuation"),
        )
        observed_at = datetime(2026, 6, 5, 10, 5, tzinfo=EASTERN_TZ)
        gbp_plan = self._plan(pair="GBP_USD", workflow="continuation", confidence=0.86, votes=6)
        gbp_decision = commander.evaluate(
            planned_trades=(gbp_plan,),
            snapshots=(self._snapshot(pair="GBP_USD", workflow_time=observed_at),),
            prices=(self._price(pair="GBP_USD"),),
            observed_at=observed_at,
        )
        self.assertEqual(gbp_decision.approved_plans, ())

        boundary = datetime(2026, 6, 5, 11, 30, tzinfo=EASTERN_TZ)
        eur_plan = self._plan(pair="EUR_USD", workflow="continuation", confidence=0.86, votes=6)
        boundary_decision = commander.evaluate(
            planned_trades=(eur_plan,),
            snapshots=(self._snapshot(pair="EUR_USD", workflow_time=boundary),),
            prices=(self._price(pair="EUR_USD"),),
            observed_at=boundary,
        )
        self.assertEqual(boundary_decision.approved_plans, ())

    def test_market_closed_blocks_otherwise_valid_plan(self) -> None:
        commander = AutonomyCommander(PHASE1_CONTRACT)
        closed_time = datetime(2026, 6, 6, 10, 0, tzinfo=EASTERN_TZ)
        decision = commander.evaluate(
            planned_trades=(self._plan(),),
            snapshots=(self._snapshot(workflow_time=closed_time),),
            prices=(self._price(),),
            observed_at=closed_time,
        )

        self.assertEqual(decision.status, TradeMode.NO_TRADE)
        self.assertEqual(decision.approved_plans, ())
        self.assertIn("forex market is closed", decision.plan_decisions[0].reasons)

    def test_c_grade_scalp_requires_clean_two_r_and_spread(self) -> None:
        commander = AutonomyCommander(PHASE1_CONTRACT)
        plan = self._plan(workflow="scalp", confidence=0.70, votes=2)
        decision = commander.evaluate(
            planned_trades=(plan,),
            snapshots=(self._snapshot(two_r_available=0.80),),
            prices=(self._price(spread_pips=1.1),),
            observed_at=datetime(2026, 6, 5, 4, 15, tzinfo=EASTERN_TZ),
        )

        self.assertEqual(decision.status, TradeMode.C_GRADE)
        self.assertEqual(decision.approved_plans, (plan,))

        blocked = commander.evaluate(
            planned_trades=(plan,),
            snapshots=(self._snapshot(two_r_available=0.20),),
            prices=(self._price(spread_pips=1.1),),
            observed_at=datetime(2026, 6, 5, 4, 15, tzinfo=EASTERN_TZ),
        )
        self.assertEqual(blocked.approved_plans, ())
        self.assertIn("no verified A/B/C edge grade matched", blocked.plan_decisions[0].reasons)

    def test_bad_spread_regime_blocks_new_entries(self) -> None:
        commander = AutonomyCommander(
            PHASE1_CONTRACT,
            policy=CommanderPolicy(max_average_spread_pips=1.0),
        )
        decision = commander.evaluate(
            planned_trades=(self._plan(),),
            snapshots=(self._snapshot(),),
            prices=(self._price(spread_pips=1.5),),
            observed_at=datetime(2026, 6, 5, 4, 15, tzinfo=EASTERN_TZ),
        )

        self.assertEqual(decision.approved_plans, ())
        self.assertIn("average spread regime is too wide", decision.plan_decisions[0].reasons)


class ReplayEngineTests(unittest.TestCase):
    def test_replay_demo_fixture_runs(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "replay_input.jsonl"
        engine = ReplayEngine(PHASE1_CONTRACT)
        snapshots = engine.load_jsonl(fixture_path)
        summary, records = engine.run(snapshots)
        self.assertEqual(summary.snapshots_seen, 5)
        self.assertGreaterEqual(summary.raw_signals, 1)
        self.assertGreaterEqual(summary.approved_signals, 1)
        self.assertEqual(summary.raw_signals, len(records))

    def test_april14_momentum_fixture_replays_known_winner_timestamps(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "april14_momentum_winners.jsonl"
        pack = load_strategy_pack("april14_momentum_3am_9am")
        engine = ReplayEngine(PHASE1_CONTRACT, strategy_pack=pack)
        snapshots = engine.load_jsonl(fixture_path)
        summary, records = engine.run(snapshots)

        self.assertEqual(summary.snapshots_seen, 10)
        self.assertEqual(summary.raw_signals, 10)
        self.assertEqual(summary.approved_signals, 10)
        self.assertEqual(summary.approvals_by_workflow, {"momentum": 10})
        self.assertEqual(
            {record.signal.observed_at.strftime("%H:%M") for record in records},
            {"03:00", "03:15", "04:15", "05:45", "06:15", "07:00", "08:30"},
        )


class PeakGivebackOverlayTests(unittest.TestCase):
    def test_session_key_rolls_at_5pm_et(self) -> None:
        self.assertEqual(
            session_key_for(datetime(2026, 4, 13, 16, 59, tzinfo=EASTERN_TZ)),
            "2026-04-13",
        )
        self.assertEqual(
            session_key_for(datetime(2026, 4, 13, 17, 0, tzinfo=EASTERN_TZ)),
            "2026-04-14",
        )

    def test_peak_giveback_arms_then_flattens_after_175_giveback(self) -> None:
        policy = PeakGivebackPolicy(arm_gain_usd=350.0, giveback_from_peak_usd=175.0)
        observed_at = datetime(2026, 4, 14, 3, 0, tzinfo=EASTERN_TZ)
        state = PeakGivebackState(
            session_key=session_key_for(observed_at),
            baseline_nav=10_000.0,
            peak_nav=10_000.0,
            armed=False,
        )

        armed = evaluate_peak_giveback(
            state,
            nav=10_360.0,
            observed_at=observed_at,
            policy=policy,
        )
        self.assertEqual(armed.action, "arm")
        self.assertTrue(armed.state.armed)

        flattened = evaluate_peak_giveback(
            armed.state,
            nav=10_180.0,
            observed_at=observed_at,
            policy=policy,
        )
        self.assertEqual(flattened.action, "flatten")
        self.assertTrue(flattened.should_flatten)
        self.assertEqual(flattened.giveback_from_peak_usd, 180.0)


class SignalSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = SignalPipelineShell(PHASE1_CONTRACT)
        self.selector = SignalSelector(PHASE1_CONTRACT)

    def test_selector_prefers_best_unique_pairs(self) -> None:
        snapshots = (
            FeatureSnapshot(
                pair="GBP_USD",
                direction="BUY",
                observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                spread_pips=1.1,
                trend_score=0.91,
                momentum_score=0.87,
                retest_score=0.73,
                breakout_score=0.83,
                scalp_score=0.62,
                volatility_score=0.68,
            ),
            FeatureSnapshot(
                pair="USD_CAD",
                direction="SELL",
                observed_at=datetime(2026, 6, 4, 13, 15, tzinfo=EASTERN_TZ),
                spread_pips=1.6,
                trend_score=0.80,
                momentum_score=0.83,
                retest_score=0.76,
                breakout_score=0.79,
                scalp_score=0.77,
                volatility_score=0.72,
            ),
        )
        signals = []
        for snapshot in snapshots:
            signals.extend(self.pipeline.scan(snapshot))

        result = self.selector.select(tuple(signals), open_slots=2)
        self.assertEqual(len(result.selected), 2)
        self.assertEqual(result.selected[0].signal.pair, "GBP_USD")
        self.assertEqual(result.selected[1].signal.pair, "USD_CAD")

    def test_selector_respects_open_pair_conflicts(self) -> None:
        snapshot = FeatureSnapshot(
            pair="GBP_USD",
            direction="BUY",
            observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
            spread_pips=1.1,
            trend_score=0.91,
            momentum_score=0.87,
            retest_score=0.73,
            breakout_score=0.83,
            scalp_score=0.62,
            volatility_score=0.68,
        )
        signals = self.pipeline.scan(snapshot)
        result = self.selector.select(signals, open_pairs=("GBP_USD",), open_slots=2)
        self.assertEqual(result.selected, ())
        self.assertTrue(any("already occupied" in reason for reason in result.skipped_reasons.values()))


class TradePlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = SignalPipelineShell(PHASE1_CONTRACT)
        self.sizer = PositionSizer(PHASE1_CONTRACT)

    def test_position_sizer_uses_base_units_for_highest_quality_signal(self) -> None:
        snapshot = FeatureSnapshot(
            pair="GBP_USD",
            direction="BUY",
            observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
            spread_pips=1.1,
            trend_score=0.96,
            momentum_score=0.92,
            retest_score=0.86,
            breakout_score=0.91,
            scalp_score=0.70,
            volatility_score=0.75,
        )
        signal = self.pipeline.scan(snapshot)[0]
        self.assertEqual(self.sizer.units_for(signal), PHASE1_CONTRACT.base_units)

    def test_cycle_engine_respects_existing_open_position(self) -> None:
        snapshots = (
            FeatureSnapshot(
                pair="GBP_USD",
                direction="BUY",
                observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                spread_pips=1.1,
                trend_score=0.91,
                momentum_score=0.87,
                retest_score=0.73,
                breakout_score=0.83,
                scalp_score=0.62,
                volatility_score=0.68,
            ),
            FeatureSnapshot(
                pair="USD_CAD",
                direction="SELL",
                observed_at=datetime(2026, 6, 4, 13, 15, tzinfo=EASTERN_TZ),
                spread_pips=1.6,
                trend_score=0.80,
                momentum_score=0.83,
                retest_score=0.76,
                breakout_score=0.79,
                scalp_score=0.77,
                volatility_score=0.72,
            ),
        )
        engine = CycleEngine(PHASE1_CONTRACT)
        portfolio = PortfolioState(
            open_positions=(
                OpenPosition(
                    pair="GBP_USD",
                    direction="BUY",
                    units=50_000,
                    workflow="continuation",
                ),
            )
        )
        result = engine.run(snapshots, portfolio=portfolio)
        self.assertEqual(len(result.planned_trades), 1)
        self.assertEqual(result.planned_trades[0].pair, "USD_CAD")

    def test_order_preview_builder_places_buy_stop_below_entry(self) -> None:
        preview_builder = OrderPreviewBuilder()
        plan = self.pipeline.scan(
            FeatureSnapshot(
                pair="GBP_USD",
                direction="BUY",
                observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                spread_pips=1.1,
                trend_score=0.96,
                momentum_score=0.92,
                retest_score=0.86,
                breakout_score=0.91,
                scalp_score=0.70,
                volatility_score=0.75,
            )
        )[0]
        trade_plan = CycleEngine(PHASE1_CONTRACT).run(
            (
                FeatureSnapshot(
                    pair="GBP_USD",
                    direction="BUY",
                    observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                    spread_pips=1.1,
                    trend_score=0.96,
                    momentum_score=0.92,
                    retest_score=0.86,
                    breakout_score=0.91,
                    scalp_score=0.70,
                    volatility_score=0.75,
                ),
            )
        ).planned_trades[0]
        preview = preview_builder.build(
            trade_plan,
            OandaPriceSnapshot(pair="GBP_USD", bid=1.3000, ask=1.3002, spread_pips=2.0),
        )
        self.assertLess(preview.stop_price, preview.entry_price)
        self.assertGreater(preview.target_price, preview.entry_price)

    def test_order_preview_builder_places_sell_stop_above_entry(self) -> None:
        preview_builder = OrderPreviewBuilder()
        trade_plan = CycleEngine(PHASE1_CONTRACT).run(
            (
                FeatureSnapshot(
                    pair="USD_CAD",
                    direction="SELL",
                    observed_at=datetime(2026, 6, 4, 13, 15, tzinfo=EASTERN_TZ),
                    spread_pips=1.6,
                    trend_score=0.80,
                    momentum_score=0.83,
                    retest_score=0.76,
                    breakout_score=0.79,
                    scalp_score=0.77,
                    volatility_score=0.72,
                ),
            )
        ).planned_trades[0]
        preview = preview_builder.build(
            trade_plan,
            OandaPriceSnapshot(pair="USD_CAD", bid=1.3900, ask=1.3902, spread_pips=2.0),
        )
        self.assertGreater(preview.stop_price, preview.entry_price)
        self.assertLess(preview.target_price, preview.entry_price)

    def test_manager_holds_trade_inside_working_range(self) -> None:
        trade_plan = CycleEngine(PHASE1_CONTRACT).run(
            (
                FeatureSnapshot(
                    pair="GBP_USD",
                    direction="BUY",
                    observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                    spread_pips=1.1,
                    trend_score=0.96,
                    momentum_score=0.92,
                    retest_score=0.86,
                    breakout_score=0.91,
                    scalp_score=0.70,
                    volatility_score=0.75,
                ),
            )
        ).planned_trades[0]
        preview = OrderPreviewBuilder().build(
            trade_plan,
            OandaPriceSnapshot(pair="GBP_USD", bid=1.3000, ask=1.3002, spread_pips=2.0),
        )
        position = ManagedPosition(
            pair="GBP_USD",
            direction="BUY",
            entry_price=preview.entry_price,
            current_price=preview.entry_price + 0.0008,
            stop_price=preview.stop_price,
            target_price=preview.target_price,
        )
        decision = manage_position(position, build_exit_plan(trade_plan))
        self.assertEqual(decision.action, "hold")

    def test_manager_arms_green_lock_on_strong_profit(self) -> None:
        trade_plan = CycleEngine(PHASE1_CONTRACT).run(
            (
                FeatureSnapshot(
                    pair="GBP_USD",
                    direction="BUY",
                    observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                    spread_pips=1.1,
                    trend_score=0.96,
                    momentum_score=0.92,
                    retest_score=0.86,
                    breakout_score=0.91,
                    scalp_score=0.70,
                    volatility_score=0.75,
                ),
            )
        ).planned_trades[0]
        preview = OrderPreviewBuilder().build(
            trade_plan,
            OandaPriceSnapshot(pair="GBP_USD", bid=1.3000, ask=1.3002, spread_pips=2.0),
        )
        position = ManagedPosition(
            pair="GBP_USD",
            direction="BUY",
            entry_price=preview.entry_price,
            current_price=preview.entry_price + 0.0018,
            stop_price=preview.stop_price,
            target_price=preview.target_price,
        )
        decision = manage_position(position, build_exit_plan(trade_plan))
        self.assertEqual(decision.action, "move_stop")
        self.assertIsNotNone(decision.suggested_stop_price)

    def test_manager_closes_at_target(self) -> None:
        trade_plan = CycleEngine(PHASE1_CONTRACT).run(
            (
                FeatureSnapshot(
                    pair="GBP_USD",
                    direction="BUY",
                    observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                    spread_pips=1.1,
                    trend_score=0.96,
                    momentum_score=0.92,
                    retest_score=0.86,
                    breakout_score=0.91,
                    scalp_score=0.70,
                    volatility_score=0.75,
                ),
            )
        ).planned_trades[0]
        preview = OrderPreviewBuilder().build(
            trade_plan,
            OandaPriceSnapshot(pair="GBP_USD", bid=1.3000, ask=1.3002, spread_pips=2.0),
        )
        position = ManagedPosition(
            pair="GBP_USD",
            direction="BUY",
            entry_price=preview.entry_price,
            current_price=preview.target_price,
            stop_price=preview.stop_price,
            target_price=preview.target_price,
        )
        decision = manage_position(position, build_exit_plan(trade_plan))
        self.assertEqual(decision.action, "close_target")


class EvidenceTests(unittest.TestCase):
    def test_loads_real_counterfactual_windows(self) -> None:
        path = (
            "/home/rfing/READ_ONLY_LEGACY/backups/"
            "RESTORED_PRE10AM_TRANSFER_READY_20260430_025439/repos/"
            "OAD_DEV/analysis/oanda_loss_manager_counterfactual_apr14_session_20260421.json"
        )
        windows = load_counterfactual_windows(path)
        self.assertTrue(windows)
        self.assertIsInstance(windows[0], HistoricalWindow)
        summary = summarize_windows(windows)
        self.assertGreater(summary.best_window_pnl_usd, 0.0)
        self.assertIn("momentum", summary.pnl_by_strategy)


class OandaHelperTests(unittest.TestCase):
    def test_spread_pips_uses_jpy_scale(self) -> None:
        self.assertEqual(_spread_pips("USD_JPY", 155.100, 155.120), 2.0)

    def test_spread_pips_uses_standard_scale(self) -> None:
        self.assertEqual(_spread_pips("EUR_USD", 1.1000, 1.1002), 2.0)

    def test_reads_env_file(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "test_env.env"
        values = _read_env_file(fixture)
        self.assertEqual(values["OANDA_ACCOUNT_ID"], "acct-test")
        self.assertEqual(values["OANDA_TOKEN"], "token-test")

    def test_oanda_config_from_env_file(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "test_env.env"
        config = OandaPracticeConfig.from_env_file(fixture)
        self.assertEqual(config.account_id, "acct-test")
        self.assertEqual(config.api_token, "token-test")
        self.assertIn("fxpractice", config.api_base)

    def test_oanda_config_rejects_live_money_endpoint(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "test_env_live.env"
        with self.assertRaises(RuntimeError):
            OandaPracticeConfig.from_env_file(fixture)

    def test_extract_trade_ids_from_order_response(self) -> None:
        payload = {
            "orderFillTransaction": {
                "tradeOpened": {"tradeID": "155588"},
            }
        }
        self.assertEqual(extract_trade_ids_from_order_response(payload), ("155588",))


class MarketFeatureTests(unittest.TestCase):
    def test_parse_oanda_mid_candles(self) -> None:
        raw = (
            {
                "time": "2026-06-04T09:00:00Z",
                "complete": True,
                "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"},
            },
        )
        parsed = parse_oanda_mid_candles(raw)
        self.assertEqual(len(parsed), 1)
        self.assertIsInstance(parsed[0], MidCandle)

    def test_build_feature_snapshot_from_candles(self) -> None:
        candles = tuple(
            MidCandle(
                time=datetime(2026, 6, 4, 9, idx, tzinfo=ZoneInfo("UTC")),
                open=1.1000 + (idx * 0.0001),
                high=1.1005 + (idx * 0.0001),
                low=1.0995 + (idx * 0.0001),
                close=1.1003 + (idx * 0.0001),
            )
            for idx in range(20)
        )
        price = OandaPriceSnapshot(pair="EUR_USD", bid=1.1020, ask=1.1022, spread_pips=2.0)
        snapshot = build_feature_snapshot_from_candles("EUR_USD", price, candles)
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.pair, "EUR_USD")
        self.assertIn(snapshot.direction, ("BUY", "SELL"))

    def test_builds_turboscribe_cartridge_feature_slots_from_candles(self) -> None:
        candles = tuple(
            MidCandle(
                time=datetime(2026, 6, 4, 9, idx, tzinfo=ZoneInfo("UTC")),
                open=1.1000 + (idx * 0.00015),
                high=1.1007 + (idx * 0.00015),
                low=1.0998 + (idx * 0.00015),
                close=1.1005 + (idx * 0.00015),
            )
            for idx in range(40)
        )
        price = OandaPriceSnapshot(pair="EUR_USD", bid=1.1060, ask=1.1062, spread_pips=2.0)
        snapshot = build_feature_snapshot_from_candles("EUR_USD", price, candles)

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertGreaterEqual(snapshot.top_down_bias_score, 0.0)
        self.assertLessEqual(snapshot.top_down_bias_score, 1.0)
        self.assertGreaterEqual(snapshot.ema_9_reclaim_score, 0.0)
        self.assertLessEqual(snapshot.failed_break_risk, 1.0)
        self.assertGreaterEqual(snapshot.two_r_available, 0.0)


class RuntimeStateTests(unittest.TestCase):
    def test_records_from_submission_tracks_trade_id(self) -> None:
        plan = CycleEngine(PHASE1_CONTRACT).run(
            (
                FeatureSnapshot(
                    pair="GBP_USD",
                    direction="BUY",
                    observed_at=datetime(2026, 6, 4, 5, 0, tzinfo=EASTERN_TZ),
                    spread_pips=1.1,
                    trend_score=0.96,
                    momentum_score=0.92,
                    retest_score=0.86,
                    breakout_score=0.91,
                    scalp_score=0.70,
                    volatility_score=0.75,
                ),
            )
        ).planned_trades[0]
        preview = OrderPreviewBuilder().build(
            plan,
            OandaPriceSnapshot(pair="GBP_USD", bid=1.3000, ask=1.3002, spread_pips=2.0),
        )
        response = {"orderFillTransaction": {"tradeOpened": {"tradeID": "155588"}}}
        records = records_from_submission(plan, preview, response, "2026-06-04T09:00:00-04:00")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].trade_id, "155588")
        self.assertEqual(records[0].profile_name, preview.exit_plan.profile_name)

    def test_runtime_state_round_trips_to_disk(self) -> None:
        state = RuntimeState(
            active_trades=(
                ManagedTradeRecord(
                    trade_id="155588",
                    pair="GBP_USD",
                    direction="BUY",
                    units=50_000,
                    workflow="continuation",
                    confidence=0.91,
                    votes=4,
                    rank_score=115.0,
                    rationale=("trend aligned",),
                    profile_name="clip_75pct_tp",
                    entry_price=1.3002,
                    stop_price=1.2992,
                    target_price=1.30272,
                    opened_at_et="2026-06-04T09:00:00-04:00",
                    last_synced_at_et="2026-06-04T09:00:00-04:00",
                    last_action="submitted",
                ),
            ),
            closed_trades=(
                ClosedTradeRecord(
                    trade_id="144000",
                    pair="EUR_USD",
                    direction="SELL",
                    workflow="scalp",
                    closed_at_et="2026-06-04T10:00:00-04:00",
                    close_reason="target reached",
                    entry_price=1.1010,
                    stop_price=1.1020,
                    target_price=1.0997,
                ),
            ),
        )
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "runtime_state.json"
            save_runtime_state(state, path)
            loaded = load_runtime_state(path)
        self.assertEqual(loaded, state)

    def test_reconcile_adopts_unknown_broker_trade(self) -> None:
        state = RuntimeState()
        broker_trades = (
            OandaTradeSnapshot(
                trade_id="155588",
                pair="USD_CAD",
                direction="BUY",
                units=50_000,
                entry_price=1.3900,
                unrealized_pl=12.0,
                stop_price=1.3890,
                target_price=1.3925,
            ),
        )
        reconciled, actions = reconcile_state_with_broker(
            state,
            broker_trades,
            "2026-06-04T09:15:00-04:00",
        )
        self.assertEqual(len(reconciled.active_trades), 1)
        self.assertEqual(reconciled.active_trades[0].trade_id, "155588")
        self.assertEqual(actions[0].action, "adopt")

    def test_management_actions_suggest_green_lock_move(self) -> None:
        state = RuntimeState(
            active_trades=(
                ManagedTradeRecord(
                    trade_id="155588",
                    pair="GBP_USD",
                    direction="BUY",
                    units=50_000,
                    workflow="continuation",
                    confidence=0.91,
                    votes=4,
                    rank_score=115.0,
                    rationale=("trend aligned",),
                    profile_name="clip_75pct_tp",
                    entry_price=1.3002,
                    stop_price=1.2992,
                    target_price=1.30272,
                    opened_at_et="2026-06-04T09:00:00-04:00",
                    last_synced_at_et="2026-06-04T09:00:00-04:00",
                    last_action="submitted",
                ),
            )
        )
        broker_trades = (
            OandaTradeSnapshot(
                trade_id="155588",
                pair="GBP_USD",
                direction="BUY",
                units=50_000,
                entry_price=1.3002,
                unrealized_pl=80.0,
                stop_price=1.2992,
                target_price=1.30272,
            ),
        )
        price_map = {
            "GBP_USD": OandaPriceSnapshot(pair="GBP_USD", bid=1.3021, ask=1.3023, spread_pips=2.0),
        }
        actions = evaluate_management_actions(state, broker_trades, price_map)
        self.assertEqual(actions[0].action, "move_stop")
        self.assertIsNotNone(actions[0].suggested_stop_price)


if __name__ == "__main__":
    unittest.main()
