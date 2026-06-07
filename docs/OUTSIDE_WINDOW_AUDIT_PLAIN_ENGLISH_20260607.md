# Outside-Window Audit - Plain English Decision Report

Date: June 7, 2026

Repo: ODA_TRABOT

## One-Sentence Answer

The audit found one outside-window edge worth building from: momentum continuation after the frozen 3 AM-9 AM cartridge, especially 9:00 AM-11:30 AM ET.

This does not mean trade all day.

It means the bot found repeated profitable OANDA practice trades when the morning momentum move continued after 9 AM.

## What Was Audited

I scanned historical logs from the older read-only repos.

I only counted trades that met this proof standard:

- OANDA practice/live-paper log data only
- Closed trade with positive P&L
- Outside the frozen 3 AM-9 AM ET momentum cartridge window
- Linked to real practice order evidence where possible
- Not Coinbase
- Not TurboScribe transcript claims
- Not replay-only or backtest-only result files
- Not "estimated" closes for cartridge decisions
- Not "transcript" close reasons for cartridge decisions

## Why This Is Real Evidence

The strongest evidence class was:

`high_confidence_practice_receipt`

That means the trade close was linked to a matching OANDA practice order that logged:

- `environment: PRACTICE`
- `live_api: true`
- `visible_in_oanda: true`

That is the clean paper-trading receipt standard.

## Audit Size

- Files scanned: 224
- Data scanned: about 3.46 GB
- Lines scanned: 12,341,503
- JSON log records scanned: 9,306,144
- Close events found: 9,172
- Profitable close events found: 1,755
- Profitable close events outside 3 AM-9 AM: 1,290
- Unique profitable outside-window trades: 87
- High-confidence practice receipts: 74
- Clean high-confidence receipts used for cartridge mining: 59

## The Main Finding

The winning outside-window behavior was not a new unrelated strategy.

It was mostly the same family:

`momentum / continuation`

That means:

- trend still aligned
- momentum still active
- continuation/reclaim behavior still holding
- common detectors included `ema_stack`, `fibonacci`, and sometimes `momentum_sma`

## Strongest Outside-Window Block

Best block:

`9:00 AM-11:30 AM ET momentum continuation`

Evidence:

- 16 clean wins based on close-time grouping
- Total clean P&L: about +$772.61
- 13 of those trades opened after 9:00 AM ET
- Those post-9 AM entries alone produced about +$610.62
- Pairs involved: AUD_USD, EUR_USD, GBP_USD, NZD_USD, USD_CAD, USD_CHF

This matters because it proves the 9 AM idea was not just old 3 AM-9 AM trades being carried forward. Most of the strongest group actually opened after 9 AM.

## Ranked Outside-Window Candidates

| Rank | Candidate | Clean Wins | Approx P&L | Decision |
| --- | --- | ---: | ---: | --- |
| 1 | 9:00-11:30 AM momentum continuation | 16 | +$772.61 | Build first |
| 2 | 11:30 AM-2:00 PM momentum continuation | 10 | +$497.68 | Paper-probation candidate |
| 3 | 2:00-5:00 PM momentum continuation | 8 | +$502.55 | Paper-probation candidate |
| 4 | 5:00 PM rollover momentum | 7 | +$185.93 | Watch only at first |

## What Did Not Clear The Bar

Other strategy labels had some wins, but not enough clean repeated evidence to become their own cartridge.

| Strategy Family | Clean Wins | Decision |
| --- | ---: | --- |
| momentum | 44 | Proven outside-window family |
| scalp | 6 | Not enough for main cartridge |
| reversal | 4 | Not enough for cartridge |
| legacy | 3 | Too vague, not clean enough |
| trend continuation label | 2 | Supports momentum continuation, not separate enough |
| smart money / mean reversion | 1 each | Not proven |

## Trading Meaning

The frozen cartridge remains:

`april14_momentum_3am_9am`

That is the primary morning edge.

The next cartridge is:

`post_9am_momentum_continuation`

That cartridge is not a different bot personality. It is the same momentum logic allowed to keep hunting only when the move continues after the main morning window.

## What The New Cartridge Does

The new cartridge watches after 9 AM ET for continuation setups.

It only considers trades when:

- the pair is one of the proven post-9 pairs
- the signal is momentum or continuation
- the detectors show `ema_stack` and `fibonacci`
- `momentum_sma` strengthens the setup when present
- spread is acceptable
- the bot has open position capacity
- daily loss and peak-giveback protections are clean

Default outside those conditions:

`NO_TRADE`

## What The New Cartridge Does Not Do

It does not:

- trade 24/5 just because the market is open
- replace the frozen 3 AM-9 AM cartridge
- turn scalp into the main strategy
- use TurboScribe as the base
- import old repo code
- treat backtests or transcript claims as proof

## Final Decision

Build this as the first outside-window candidate cartridge:

`post_9am_momentum_continuation`

Initial active entry window:

`9:00 AM-11:30 AM ET`

Initial pair list:

- AUD_USD
- EUR_USD
- GBP_USD
- NZD_USD
- USD_CAD
- USD_CHF

Initial mode:

`practice only`

Activation level:

`candidate cartridge with paper probation`

That is the clean decision from the logged historical evidence.

