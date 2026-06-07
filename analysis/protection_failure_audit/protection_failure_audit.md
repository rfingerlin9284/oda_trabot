# Protection Failure Audit - Plain English

Date: June 7, 2026

## Operator Answer

This audit checks whether losses were caused by the strategy being bad, or by secondary protection failures such as missing SL, missing TP, missing trailing stop, no green lock, or trade management failing after the trade had already gone green.

## Direct Finding

- Clean trades checked: 502
- Wins checked: 107
- Losses checked: 395
- Losses where secondary protection likely killed or failed to preserve edge: 80
- Losses with missing logged SL/TP/OCO in the clean high-confidence set: 0

Plain English: in the clean high-confidence OANDA practice receipts, the initial OCO/SL/TP was generally present. The bigger failure was not usually missing initial SL/TP. The bigger failure was that trades went green and then the secondary protection layer did not lock, trail, or hold the gain.

## Broader SL/TP Field Check

This looser check includes lower-confidence/unlinked rows too. It is useful for spotting logging or protection concerns, but it is not the clean cartridge-mining evidence set.

- All closed results checked: 656
- All losses checked: 517
- Rows missing logged stop-loss field: 9
- Rows missing logged take-profit field: 9
- Losing rows missing logged stop-loss field: 2
- Losing rows missing logged take-profit field: 2

Plain English: there were some lower-confidence rows with missing SL/TP fields, but the clean broker-linked OCO rows did not show missing initial SL/TP. The bigger proven failure in the clean evidence is missing or inactive trailing/green-lock after the trade had already gone favorable.

## Losses By Protection Failure Type

| Failure Type | Count | P&L Impact | Plain-English Meaning |
| --- | ---: | ---: | --- |
| entry_failed_before_secondary_could_help | 215 | -3806.62 | Trade never showed favorable excursion; entry/setup failed first. |
| edge_present_but_no_trailing_or_lock | 78 | -4318.64 | Trade went green, then red, with no logged lock/trailing application. |
| small_pip_green_not_enough_for_lock | 56 | -1240.30 | Trade barely moved in pips; not enough edge to blame trailing. |
| small_green_not_enough_for_lock | 44 | -1195.22 | Trade barely went green; not enough edge to blame trailing. |
| loss_no_trailing_manager_samples | 2 | -8.00 | SL/TP existed, but trade manager did not log trailing samples. |

## Protection Failure By Strategy

| Strategy | Losses | Main Protection Failure | Edge-Present Protection Failures | Missing SL/TP/OCO |
| --- | ---: | --- | ---: | ---: |
| reversal | 153 | entry_failed_before_secondary_could_help | 19 | 0 |
| momentum | 145 | edge_present_but_no_trailing_or_lock | 44 | 0 |
| scalp | 74 | entry_failed_before_secondary_could_help | 0 | 0 |
| momentum_continuation | 11 | edge_present_but_no_trailing_or_lock | 7 | 0 |
| legacy | 10 | edge_present_but_no_trailing_or_lock | 7 | 0 |
| trend | 2 | loss_no_trailing_manager_samples | 1 | 0 |

## Biggest Edge-Giveback Losses

| Close ET | Strategy | Pair | Final P&L | Max P&L | Green Lock | Stop Updates | Locked Samples | Failure |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-04-10T02:56 | momentum_continuation | AUD_USD | -173.02 | 165.08 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-09T11:33 | reversal | NZD_USD | -225.00 | 94.64 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-10T03:59 | reversal | AUD_USD | -177.78 | 17.46 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-09T14:14 | momentum_continuation | EUR_USD | -100.00 | 81.48 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-14T11:50 | momentum | USD_CHF | -95.07 | 61.57 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-10T09:24 | momentum_continuation | EUR_USD | -125.00 | 31.48 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-28T11:39 | momentum | USD_CHF | -82.28 | 68.29 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-10T09:29 | momentum_continuation | USD_CAD | -85.89 | 53.25 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-10T12:20 | momentum | EUR_USD | -41.67 | 96.30 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-27T09:58 | momentum | EUR_USD | -96.75 | 39.00 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-30T10:37 | momentum | USD_CHF | -63.78 | 69.65 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-27T12:49 | momentum | USD_CHF | -63.67 | 67.63 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-17T11:03 | momentum | GBP_USD | -95.76 | 30.40 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-14T11:50 | momentum | EUR_USD | -56.00 | 68.32 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-05-25T21:40 | legacy | GBP_USD | -63.00 | 58.50 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-29T15:55 | momentum | NZD_USD | -63.18 | 53.82 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-30T09:34 | momentum | USD_CHF | -83.61 | 30.33 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-05-21T04:07 | momentum | AUD_USD | -94.50 | 18.75 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-24T04:19 | legacy | EUR_USD | -63.00 | 49.50 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-30T07:57 | momentum | EUR_USD | -94.50 | 18.00 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-09T20:01 | momentum_continuation | USD_CAD | -91.60 | 20.90 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-15T09:30 | legacy | USD_CHF | -82.72 | 27.18 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-30T08:09 | legacy | USD_CAD | -69.83 | 39.72 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-30T10:37 | momentum | AUD_USD | -92.04 | 15.60 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-06-02T13:46 | momentum | AUD_USD | -75.00 | 30.00 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-15T05:02 | legacy | USD_CHF | -82.08 | 17.77 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-15T05:11 | momentum | AUD_USD | -84.00 | 15.00 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-27T12:49 | momentum | GBP_USD | -64.50 | 30.00 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-06-04T10:27 | momentum | GBP_USD | -50.50 | 42.50 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-15T06:28 | momentum | AUD_USD | -64.00 | 27.00 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-17T14:52 | momentum | USD_CHF | -81.49 | 8.26 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-10T06:54 | momentum_continuation | USD_JPY | -71.34 | 18.11 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-06-03T06:06 | momentum | GBP_USD | -50.50 | 36.50 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-21T09:32 | momentum | USD_JPY | -47.63 | 37.30 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |
| 2026-04-16T15:10 | momentum | USD_CHF | -66.41 | 17.67 | 0 | 0 | 0 | edge_present_but_no_trailing_or_lock |

## What This Means For The Bot

Do not just ask whether a strategy label won or lost.

For many losses, the better question is: did the trade first show edge, and did the protection layer fail to keep it?

The evidence says yes for a meaningful subset. That means the next cartridge work needs a protection contract, not just entry logic:

- every paper order must have broker-visible OCO
- every open trade must sync broker SL
- every open trade must have manager samples
- once a trade reaches a defined green threshold, it must lock or trail
- if lock/trail fails, the bot must log and flatten or block new entries
- any strategy cartridge without verified SL/TP/TS behavior stays disabled

## Output Files

- CSV: `/home/rfing/ODA_TRABOT/analysis/protection_failure_audit/protection_failure_results.csv`
- JSON: `/home/rfing/ODA_TRABOT/analysis/protection_failure_audit/protection_failure_results.json`
- Technical report: `/home/rfing/ODA_TRABOT/analysis/protection_failure_audit/protection_failure_audit.md`
