# Live Paper Outside-Window Audit

This audit scans read-only legacy logs for profitable OANDA practice/live paper close receipts outside the frozen 3 AM-9 AM ET momentum cartridge window.

## Guardrails

- Accepted evidence is log data only, not replay/result/counterfactual JSON.
- Coinbase and TurboScribe paths are excluded from this pass.
- The protected cartridge window is treated as 03:00 through 08:59 ET; close receipts inside that window are excluded.
- `high_confidence_practice_receipt` means a profitable close was linked to a matching `PRACTICE` OCO order with `live_api=true` and `visible_in_oanda=true`.
- Cartridge candidates use a stricter clean subset that excludes `estimated` closes and close reasons containing `transcript`.
- `runtime_paper_close` means a profitable close came from a runtime log initialized against `api-fxpractice.oanda.com`, but the matching OCO receipt was not present in that same scanned file.

## Scan Stats

- Generated UTC: `2026-06-07T12:29:07.343494+00:00`
- Legacy root: `/home/rfing/READ_ONLY_LEGACY`
- Files scanned: `224`
- Lines scanned: `12341503`
- JSON records scanned: `9306144`
- Close events seen: `9172`
- Positive close events seen: `1755`
- Positive close events outside window: `1290`
- Unique profitable outside-window trades: `87`
- High-confidence practice receipts: `74`
- Clean high-confidence receipts for cartridge mining: `59`
- Runtime paper closes: `1`

## Clean Cartridge Evidence

| Close ET | Pair | P&L | Strategy | Workflow | Session | Detectors | Reason | Source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| 2026-04-09T12:24 | EUR_USD | 135.19 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-09T12:32 | USD_CHF | 166.65 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-09T20:21 | AUD_USD | 213.49 | Trend Continuation | unknown | rollover_17_00 | trap_reversal;rsi_extreme | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-12T22:17 | EUR_USD | 17.50 | Trend Continuation | unknown | rollover_17_00 | fvg | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-12T22:17 | USD_CAD | 19.64 | reversal | unknown | rollover_17_00 | trap_reversal;rsi_extreme | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T09:28 | USD_CHF | 18.18 | legacy | unknown | post_london_overlap_09_1130 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:12 | USD_CHF | 89.46 | legacy | momentum | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:24 | AUD_USD | 18.00 | momentum | unknown | post_london_overlap_09_1130 | momentum_sma;ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:40 | USD_CHF | 82.04 | momentum | momentum | post_london_overlap_09_1130 | momentum_sma;ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:47 | EUR_USD | 66.50 | momentum | momentum | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-13T18:27 | GBP_USD | 19.75 | momentum | momentum | rollover_17_00 | momentum_sma;ema_stack;fibonacci | session_router_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T18:27 | EUR_USD | 21.50 | momentum | momentum | rollover_17_00 | momentum_sma;ema_stack;fibonacci | session_router_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-15T14:50 | AUD_USD | 75.00 | momentum | momentum | ny_afternoon_close_14_17 | momentum_sma;ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:14 | USD_CAD | 31.07 | momentum | momentum | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:34 | USD_JPY | 28.60 | momentum | momentum | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:34 | EUR_USD | 20.25 | momentum | momentum | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:34 | USD_CHF | 11.36 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T13:14 | USD_JPY | 6.53 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T13:59 | GBP_USD | 6.00 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T14:37 | USD_CAD | 10.48 | momentum | unknown | ny_afternoon_close_14_17 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T23:58 | USD_CAD | 8.49 | momentum | unknown | rollover_17_00 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-17T01:04 | USD_JPY | 6.21 | momentum | unknown | tokyo_late_pre_london_00_03 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-17T02:44 | GBP_USD | 5.25 | momentum | unknown | tokyo_late_pre_london_00_03 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-20T09:29 | USD_CHF | 76.17 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-20T14:40 | AUD_USD | 75.75 | momentum | continuation | ny_afternoon_close_14_17 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-21T09:48 | NZD_USD | 22.50 | momentum | unknown | post_london_overlap_09_1130 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-21T15:42 | USD_JPY | 75.40 | momentum | unknown | ny_afternoon_close_14_17 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-21T16:15 | USD_CHF | 14.26 | scalp | scalp | ny_afternoon_close_14_17 | fvg;aggressive_short_ob | wick_scratch | WSL_LEGACY_READ_ONLY |
| 2026-04-21T16:30 | USD_CHF | 24.73 | scalp | scalp | ny_afternoon_close_14_17 | fvg;aggressive_short_ob | wick_scratch | WSL_LEGACY_READ_ONLY |
| 2026-04-23T13:46 | USD_CHF | 78.27 | momentum | continuation | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | RBOTZILLA_VERSION_AUDIT_LAB |
| 2026-04-29T09:14 | NZD_USD | 75.00 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-29T09:48 | NZD_USD | 81.12 | momentum | continuation | post_london_overlap_09_1130 | momentum_sma;ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-29T14:37 | EUR_USD | 82.84 | momentum | continuation | ny_afternoon_close_14_17 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-30T10:12 | USD_CHF | 77.12 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-30T10:19 | AUD_USD | 81.00 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-30T14:35 | USD_CHF | 82.34 | momentum | continuation | ny_afternoon_close_14_17 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-05-06T09:45 | EUR_USD | 6.00 | reversal | liquidity_trap_reversal | post_london_overlap_09_1130 | trap_reversal | wick_scratch | RBOT_VERSIONED_REPOS |
| 2026-05-06T11:30 | USD_CAD | 0.18 | reversal | liquidity_trap_reversal | midday_new_york_1130_14 | trap_reversal | wick_scratch | RBOT_VERSIONED_REPOS |
| 2026-05-08T02:07 | USD_CHF | 79.42 | reversal | unknown | tokyo_late_pre_london_00_03 | trap_reversal | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-05-08T16:22 | EUR_USD | 75.75 | momentum | continuation | ny_afternoon_close_14_17 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |

## High-Confidence Winners

This full set is retained for audit traceability. Cartridge candidates below use only the clean subset above.

| Close ET | Pair | P&L | Strategy | Workflow | Session | Detectors | Reason | Source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| 2026-04-09T12:24 | EUR_USD | 135.19 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-09T12:32 | USD_CHF | 166.65 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-09T20:21 | AUD_USD | 213.49 | Trend Continuation | unknown | rollover_17_00 | trap_reversal;rsi_extreme | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-12T22:17 | EUR_USD | 17.50 | Trend Continuation | unknown | rollover_17_00 | fvg | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-12T22:17 | USD_CAD | 19.64 | reversal | unknown | rollover_17_00 | trap_reversal;rsi_extreme | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T09:28 | USD_CHF | 18.18 | legacy | unknown | post_london_overlap_09_1130 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:05 | USD_CHF | 3.60 | momentum | unknown | post_london_overlap_09_1130 | ema_stack;fibonacci | estimated | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:12 | USD_CHF | 89.46 | legacy | momentum | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:24 | AUD_USD | 18.00 | momentum | unknown | post_london_overlap_09_1130 | momentum_sma;ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:40 | USD_CHF | 82.04 | momentum | momentum | post_london_overlap_09_1130 | momentum_sma;ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-13T10:47 | EUR_USD | 66.50 | momentum | momentum | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-13T12:37 | NZD_USD | 41.25 | momentum | momentum | midday_new_york_1130_14 | momentum_sma;ema_stack;fibonacci | transcript_scratch | WSL_LEGACY_READ_ONLY |
| 2026-04-13T14:11 | EUR_USD | 1.00 | momentum | momentum | ny_afternoon_close_14_17 | momentum_sma;ema_stack;fibonacci | transcript_scratch | WSL_LEGACY_READ_ONLY |
| 2026-04-13T18:27 | GBP_USD | 19.75 | momentum | momentum | rollover_17_00 | momentum_sma;ema_stack;fibonacci | session_router_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-13T18:27 | EUR_USD | 21.50 | momentum | momentum | rollover_17_00 | momentum_sma;ema_stack;fibonacci | session_router_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-15T14:50 | AUD_USD | 75.00 | momentum | momentum | ny_afternoon_close_14_17 | momentum_sma;ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:14 | USD_CAD | 31.07 | momentum | momentum | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:34 | USD_JPY | 28.60 | momentum | momentum | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:34 | EUR_USD | 20.25 | momentum | momentum | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-16T12:34 | USD_CHF | 11.36 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T13:14 | USD_JPY | 6.53 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T13:59 | GBP_USD | 6.00 | momentum | unknown | midday_new_york_1130_14 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T14:37 | USD_CAD | 10.48 | momentum | unknown | ny_afternoon_close_14_17 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-16T23:58 | USD_CAD | 8.49 | momentum | unknown | rollover_17_00 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-17T01:04 | USD_JPY | 6.21 | momentum | unknown | tokyo_late_pre_london_00_03 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-17T02:44 | GBP_USD | 5.25 | momentum | unknown | tokyo_late_pre_london_00_03 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-20T09:29 | USD_CHF | 76.17 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-20T14:40 | AUD_USD | 75.75 | momentum | continuation | ny_afternoon_close_14_17 | ema_stack;fibonacci | profit_harvest_close | WSL_LEGACY_READ_ONLY |
| 2026-04-21T09:48 | NZD_USD | 22.50 | momentum | unknown | post_london_overlap_09_1130 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-21T15:42 | USD_JPY | 75.40 | momentum | unknown | ny_afternoon_close_14_17 | ema_stack;fibonacci | mid_exit | WSL_LEGACY_READ_ONLY |
| 2026-04-21T16:15 | USD_CHF | 14.26 | scalp | scalp | ny_afternoon_close_14_17 | fvg;aggressive_short_ob | wick_scratch | WSL_LEGACY_READ_ONLY |
| 2026-04-21T16:30 | USD_CHF | 24.73 | scalp | scalp | ny_afternoon_close_14_17 | fvg;aggressive_short_ob | wick_scratch | WSL_LEGACY_READ_ONLY |
| 2026-04-23T13:46 | USD_CHF | 78.27 | momentum | continuation | midday_new_york_1130_14 | ema_stack;fibonacci | profit_harvest_close | RBOTZILLA_VERSION_AUDIT_LAB |
| 2026-04-29T09:14 | NZD_USD | 75.00 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-29T09:48 | NZD_USD | 81.12 | momentum | continuation | post_london_overlap_09_1130 | momentum_sma;ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-29T14:37 | EUR_USD | 82.84 | momentum | continuation | ny_afternoon_close_14_17 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-30T10:12 | USD_CHF | 77.12 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-30T10:19 | AUD_USD | 81.00 | momentum | continuation | post_london_overlap_09_1130 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-04-30T14:35 | USD_CHF | 82.34 | momentum | continuation | ny_afternoon_close_14_17 | ema_stack;fibonacci | profit_harvest_close | backups |
| 2026-05-04T11:22 | AUD_USD | 16.95 | smart_money | unknown | post_london_overlap_09_1130 | trap_reversal | estimated | backups |

## Session Grouping

| Bucket | Strategy | Pair | Wins | P&L Sum | Avg P&L | Best P&L |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| midday_new_york_1130_14 | momentum | USD_CHF | 3 | 256.28 | 85.43 | 166.65 |
| post_london_overlap_09_1130 | momentum | USD_CHF | 3 | 235.34 | 78.45 | 82.04 |
| post_london_overlap_09_1130 | momentum | NZD_USD | 3 | 178.62 | 59.54 | 81.12 |
| post_london_overlap_09_1130 | momentum | EUR_USD | 3 | 151.25 | 50.42 | 78.00 |
| post_london_overlap_09_1130 | momentum | AUD_USD | 3 | 113.50 | 37.83 | 81.00 |
| rollover_17_00 | momentum | USD_CAD | 3 | 79.18 | 26.39 | 40.60 |
| post_london_overlap_09_1130 | momentum | USD_CAD | 3 | 38.40 | 12.80 | 22.71 |
| ny_afternoon_close_14_17 | momentum | EUR_USD | 2 | 158.59 | 79.30 | 82.84 |
| midday_new_york_1130_14 | momentum | EUR_USD | 2 | 155.44 | 77.72 | 135.19 |
| ny_afternoon_close_14_17 | momentum | AUD_USD | 2 | 150.75 | 75.38 | 75.75 |
| post_london_overlap_09_1130 | legacy | USD_CHF | 2 | 107.64 | 53.82 | 89.46 |
| rollover_17_00 | momentum | EUR_USD | 2 | 56.50 | 28.25 | 35.00 |
| rollover_17_00 | momentum | GBP_USD | 2 | 50.25 | 25.12 | 30.50 |
| ny_afternoon_close_14_17 | scalp | USD_CHF | 2 | 38.99 | 19.49 | 24.73 |
| midday_new_york_1130_14 | momentum | USD_JPY | 2 | 35.13 | 17.56 | 28.60 |
| tokyo_late_pre_london_00_03 | momentum | USD_JPY | 2 | 26.65 | 13.33 | 20.44 |
| midday_new_york_1130_14 | momentum | GBP_USD | 2 | 19.77 | 9.88 | 13.77 |
| rollover_17_00 | Trend Continuation | AUD_USD | 1 | 213.49 | 213.49 | 213.49 |
| ny_afternoon_close_14_17 | momentum | USD_CHF | 1 | 82.34 | 82.34 | 82.34 |
| tokyo_late_pre_london_00_03 | reversal | USD_CHF | 1 | 79.42 | 79.42 | 79.42 |
| ny_afternoon_close_14_17 | momentum | USD_JPY | 1 | 75.40 | 75.40 | 75.40 |
| post_london_overlap_09_1130 | momentum | GBP_USD | 1 | 55.50 | 55.50 | 55.50 |
| rollover_17_00 | legacy | GBP_USD | 1 | 51.00 | 51.00 | 51.00 |
| midday_new_york_1130_14 | momentum | USD_CAD | 1 | 31.07 | 31.07 | 31.07 |
| ny_afternoon_close_14_17 | momentum | GBP_USD | 1 | 25.00 | 25.00 | 25.00 |
| rollover_17_00 | reversal | USD_CAD | 1 | 19.64 | 19.64 | 19.64 |
| rollover_17_00 | Trend Continuation | EUR_USD | 1 | 17.50 | 17.50 | 17.50 |
| ny_afternoon_close_14_17 | momentum | USD_CAD | 1 | 10.48 | 10.48 | 10.48 |
| midday_new_york_1130_14 | scalp | GBP_USD | 1 | 8.40 | 8.40 | 8.40 |
| rollover_17_00 | scalp | GBP_USD | 1 | 7.25 | 7.25 | 7.25 |

## Candidate Cartridges

| Candidate | Evidence | Pairs | P&L Sum | Activation Stance |
| --- | ---: | --- | ---: | --- |
| post_london_overlap_09_1130_momentum | 16 wins | AUD_USD, EUR_USD, GBP_USD, NZD_USD, USD_CAD, USD_CHF | 772.61 | candidate-only; build replay fixture, then paper probation |
| midday_new_york_1130_14_momentum | 10 wins | EUR_USD, GBP_USD, USD_CAD, USD_CHF, USD_JPY | 497.68 | candidate-only; build replay fixture, then paper probation |
| ny_afternoon_close_14_17_momentum | 8 wins | AUD_USD, EUR_USD, GBP_USD, USD_CAD, USD_CHF, USD_JPY | 502.55 | candidate-only; build replay fixture, then paper probation |
| rollover_17_00_momentum | 7 wins | EUR_USD, GBP_USD, USD_CAD | 185.93 | candidate-only; build replay fixture, then paper probation |
| tokyo_late_pre_london_00_03_momentum | 3 wins | GBP_USD, USD_JPY | 31.90 | candidate-only; build replay fixture, then paper probation |
| rollover_17_00_scalp | 3 wins | EUR_USD, GBP_USD, USD_JPY | 11.77 | candidate-only; build replay fixture, then paper probation |
| rollover_17_00_trend_continuation | 2 wins | AUD_USD, EUR_USD | 230.99 | candidate-only; build replay fixture, then paper probation |
| post_london_overlap_09_1130_legacy | 2 wins | USD_CHF | 107.64 | candidate-only; build replay fixture, then paper probation |
| ny_afternoon_close_14_17_scalp | 2 wins | USD_CHF | 38.99 | candidate-only; build replay fixture, then paper probation |

## Runtime Paper Candidates

These are useful leads, but they need manual review or broker-history confirmation before they become cartridges.

| Close ET | Pair | P&L | Strategy | Workflow | Session | Detectors | Reason | Source |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| 2026-04-15T10:29 | AUD_USD | 141.75 | legacy | unknown | post_london_overlap_09_1130 | unknown | mid_exit | WSL_LEGACY_READ_ONLY |

## Unlinked Candidates

These are not deployable evidence yet because the matching practice OCO receipt was not found in the scanned source.

- Count: `12`

## Output Files

- JSON: `/home/rfing/ODA_TRABOT/analysis/live_paper_outside_window_audit/outside_window_profitable_trades.json`
- CSV: `/home/rfing/ODA_TRABOT/analysis/live_paper_outside_window_audit/outside_window_profitable_trades.csv`
- Stats: `/home/rfing/ODA_TRABOT/analysis/live_paper_outside_window_audit/scan_stats.json`
