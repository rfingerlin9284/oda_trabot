# TurboScribe Normalized Edge Reference

## Purpose

This file turns the TurboScribe sprawl into one clean reference for `ODA_TRABOT`.

It is meant to answer four questions:

1. Which TurboScribe sources are worth trusting?
2. What exact strategies, workflows, indicators, and loss-protection rules do they prove?
3. What is already live inside `ODA_TRABOT`?
4. What is still missing and worth adding later?

## Source Ranking

### Tier 1: Best transcript truth for strategy and risk logic

These are the strongest sources to mine first.

- `/home/rfing/READ_ONLY_LEGACY/TurboScribe Export 825774768`
- `/home/rfing/READ_ONLY_LEGACY/TurboScribe Export 4076235464`
- `/home/rfing/READ_ONLY_LEGACY/RBOTZILLA_OANDA_CLEAN__pre_frozen_restore_20260415_094805/TurboScribe Export 3076884018`
- `/home/rfing/READ_ONLY_LEGACY/RBOTZILLA_OANDA_CLEAN__pre_frozen_restore_20260415_094805/TurboScribe Export 959515257`
- `/home/rfing/READ_ONLY_LEGACY/COINBASE_RESTORE_TEST_20260413_110635/rbtz_pheonix_1/dec4_dec10/RBOTZILLA_FLAT_DUMP.md`
- `/home/rfing/READ_ONLY_LEGACY/COINBASE_RESTORE_TEST_20260413_110635/rbtz_pheonix_1/dec4_dec10/rbz_tight_trailing.py`

Why Tier 1 matters:

- contains direct strategy walkthroughs
- contains concrete workflow sequences
- contains real protection logic
- contains actual thresholds and stop logic, not just vague ideas

### Tier 2: Useful supporting evidence

- `/home/rfing/READ_ONLY_LEGACY/RBOTZILLA_OANDA_CLEAN__pre_frozen_restore_20260415_094805/TurboScribe Export 319702483`
- `/home/rfing/READ_ONLY_LEGACY/COINBASE_RESTORE_TEST_20260413_110635/rbtz_pheonix_1/dec4_dec10/gemini_Strat_collect.txt`
- `/home/rfing/READ_ONLY_LEGACY/COINBASE_RESTORE_TEST_20260413_110635/rbtz_pheonix_1/dec4_dec10/restore_confidence_env.sh`

Why Tier 2 matters:

- useful for architecture clues
- useful for confirming which strategy families existed
- useful for confirming intended confidence and restore behavior

### Tier 3: Noisy, duplicated, or contaminated

- `/home/rfing/READ_ONLY_LEGACY/RBOTZILLA_OANDA_CLEAN__pre_frozen_restore_20260415_094805/TurboScribe Export 2971328458`
- loose temp markdown files from `C:\Users\RFing\AppData\Local\Temp\*.md`
- `all_strategies_parameters.txt`
- `envv_new.env.txt`

Why Tier 3 is weak:

- mixed unrelated content
- duplicated mirrors
- mislabeled filenames
- prior AI/chat contamination
- unsafe to treat as canonical truth

## Important Warning About Temp Markdown Files

The loose temp markdown files are not trustworthy by filename alone.

Examples found during audit:

- `workflow-router.md` content did not actually match workflow router
- `session-killzone-filter.md` content did not match its label
- `vwap-strategy-suite.md` content did not match its label
- `position-sizing-engine.md` content was mismatched and incomplete

Conclusion:

- use raw TurboScribe export folders first
- use loose temp markdown labels only as hints, never as truth

## Extracted Strategy Truth

## 1. Order Block Sniper

Primary source:

- `Order Blocks Explained Trade Like the Banks (No BS Guide).txt`

### Core rules

- Find a sharp displacement move.
- The order block is the candle before the displacement.
- A valid order block needs:
  - inefficiency or gap
  - break of structure
  - no full mitigation yet
- Best entries come when price returns into the block after structure has already shifted.

### Workflow

- Start with higher-timeframe direction.
- Mark the order block that caused the break.
- Wait for price to return into the zone.
- Refine on lower timeframe for confirmation.
- Enter on lower-timeframe shift or mini order block.

### Indicators and concepts

- market structure
- break of structure
- displacement
- inefficiency
- order block
- optional Fibonacci helper

### Loss protection

- stop above or below the order block
- move stop to breakeven once trade proves itself
- do not reuse already mitigated blocks
- take profit at the next realistic liquidity or order block, not always the farthest target
- reduce exposure near Friday close or weekend conditions

## 2. Range Bounce and Breakout

Primary source:

- `Most Effective RANGE Trading Strategy for Crypto Forex & Stocks (SidewaysChoppy Market Strategy).txt`

### Core rules

- First identify a true range.
- Support and resistance are zones, not exact lines.
- In a wide range, trade the bounces.
- In a narrow range, prepare for a breakout instead.
- A breakout must be backed by real momentum, not a weak candle.

### Workflow

- classify regime first: trend or range
- if wide range:
  - buy support zone
  - sell resistance zone
- if narrow range:
  - wait for breakout
  - require momentum confirmation

### Indicators and concepts

- market structure
- support and resistance zones
- candle momentum
- breakout follow-through

### Loss protection

- avoid using trend indicators blindly inside ranges
- avoid weak break candles
- use momentum candle filter to avoid false breakout entries

## 3. Smart-Money Liquidity Sweep plus FVG plus Order Block

Primary source:

- `Smart Money Concepts How I Combine Liquidity Sweeps, FVGs & Order Blocks (Full Strategy).txt`

### Core rules

- Use higher timeframe to locate the liquidity sweep and the order block.
- Require immediate reversal after the sweep.
- Require a lower-timeframe structure break or change of character.
- Use FVG midpoint as the refined entry, not a random market chase.

### Workflow

- higher timeframe:
  - locate sweep
  - locate order block
  - locate nearby liquidity target
- lower timeframe:
  - wait for market shift
  - identify bullish or bearish FVG
  - place limit at midpoint

### Indicators and concepts

- liquidity sweep
- order block
- fair value gap
- market structure shift
- change of character
- higher-timeframe liquidity target

### Loss protection

- enter at midpoint instead of chasing
- target nearest higher-timeframe liquidity
- keep timeframe discipline
- use structure-defined invalidation

## 4. Top-Down Bias Stack

Primary source:

- `The Best Top Down Analysis Strategy for 2025 Forex Trading Guide.txt`

### Core rules

- Use weekly, daily, and 4H to define directional bias.
- Use lower timeframe only for aligned entries.
- Pullbacks are acceptable only when lower timeframe re-aligns back into the higher-timeframe direction.

### Workflow

- weekly: broad structure and major trend
- daily: directional bias
- 4H: active trend state
- 2H, 1H, 30m, 15m: entry alignment

### Indicators and concepts

- multi-timeframe structure
- higher-timeframe trend
- lower-timeframe re-alignment
- pullback continuation

### Loss protection

- do not counter-trade the higher-timeframe direction
- wait for lower-timeframe structure to re-align before entering

## 5. 9 EMA Continuation and Prop-Desk Scalp

Primary sources:

- `Moving Average Trading Tutorial (For Day Trading).txt`
- `How to Scalp Like an Elite Prop Trader (Inside Look).txt`
- `Scalping series #01 Rules for scalping.txt`
- `Step-by-Step Tutorial to Make Consistent Daily Profits in 2026.txt`

### Core rules

- Strong move first, then pullback.
- First touch of the 9 EMA is higher quality than late touches.
- Better when there is a catalyst or clear directional session context.
- Second-chance entry can be valid if the original move resumes cleanly.

### Workflow

- identify a clean directional move
- wait for pullback to EMA or key reclaim zone
- require buyer or seller response
- enter on continuation confirmation

### Indicators and concepts

- 9 EMA
- trend continuation
- second-chance scalp
- opening range or key reclaim
- catalyst and momentum context

### Loss protection

- stop below pullback low or reclaim low
- do not chase late entries
- trail with EMA or structure once trade expands
- realistic R framing, not fantasy target forcing
- avoid first few minutes unless setup is exceptional

## 6. False Breakout Filter

Primary source:

- `How I Avoid False Breakouts (My Secret Technique).txt`

### Core rules

- Too many repeated touches weaken a level.
- Breakouts need real expansion and follow-through.
- The first few bars after the break matter.

### Workflow

- watch the break
- watch the next five bars
- if follow-through is weak, indecisive, or lethargic:
  - do not trust the break
- if full failure develops:
  - wait for the other side of the range to break or retest

### Indicators and concepts

- breakout pressure
- post-break behavior
- follow-through quality
- retest response

### Loss protection

- fold quickly if follow-through is poor
- do not chase a breakout without confirmation

## 7. Orderflow and Value-Area Framework

Primary source:

- `The Only Orderflow Guide You'll Ever Need.txt`

### Core rules

- Use value and imbalance to understand where price is accepted or rejected.
- Distinguish aggressive participation from passive absorption.
- Do not rely on price alone if the underlying flow disagrees.

### Workflow

- determine value area and key volume nodes
- look for imbalance or acceptance failure
- use orderflow signs to confirm continuation or reversal

### Indicators and concepts

- volume profile
- value area
- point of control
- low volume nodes
- delta
- absorption
- initiative auction
- exhaustion

### Loss protection

- do not enter when aggression and result disagree
- use value acceptance or rejection to frame invalidation

## 8. Swing Ladder and Continuous Realized Gains

Primary source:

- `How I Swing Trade for Continuous Realized Gains - My Full Strategy Revealed.txt`

### Core rules

- Keep a core position.
- Use swing overlays around the core instead of full in and full out.
- Sell some into extension and buy some into discount.

### Workflow

- keep core size intact
- trade around the core
- trim when stretched above moving average
- add when stretched below moving average

### Indicators and concepts

- moving average stretch
- ladder scaling
- portfolio weight control

### Loss protection

- never trim below the core floor
- avoid trading names you do not understand deeply
- keep cash available
- stop swing trading when breakout regime becomes real

## December and Phoenix Edge Evidence

## 9. EMA, RSI, MACD, ATR, FVG, Supply/Demand, and Liquidity Sweep Stack

Primary source:

- `RBOTZILLA_FLAT_DUMP.md`

### Concrete strategy families found

- EMA trend alignment
- RSI momentum
- MACD crossover
- FVG fill
- supply and demand rejection
- sideways RSI mean reversion
- liquidity sweep

### Concrete indicators found

- EMA 9
- EMA 21
- EMA 50
- RSI
- MACD
- ATR
- Bollinger Bands
- FVG logic
- supply and demand
- liquidity sweep

### Concrete loss protection found

- ATR stop example:
  - `sl = atr * 1.5`
- ATR target example:
  - `tp = atr * 3.2`
- minimum risk reward example:
  - `MIN_RISK_REWARD_RATIO = 3.2`
- daily loss breaker example:
  - `DAILY_LOSS_BREAKER_PCT == -5.0`
- FX stop multiplier example:
  - `FX_STOP_LOSS_ATR_MULTIPLIER = 1.2`
- crypto stop multiplier example:
  - `CRYPTO_STOP_LOSS_ATR_MULTIPLIER = 1.5`

### Other concrete protection and governance found

- session bundles
- enable or disable strategy families by regime
- risk tier examples:
  - `0.25`
  - `0.5`
  - `1.0`

## 10. Tight Trailing and Two-Step Lock

Primary source:

- `rbz_tight_trailing.py`

### Core protection logic

- step-one lock
- breakeven transition
- aggressive trailing
- TP guard

### Pair-aware examples

- major:
  - `TightSL(0.0020, -0.0003, 0.0040, 0.0070, 0.0020)`
- minor:
  - `TightSL(0.0025, -0.0003, 0.0045, 0.0080, 0.0022)`
- exotic:
  - `TightSL(0.0030, -0.0004, 0.0050, 0.0100, 0.0025)`

### What it proves

- loss protection used to be more sophisticated than a static stop and target
- pair class mattered
- the system did include graduated protection logic, not just one hard stop

## 11. Strategic Hedge or Flip Protection

Primary source:

- `RBOTZILLA_FLAT_DUMP.md`

### Core logic

- if a trade stays in loss past pip and time thresholds
- and momentum flips
- the system can open an opposite hedge or flip

### Concrete thresholds found

- `loss_pips_trigger: 7.0`
- `loss_pips_max: 42.0`
- `loss_time_trigger_sec: 600`
- `hedge_sl_pips: 15.0`
- `hedge_tp_pips: 45.0`

### Confirmation stack found

- `ema_fast: 21`
- `ema_slow: 50`
- `rsi_period: 21`
- `rsi_up_min: 55`
- `rsi_down_max: 45`
- optional FVG confirmation:
  - `use_fvg_confirmation: true`
  - `fvg_min_gap_pips: 3.0`

## Cross-Cutting Workflow Truth

The transcripts strongly support these shared principles:

- regime first, entry second
- higher timeframe bias matters
- lower timeframe refinement matters
- momentum continuation is a real edge family
- scalp entries need a specific session and context
- not every session should run the same playbook
- stop logic and trailing logic matter almost as much as entries
- correlation and exposure stacking should be controlled
- daily loss breakers are real protection, not optional noise

## Loss Protection Summary

These are the strongest recurring protection ideas across sources.

### Strongly supported

- fixed or structure-defined invalidation
- ATR-based stop sizing
- risk reward floor around 2R to 3.2R
- breakeven transition after proof
- two-step lock then trail
- pair-aware trailing presets
- daily loss breaker
- per-trade risk cap
- session restriction
- correlation or exposure de-stacking

### Supported but needs careful treatment

- strategic hedge or flip when loss persists and momentum reverses
- TP guard and profit-harvest logic
- swing overlay logic around a core position

### Not yet trustworthy enough to rebuild blindly

- contaminated environment dumps with mixed AI notes
- any temp markdown file whose content does not match its filename

## Mapping Against Current Live ODA_TRABOT

## Already live now

- 7-pair OANDA practice scanning
- session router
- continuation workflow
- second_chance workflow
- fashionably_late workflow
- scalp workflow
- confidence and votes gate
- max open positions
- live broker spread input
- M15 candle input
- trend score
- momentum score
- retest score
- breakout score
- scalp score
- volatility score

## Partial now

- session killzone logic
- workflow router
- top-down bias idea
- position sizing engine
- scalp math rules

## Missing now

- liquidity sweep entry
- order block sniper
- FVG entry logic
- range bounce and breakout regime switch
- orderflow and value-area logic
- VWAP suite
- full ATR-based stop engine
- full two-step trailing engine
- strategic hedge or flip logic
- market-news helper
- AI hive or sentiment weighting

## Best Next Strategy Additions for ODA_TRABOT

Add them one at a time, in this order:

1. liquidity sweep plus FVG plus order block
2. order block sniper refinement
3. top-down bias stack
4. range bounce and breakout regime switch
5. ATR-based stop plus 3R-style target framework
6. two-step lock plus trailing engine
7. false-breakout filter

Why this order:

- it adds the strongest smart-money edge first
- it improves structure and invalidation before complexity
- it improves loss protection before exotic add-ons

## Rebuild Guidance

Do not rebuild from:

- loose temp markdown labels
- contaminated December parameter dumps
- duplicated mirror trees

Do rebuild from:

- Tier 1 transcript folders
- concrete code-based protection logic
- April 14 session-shaped OANDA evidence
- one strategy family at a time

## Bottom Line

The TurboScribe folders prove that the historical edge was not one simple indicator trick.

It was a stack of:

- session-aware workflow routing
- higher-timeframe bias
- lower-timeframe confirmation
- structure-based entries
- momentum continuation
- smart-money refinement
- disciplined invalidation
- real loss protection

The clean `ODA_TRABOT` bot already has the session shell and confidence shell.

What it still needs most is:

- smart-money structure entries
- stronger top-down bias logic
- better stop and trail protection

That is the safest path to carry the best transcript truth forward without dragging legacy drift back into production.
