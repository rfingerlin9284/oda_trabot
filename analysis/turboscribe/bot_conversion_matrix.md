# TurboScribe Bot Conversion Matrix

Generated UTC: 2026-06-05T17:41:17.693162+00:00

Scope: fresh scan of TurboScribe-named local files. Windows C: exact TurboScribe filename search found 0. WSL `/home/rfing`: 76 TurboScribe-named matches, 73 zip matches, 9 unique archive hashes.

Manifest check: scanned 374 WSL-home zip files; found 78 TurboScribe-related zip hits. 73 were direct TurboScribe-named zips and 5 were generic backup zips containing TurboScribe entries already represented by the same export families.

## Ready / Candidate Matrix

| Strategy | Status | Exact Extracted Data | Bot Conversion |
|---|---|---|---|
| `top_down_bias_gate` | `phase1_ready_as_filter` | bias_timeframes=['weekly', 'daily', '4 hour']; entry_alignment_ladder=['2 hour', '1 hour', '30 minute', '15 minute'] | add/use: top_down_bias_score, weekly_bias, daily_bias, h4_bias, entry_timeframe_alignment_score |
| `ema_9_continuation_scalp` | `phase1_ready_core_workflow` | primary_ema=9; context_ma=200 SMA or 200 EMA context only; risk_reward_floor=2:1 minimum, 3:1 preferred, 4:1+ stretch only after proof | add/use: ema_9_distance, ema_9_reclaim_score, first_touch_quality, late_touch_penalty |
| `range_bounce_breakout_classifier` | `phase1_ready_filter` | range_levels=['support zone', 'resistance zone']; narrow_range_action=breakout strategy, not bounce strategy; wide_range_action=trade bounces only at zones | add/use: range_width_score, support_rejection_score, resistance_rejection_score, chop_penalty |
| `false_breakout_filter` | `phase1_ready_risk_filter` | example_consolidation_rule=about half the initial move; source example: 15-bar move wants about 7 minutes consolidation; multi_timeframe_break_pressure=1 minute plus 15 minute level pressure | add/use: break_followthrough_score, failed_break_risk, post_break_acceptance_score, level_touch_count |
| `order_block_retest` | `phase2_candidate_requires_new_features` | structure_timeframes_seen=['4 hour', '1 hour', '15 minute', '5 minute', '1 minute']; validity_requirements=['break of structure', 'unmitigated block', 'liquidity/volume/inefficiency context'] | add/use: order_block_zone, order_block_freshness, break_of_structure_score, mitigation_status, structure_invalidation_price |
| `liquidity_sweep_fvg_midpoint` | `phase2_candidate_requires_new_features` | entry_price=50% / midpoint of the fair value gap; confirmation_timeframes=['5 minute', '1 minute']; target_type=higher-timeframe buy-side/sell-side liquidity | add/use: liquidity_sweep_score, fvg_zone, fvg_midpoint_price, choch_score, htf_liquidity_target |
| `simple_5m_session_scalp` | `phase2_candidate_after_session_replay` | active_work_time=less than 90 minutes a day; bias_candle=first 15-minute candle direction; minimum_r_multiple=2R | add/use: session_open_15m_bias, session_retest_score, two_r_available |
| `orderflow_value_area_confirmation` | `research_only_for_oanda_spot_fx` | concepts=['value area', 'point of control', 'delta', 'absorption', 'imbalance'] | add/use: value_area_state, delta_proxy, absorption_proxy |

## Highest Signal Conversion Path

1. Add a top-down bias gate using weekly/daily/4H direction before current `continuation`, `second_chance`, and `scalp` workflows.
2. Add 9 EMA first-touch/reclaim features so the current score shell can distinguish clean continuation from late chase entries.
3. Add range and false-breakout filters before breakout entries are allowed to rank highly.
4. Keep order block/FVG/liquidity-sweep logic as Phase 2 until zone extraction and replay tests exist.
5. Keep orderflow/value-area logic disabled unless a true orderflow or credible volume proxy feed is attached.

## Files

- `archive_inventory.json`: full deduped source archive inventory by SHA-256.
- `document_inventory.csv`: best text-bearing document per archive/title with numeric hits and relevance terms.
- `strategy_specs.json`: bot-ready structured conversion data.
