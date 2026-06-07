# Outside-Frozen Session Strategy Reassessment

Date: June 7, 2026

## Operator Answer

I reassessed strategies by entry time outside the frozen 3:00 AM-8:30 AM ET momentum cartridge.

The deployable read is not "trade momentum all day."

The clean outside-frozen edge is narrower:

`9:00-11:30 AM ET EMA/Fibonacci momentum continuation`

That is the only outside-frozen session/strategy combination that clearly survives this pass.

## Method

- Used historical OANDA repo logs only.
- Used clean high-confidence closed trade results from the lifecycle audit.
- Grouped by trade open time, not close time.
- Excluded entries opened from 3:00 AM through 8:29 AM ET.
- Folded in protection-failure classifications from the SL/TP/trailing audit.
- Split clean EMA/Fibonacci continuation away from detector-contaminated continuation labels.

## Audit Counts

- Clean trades in frozen 3:00-8:30 AM window: 159
- Clean trades opened outside frozen window: 343
- Clean core EMA/Fibonacci continuation trades outside frozen window: 14

## Session-Level Result

| Session | Trades | Wins | Losses | P&L | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| 8:30-9:00 AM transition | 21 | 4 | 17 | -410.01 | do not trade this whole session bucket |
| 9:00-11:30 AM post-London / NY overlap | 104 | 26 | 78 | -1258.83 | only EMA/Fib continuation survives; all-session bucket is negative if contaminated |
| 11:30 AM-2:00 PM New York midday | 91 | 11 | 80 | -753.48 | do not trade this whole session bucket |
| 2:00-5:00 PM New York afternoon | 65 | 9 | 56 | -652.53 | watch only; tiny positive continuation sample |
| 5:00-9:00 PM rollover / Asia open | 25 | 8 | 17 | -191.72 | do not trade this whole session bucket |
| 9:00 PM-midnight Tokyo | 13 | 0 | 13 | -348.10 | do not trade this whole session bucket |
| midnight-3:00 AM pre-London | 24 | 9 | 15 | -250.46 | do not trade this whole session bucket |

## Strategy Result By Session

| Session | Strategy | Trades | W | L | P&L | PF | Edge Giveback Losses | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 8:30-9:00 AM transition | legacy | 1 | 1 | 0 | 18.18 | inf | 0 | small-sample watch only |
| 8:30-9:00 AM transition | scalp | 5 | 0 | 5 | -37.25 | 0.00 | 0 | do not deploy |
| 8:30-9:00 AM transition | reversal | 3 | 0 | 3 | -43.26 | 0.00 | 0 | do not deploy |
| 8:30-9:00 AM transition | momentum_continuation | 1 | 0 | 1 | -125.00 | 0.00 | 1 | do not deploy |
| 8:30-9:00 AM transition | momentum | 11 | 3 | 8 | -222.67 | 0.07 | 2 | do not deploy |
| 9:00-11:30 AM post-London / NY overlap | momentum_continuation | 9 | 8 | 1 | 506.51 | 6.90 | 1 | build narrow cartridge after detector cleanup |
| 9:00-11:30 AM post-London / NY overlap | legacy | 1 | 1 | 0 | 75.75 | inf | 0 | small-sample watch only |
| 9:00-11:30 AM post-London / NY overlap | scalp | 11 | 0 | 11 | -98.83 | 0.00 | 0 | do not deploy |
| 9:00-11:30 AM post-London / NY overlap | reversal | 30 | 2 | 28 | -544.19 | 0.01 | 2 | do not deploy |
| 9:00-11:30 AM post-London / NY overlap | momentum | 53 | 15 | 38 | -1198.07 | 0.35 | 9 | do not deploy |
| 11:30 AM-2:00 PM New York midday | momentum_continuation | 5 | 3 | 2 | 130.67 | 1.68 | 2 | paper probation only |
| 11:30 AM-2:00 PM New York midday | legacy | 1 | 1 | 0 | 82.34 | inf | 0 | small-sample watch only |
| 11:30 AM-2:00 PM New York midday | scalp | 17 | 1 | 16 | -72.76 | 0.10 | 0 | do not deploy |
| 11:30 AM-2:00 PM New York midday | reversal | 39 | 0 | 39 | -368.72 | 0.00 | 4 | do not deploy |
| 11:30 AM-2:00 PM New York midday | momentum | 29 | 6 | 23 | -525.00 | 0.31 | 4 | do not deploy |
| 2:00-5:00 PM New York afternoon | momentum_continuation | 2 | 2 | 0 | 117.84 | inf | 0 | small-sample watch only |
| 2:00-5:00 PM New York afternoon | legacy | 3 | 1 | 2 | -78.56 | 0.39 | 1 | do not deploy |
| 2:00-5:00 PM New York afternoon | scalp | 23 | 2 | 21 | -128.53 | 0.23 | 0 | do not deploy |
| 2:00-5:00 PM New York afternoon | reversal | 20 | 0 | 20 | -181.71 | 0.00 | 0 | do not deploy |
| 2:00-5:00 PM New York afternoon | momentum | 17 | 4 | 13 | -381.57 | 0.27 | 3 | do not deploy |
| 5:00-9:00 PM rollover / Asia open | legacy | 1 | 1 | 0 | 17.50 | inf | 0 | small-sample watch only |
| 5:00-9:00 PM rollover / Asia open | scalp | 8 | 3 | 5 | -25.46 | 0.32 | 0 | do not deploy |
| 5:00-9:00 PM rollover / Asia open | momentum_continuation | 4 | 1 | 3 | -40.61 | 0.55 | 1 | do not deploy |
| 5:00-9:00 PM rollover / Asia open | reversal | 3 | 1 | 2 | -42.23 | 0.32 | 1 | do not deploy |
| 5:00-9:00 PM rollover / Asia open | momentum | 9 | 2 | 7 | -100.92 | 0.22 | 2 | do not deploy |
| 9:00 PM-midnight Tokyo | scalp | 3 | 0 | 3 | -5.43 | 0.00 | 0 | do not deploy |
| 9:00 PM-midnight Tokyo | momentum | 4 | 0 | 4 | -101.53 | 0.00 | 2 | do not deploy |
| 9:00 PM-midnight Tokyo | momentum_continuation | 1 | 0 | 1 | -115.50 | 0.00 | 0 | do not deploy |
| 9:00 PM-midnight Tokyo | reversal | 5 | 0 | 5 | -125.64 | 0.00 | 4 | do not deploy |
| midnight-3:00 AM pre-London | trend | 1 | 0 | 1 | -4.00 | 0.00 | 0 | do not deploy |
| midnight-3:00 AM pre-London | scalp | 4 | 0 | 4 | -9.40 | 0.00 | 0 | do not deploy |
| midnight-3:00 AM pre-London | reversal | 8 | 3 | 5 | -24.60 | 0.85 | 4 | do not deploy |
| midnight-3:00 AM pre-London | momentum | 9 | 5 | 4 | -74.68 | 0.49 | 1 | do not deploy |
| midnight-3:00 AM pre-London | momentum_continuation | 2 | 1 | 1 | -137.77 | 0.20 | 1 | do not deploy |

## Clean EMA/Fibonacci Continuation Only

This is the cleaner version of the edge. It requires `ema_stack` and `fibonacci`, and it avoids treating reversal/trap labels as continuation just because an old log named them that way.

| Session | Strategy | Trades | W | L | P&L | PF | Edge Giveback Losses | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 9:00-11:30 AM post-London / NY overlap | momentum_continuation | 7 | 7 | 0 | 562.31 | inf | 0 | build narrow cartridge after detector cleanup |
| 11:30 AM-2:00 PM New York midday | momentum_continuation | 4 | 2 | 2 | -82.83 | 0.57 | 2 | do not deploy |
| 2:00-5:00 PM New York afternoon | momentum_continuation | 2 | 2 | 0 | 117.84 | inf | 0 | small-sample watch only |
| midnight-3:00 AM pre-London | momentum_continuation | 1 | 1 | 0 | 35.25 | inf | 0 | small-sample watch only |

## Reassessment Decision

### Build First

`post_9am_ema_fib_momentum_continuation`

- Entry window: 9:00-11:30 AM ET
- Clean core sample: 7 wins, 0 losses
- P&L: about +$562.31
- Pairs: AUD_USD, EUR_USD, NZD_USD, USD_CAD, USD_CHF
- Required detectors: `ema_stack` + `fibonacci`
- Stronger when `momentum_sma` is also present
- Required workflow: `continuation`
- Exclude `trap_reversal`, `rsi_extreme`, and scalp detectors from this cartridge
- Practice only

### Watch But Do Not Deploy Yet

`ny_afternoon_ema_fib_continuation`

- Entry window: 2:00-5:00 PM ET
- Clean core sample: 2 wins, 0 losses
- P&L: about +$117.84
- Pair evidence: EUR_USD only
- Too small to activate as a separate cartridge yet

### Do Not Deploy

- 8:30-9:00 AM transition: negative and unstable.
- 11:30 AM-2:00 PM midday: not cleared once detector contamination is removed.
- 5:00-9:00 PM rollover / Asia open: negative.
- 9:00 PM-midnight Tokyo: 0 wins in the clean outside-frozen set.
- midnight-3:00 AM pre-London: negative overall.
- scalp: negative in every outside-frozen bucket.
- reversal: negative in every outside-frozen bucket.
- generic momentum: negative outside frozen because it was weakly gated and contaminated.

## Protection Read

| Protection Class | Count | Meaning |
| --- | ---: | --- |
| entry_failed_before_secondary_could_help | 159 | Entry/setup failed before protection could help. |
| edge_present_but_no_trailing_or_lock | 45 | Trade went green, then red, with no logged lock/trailing. |
| small_pip_green_not_enough_for_lock | 41 | Small pip movement, not enough to blame trailing. |
| small_green_not_enough_for_lock | 29 | Small positive P&L, not enough to blame trailing. |
| loss_no_trailing_manager_samples | 2 | SL/TP existed, but manager did not log trailing samples. |

## Core 9:00-11:30 Evidence Trades

| Open ET | Close ET | Pair | P&L | Detectors | Protection Class |
| --- | --- | --- | ---: | --- | --- |
| 2026-04-29T09:15 | 2026-04-29T09:48 | NZD_USD | 81.12 | momentum_sma;ema_stack;fibonacci | winner_static_sl_tp_only |
| 2026-04-30T09:39 | 2026-04-30T10:12 | USD_CHF | 77.12 | ema_stack;fibonacci | winner_static_sl_tp_only |
| 2026-04-30T09:50 | 2026-04-30T10:19 | AUD_USD | 81.00 | ema_stack;fibonacci | winner_static_sl_tp_only |
| 2026-05-08T10:45 | 2026-05-08T16:22 | EUR_USD | 75.75 | ema_stack;fibonacci | winner_with_secondary_protection |
| 2026-05-19T10:05 | 2026-05-19T10:21 | EUR_USD | 78.00 | ema_stack;fibonacci | winner_static_sl_tp_only |
| 2026-06-03T11:15 | 2026-06-03T17:00 | USD_CAD | 40.60 | ema_stack;fibonacci | winner_with_secondary_protection |
| 2026-06-03T11:15 | 2026-06-04T03:37 | USD_CAD | 128.71 | ema_stack;fibonacci | winner_with_secondary_protection |

## Final Rule

The frozen 3:00-8:30 AM cartridge stays untouched.

The only new outside-frozen cartridge that earns construction is a separate, narrow practice-only cartridge:

`post_9am_ema_fib_momentum_continuation`

Anything broader is contamination.

## Output Files

- Session summary JSON: `/home/rfing/ODA_TRABOT/analysis/session_strategy_reassessment/session_strategy_summary.json`
- Core continuation JSON: `/home/rfing/ODA_TRABOT/analysis/session_strategy_reassessment/core_ema_fib_continuation_summary.json`
- Outside-frozen trade CSV: `/home/rfing/ODA_TRABOT/analysis/session_strategy_reassessment/outside_frozen_clean_trades.csv`
- Technical report: `/home/rfing/ODA_TRABOT/analysis/session_strategy_reassessment/outside_frozen_session_strategy_reassessment.md`
