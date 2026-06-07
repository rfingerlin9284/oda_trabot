# Strategy Lifecycle Audit - Plain English

Date: June 7, 2026

## Operator Answer

This audit looked at closed historical OANDA practice trades from repo logs only, then counted wins and losses by strategy.

The goal was to find whether there are more strategies than the frozen morning momentum cartridge, and to inspect losses to see whether the strategy itself failed or whether workflow, timing, confirmation, or exit management caused the damage.

## Proof Standard

Primary evidence used for strategy mining:

- closed OANDA trade logs from historical repos
- linked to a matching PRACTICE OCO order when available
- `live_api=true`
- `visible_in_oanda=true`
- not Coinbase
- not TurboScribe transcript claims
- not replay-only result files
- not `estimated` close reasons
- not close reasons containing `transcript`

## Audit Size

- Unique log files scanned: 224
- Data scanned: about 3.22 GB
- Lines scanned: 12,341,503
- JSON records scanned: 9,306,144
- Close events seen: 9,172
- All closed trade results found: 656
- High-confidence linked practice results: 641
- Clean high-confidence results used for strategy mining: 502
- Clean wins: 107
- Clean losses: 395
- Clean breakeven: 0

## Direct Decision

More strategy labels were found in the logs, but most did not hold up once losses were counted.

The only clearly positive strategy family in this full lifecycle pass was `momentum_continuation`.

Important nuance: generic `momentum` across all logged conditions was negative. That does not cancel the frozen April 14 morning cartridge. It means uncontrolled or weakly gated momentum entries were contaminated. The edge appears when momentum is constrained by the right session, continuation workflow, detector stack, and risk/exit behavior.

## Wins And Losses Per Strategy

| Strategy | Trades | Wins | Losses | Win Rate | P&L | Profit Factor | Main Loss Diagnosis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| momentum_continuation | 44 | 33 | 11 | 75.0% | 1580.31 | 2.80 | edge_present_exit_or_workflow_gave_back |
| trend | 2 | 0 | 2 | 0.0% | -34.00 | 0.00 | quality_gate_too_weak |
| legacy | 19 | 9 | 10 | 47.4% | -181.84 | 0.71 | edge_present_exit_or_workflow_gave_back |
| scalp | 81 | 7 | 74 | 8.6% | -473.70 | 0.16 | scratch_or_noise_exit_without_followthrough |
| reversal | 160 | 7 | 153 | 4.4% | -1982.44 | 0.13 | scratch_or_noise_exit_without_followthrough |
| momentum | 196 | 51 | 145 | 26.0% | -4539.33 | 0.27 | quality_gate_too_weak |

## Loss Diagnosis By Strategy

| Strategy | Loss Causes | Plain-English Read |
| --- | --- | --- |
| momentum_continuation | edge_present_exit_or_workflow_gave_back: 7, quality_gate_too_weak: 2, small_edge_then_noise_loss: 2 | Losses mostly show fixable exit/workflow giveback, not a dead strategy. |
| trend | quality_gate_too_weak: 1, edge_present_exit_or_workflow_gave_back: 1 | The strategy was contaminated by weak confidence/vote gating. |
| legacy | edge_present_exit_or_workflow_gave_back: 7, quality_gate_too_weak: 2, small_edge_then_noise_loss: 1 | The entry sometimes had edge, but trade management failed to keep it. |
| scalp | scratch_or_noise_exit_without_followthrough: 66, small_edge_then_noise_loss: 4, scalp_no_followthrough: 4 | The setup usually did not travel; this is not a deployable standalone edge. |
| reversal | scratch_or_noise_exit_without_followthrough: 117, edge_present_exit_or_workflow_gave_back: 19, small_edge_then_noise_loss: 12, reversal_missing_trend_confirmation: 5 | The setup usually did not travel; this is not a deployable standalone edge. |
| momentum | quality_gate_too_weak: 54, edge_present_exit_or_workflow_gave_back: 44, small_edge_then_noise_loss: 25, scratch_or_noise_exit_without_followthrough: 21, strategy_no_logged_edge_on_trade: 1 | The strategy was contaminated by weak confidence/vote gating. |

## Loss Diagnosis Summary

| Diagnosis | Count | P&L Impact | Meaning |
| --- | ---: | ---: | --- |
| scratch_or_noise_exit_without_followthrough | 204 | -1771.35 | Wick/scratch behavior; setup did not travel cleanly. |
| edge_present_exit_or_workflow_gave_back | 78 | -4318.64 | Trade had favorable excursion, then closed red. Review exits, lock, giveback, trailing, and workflow handling. |
| quality_gate_too_weak | 59 | -2864.73 | Confidence/votes were too thin. |
| small_edge_then_noise_loss | 44 | -1195.22 | Trade moved slightly positive but not enough to prove strong edge. |
| reversal_missing_trend_confirmation | 5 | -330.89 | Reversal lacked stronger confirmation stack. |
| scalp_no_followthrough | 4 | -29.80 | Scalp did not travel enough. |
| strategy_no_logged_edge_on_trade | 1 | -58.15 | No logged favorable excursion before loss. |

## Strategy Read

- `momentum_continuation`: 44 clean trades, 33 wins, 11 losses, P&L 1580.31, profit factor 2.8043. Candidate family. Keep auditing and replay/paper-probate before activation.
- `trend`: 2 clean trades, 0 wins, 2 losses, P&L -34.00, profit factor 0.0. Do not deploy as its own cartridge from this evidence.
- `legacy`: 19 clean trades, 9 wins, 10 losses, P&L -181.84, profit factor 0.7075. Do not deploy as its own cartridge from this evidence.
- `scalp`: 81 clean trades, 7 wins, 74 losses, P&L -473.70, profit factor 0.1638. Do not deploy as its own cartridge from this evidence.
- `reversal`: 160 clean trades, 7 wins, 153 losses, P&L -1982.44, profit factor 0.1314. Do not deploy as its own cartridge from this evidence.
- `momentum`: 196 clean trades, 51 wins, 145 losses, P&L -4539.33, profit factor 0.2665. Do not deploy as its own cartridge from this evidence.

## What The Loss Screen Means

A loss was not automatically treated as proof that the strategy has no edge.

If the trade first reached positive P&L and then closed red, the audit marks that as `edge_present_exit_or_workflow_gave_back`. That means the entry may have had edge, but the workflow, exit, stop movement, green-lock behavior, or management timing failed to keep it.

If the trade never showed positive tracked P&L, the audit marks that closer to `strategy_no_logged_edge_on_trade`, `quality_gate_too_weak`, `scalp_no_followthrough`, or another setup-quality problem.

## Biggest Losses To Review By Hand

| Close ET | Strategy | Pair | P&L | Max Tracked P&L | Diagnosis | Detail |
| --- | --- | --- | ---: | ---: | --- | --- |
| 2026-04-09T11:33 | reversal | NZD_USD | -225.00 | 94.64 | edge_present_exit_or_workflow_gave_back | Trade reached about +$94.64 before closing at $-225.00; about $319.64 was given back. |
| 2026-04-10T03:59 | reversal | AUD_USD | -177.78 | 17.46 | edge_present_exit_or_workflow_gave_back | Trade reached about +$17.46 before closing at $-177.78; about $195.24 was given back. |
| 2026-04-10T16:57 | momentum | EUR_USD | -173.15 | -14.81 | quality_gate_too_weak | Signal quality was thin: confidence=0.78, votes=0. |
| 2026-04-10T02:56 | momentum_continuation | AUD_USD | -173.02 | 165.08 | edge_present_exit_or_workflow_gave_back | Trade reached about +$165.08 before closing at $-173.02; about $338.10 was given back. |
| 2026-04-09T10:48 | momentum | USD_CHF | -161.44 | -21.64 | quality_gate_too_weak | Signal quality was thin: confidence=0.78, votes=0. |
| 2026-04-10T09:22 | reversal | USD_CHF | -154.45 | -20.40 | reversal_missing_trend_confirmation | Reversal trade lacked the stronger ema_stack/fibonacci confirmation that appeared often in the better momentum winners. |
| 2026-04-10T09:24 | momentum_continuation | EUR_USD | -125.00 | 31.48 | edge_present_exit_or_workflow_gave_back | Trade reached about +$31.48 before closing at $-125.00; about $156.48 was given back. |
| 2026-05-20T10:16 | momentum | USD_CHF | -120.89 | -13.41 | quality_gate_too_weak | Signal quality was thin: confidence=0.89, votes=0. |
| 2026-04-10T03:31 | momentum_continuation | USD_CAD | -115.50 | -12.36 | quality_gate_too_weak | Signal quality was thin: confidence=0.83, votes=0. |
| 2026-04-13T07:55 | momentum | GBP_USD | -103.50 | -0.75 | quality_gate_too_weak | Signal quality was thin: confidence=0.88, votes=0. |
| 2026-04-10T02:20 | momentum | EUR_USD | -100.93 | 0.93 | small_edge_then_noise_loss | Trade had only a small favorable excursion of about +$0.93; edge was not strong enough before the loss. |
| 2026-04-09T14:14 | momentum_continuation | EUR_USD | -100.00 | 81.48 | edge_present_exit_or_workflow_gave_back | Trade reached about +$81.48 before closing at $-100.00; about $181.48 was given back. |
| 2026-04-09T10:33 | momentum | GBP_USD | -98.44 | -5.47 | quality_gate_too_weak | Signal quality was thin: confidence=0.88, votes=0. |
| 2026-04-30T07:08 | momentum | EUR_USD | -97.28 | 2.28 | small_edge_then_noise_loss | Trade had only a small favorable excursion of about +$2.28; edge was not strong enough before the loss. |
| 2026-04-27T09:58 | momentum | EUR_USD | -96.75 | 39.00 | edge_present_exit_or_workflow_gave_back | Trade reached about +$39.00 before closing at $-96.75; about $135.75 was given back. |
| 2026-04-17T11:03 | momentum | GBP_USD | -95.76 | 30.40 | edge_present_exit_or_workflow_gave_back | Trade reached about +$30.40 before closing at $-95.76; about $126.16 was given back. |
| 2026-04-14T11:50 | momentum | USD_CHF | -95.07 | 61.57 | edge_present_exit_or_workflow_gave_back | Trade reached about +$61.57 before closing at $-95.07; about $156.63 was given back. |
| 2026-04-23T13:53 | momentum | EUR_USD | -94.50 | -12.75 | quality_gate_too_weak | Signal quality was thin: confidence=0.89, votes=0. |
| 2026-04-30T07:57 | momentum | EUR_USD | -94.50 | 18.00 | edge_present_exit_or_workflow_gave_back | Trade reached about +$18.00 before closing at $-94.50; about $112.50 was given back. |
| 2026-05-21T04:07 | momentum | AUD_USD | -94.50 | 18.75 | edge_present_exit_or_workflow_gave_back | Trade reached about +$18.75 before closing at $-94.50; about $113.25 was given back. |
| 2026-05-01T09:46 | momentum | USD_CHF | -94.43 | -18.12 | quality_gate_too_weak | Signal quality was thin: confidence=0.91, votes=0. |
| 2026-04-29T17:30 | momentum | USD_CHF | -92.96 | 0.00 | quality_gate_too_weak | Signal quality was thin: confidence=0.79, votes=0. |
| 2026-04-30T10:37 | momentum | AUD_USD | -92.04 | 15.60 | edge_present_exit_or_workflow_gave_back | Trade reached about +$15.60 before closing at $-92.04; about $107.64 was given back. |
| 2026-04-09T20:01 | momentum_continuation | USD_CAD | -91.60 | 20.90 | edge_present_exit_or_workflow_gave_back | Trade reached about +$20.90 before closing at $-91.60; about $112.49 was given back. |
| 2026-05-07T07:08 | momentum | GBP_USD | -86.36 | -11.56 | quality_gate_too_weak | Signal quality was thin: confidence=0.80, votes=0. |
| 2026-04-10T09:29 | momentum_continuation | USD_CAD | -85.89 | 53.25 | edge_present_exit_or_workflow_gave_back | Trade reached about +$53.25 before closing at $-85.89; about $139.14 was given back. |
| 2026-05-07T10:05 | momentum | NZD_USD | -85.09 | 0.67 | small_edge_then_noise_loss | Trade had only a small favorable excursion of about +$0.67; edge was not strong enough before the loss. |
| 2026-04-15T05:11 | momentum | AUD_USD | -84.00 | 15.00 | edge_present_exit_or_workflow_gave_back | Trade reached about +$15.00 before closing at $-84.00; about $99.00 was given back. |
| 2026-04-30T09:34 | momentum | USD_CHF | -83.61 | 30.33 | edge_present_exit_or_workflow_gave_back | Trade reached about +$30.33 before closing at $-83.61; about $113.94 was given back. |
| 2026-04-15T09:30 | legacy | USD_CHF | -82.72 | 27.18 | edge_present_exit_or_workflow_gave_back | Trade reached about +$27.18 before closing at $-82.72; about $109.90 was given back. |

## Best Wins By Strategy

| Strategy | Close ET | Pair | P&L | Detectors | Workflow |
| --- | --- | --- | ---: | --- | --- |
| momentum_continuation | 2026-04-09T20:21 | AUD_USD | 213.49 | trap_reversal;rsi_extreme | unknown |
| momentum_continuation | 2026-04-10T08:37 | USD_CHF | 162.90 | ema_stack;fibonacci | unknown |
| momentum_continuation | 2026-06-04T03:37 | USD_CAD | 128.71 | ema_stack;fibonacci | continuation |
| momentum_continuation | 2026-05-01T04:19 | USD_JPY | 91.16 | ema_stack;fibonacci | continuation |
| momentum_continuation | 2026-04-14T08:30 | GBP_USD | 85.50 | momentum_sma;ema_stack;fibonacci | continuation |
| momentum | 2026-04-09T12:32 | USD_CHF | 166.65 | ema_stack;fibonacci | unknown |
| momentum | 2026-04-09T12:24 | EUR_USD | 135.19 | ema_stack;fibonacci | unknown |
| momentum | 2026-04-13T10:12 | USD_CHF | 89.46 | ema_stack;fibonacci | momentum |
| momentum | 2026-04-13T10:40 | USD_CHF | 82.04 | momentum_sma;ema_stack;fibonacci | momentum |
| momentum | 2026-04-21T15:42 | USD_JPY | 75.40 | ema_stack;fibonacci | unknown |
| legacy | 2026-04-30T14:35 | USD_CHF | 82.34 | ema_stack;fibonacci | continuation |
| legacy | 2026-05-01T08:18 | EUR_USD | 77.00 | ema_stack;fibonacci | unknown |
| legacy | 2026-04-20T14:40 | AUD_USD | 75.75 | ema_stack;fibonacci | continuation |
| legacy | 2026-04-30T07:00 | GBP_USD | 60.00 | momentum_sma;ema_stack;fibonacci | unknown |
| legacy | 2026-05-14T19:29 | GBP_USD | 51.00 | momentum_sma;ema_stack;fibonacci | momentum |
| reversal | 2026-04-10T06:26 | NZD_USD | 133.93 | trap_reversal | unknown |
| reversal | 2026-05-08T02:07 | USD_CHF | 79.42 | trap_reversal | unknown |
| reversal | 2026-04-09T05:19 | EUR_USD | 38.62 | trap_reversal | unknown |
| reversal | 2026-04-10T04:09 | EUR_USD | 22.22 | trap_reversal | unknown |
| reversal | 2026-04-12T22:17 | USD_CAD | 19.64 | trap_reversal;rsi_extreme | unknown |
| scalp | 2026-04-20T03:59 | USD_JPY | 33.62 | failed_breakout_fx | unknown |
| scalp | 2026-04-21T16:30 | USD_CHF | 24.73 | fvg;aggressive_short_ob | scalp |
| scalp | 2026-04-21T16:15 | USD_CHF | 14.26 | fvg;aggressive_short_ob | scalp |
| scalp | 2026-06-01T13:30 | GBP_USD | 8.40 | fvg;ema_scalper_200 | scalp |
| scalp | 2026-05-17T20:45 | GBP_USD | 7.25 | ema_scalper_200 | scalp |

## File Outputs

- Full CSV: `/home/rfing/ODA_TRABOT/analysis/strategy_lifecycle_audit/closed_trade_lifecycle_results.csv`
- Full JSON: `/home/rfing/ODA_TRABOT/analysis/strategy_lifecycle_audit/closed_trade_lifecycle_results.json`
- Strategy JSON summary: `/home/rfing/ODA_TRABOT/analysis/strategy_lifecycle_audit/strategy_summary.json`
- Technical markdown: `/home/rfing/ODA_TRABOT/analysis/strategy_lifecycle_audit/strategy_lifecycle_audit.md`
