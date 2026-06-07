# Strategy Packs

Strategy behavior is now loaded through a cartridge-style socket:

- signal checks and confidence weights
- workflow ranking priority
- position sizing tiers
- exit profiles and scalp/default stop-target behavior

The main pipeline modules are the only code that read the active entry pack:

- `SignalPipelineShell`
- `SignalSelector`
- `PositionSizer`
- `OrderPreviewBuilder`
- runtime trade management

Runtime entry selection is automatic when `ODA_TRABOT_CARTRIDGE_ROUTING=auto`.

## Available Packs

`april14_momentum_3am_9am`

- Primary active cartridge for the April 14 proven momentum lane.
- OANDA practice only.
- Emits the `momentum` workflow directly; scalp is disabled in this pack.
- Runtime schedule gates entries to 3:00 AM ET through the 8:30 AM ET minute.
- Uses the April 14 evidence pair universe:
  - `USD_CHF`
  - `GBP_USD`
  - `EUR_USD`
  - `NZD_USD`
  - `USD_CAD`
  - `AUD_USD`
  - `USD_JPY`
- Documents the `peak_giveback_175_after_350` overlay, which is implemented as a clean runtime guard.

`post_9am_ema_fib_momentum_continuation`

- Second frozen cartridge, derived from clean outside-frozen OANDA practice receipts.
- OANDA practice only.
- Emits only the `continuation` workflow.
- Runtime schedule gates entries to 9:00 AM ET through 11:29 AM ET.
- Uses the clean post-9 pair universe:
  - `AUD_USD`
  - `EUR_USD`
  - `NZD_USD`
  - `USD_CAD`
  - `USD_CHF`
- Requires EMA/Fibonacci continuation proxies through `top_down_bias_score`, `ema_9_reclaim_score`, trend, momentum, post-break acceptance, retest, low failed-break risk, low chop, and acceptable spread.
- Uses the same broker-visible OCO stop/target profile as the morning pack: 10 pip stop, 25.2 pip target, 15 pip green-lock threshold, 5 pip lock.
- Excludes scalp, reversal, trap/reversal labels, and loose generic momentum.

## Automatic Cartridge Schedule

With `ODA_TRABOT_CARTRIDGE_ROUTING=auto`, entry planning is:

- `03:00:00-08:30:59 ET`: `april14_momentum_3am_9am`
- `08:31:00-08:59:59 ET`: no new entries; manage existing trades only
- `09:00:00-11:29:59 ET`: `post_9am_ema_fib_momentum_continuation`
- `11:30:00 ET onward`: no new entries; manage existing trades only

Open trades are not force-closed just because a cartridge window ends. They are managed first on every cycle using the trade's recorded workflow/profile, broker stop, broker target, and green-lock rules. The cartridge schedule controls new entries only.

`legacy_phase1`

- Mirrors the original hardcoded behavior.
- Use this when you want the old strategy and old exit behavior.

`turboscribe_phase1`

- Uses the TurboScribe extraction as a Phase 1 pack.
- Active logic uses the cartridge feature slots built from M15 candles.
- Current cartridge slots include top-down proxy, 9 EMA reclaim, first-touch quality, late-touch penalty, range width, chop penalty, false-break risk, and 2R availability.
- Order block, FVG midpoint, and true orderflow logic stay disabled until those specialized detectors exist.
- Scalp exits use a 10 pip stop and 20 pip target to honor the extracted 2R floor.

## Master TurboScribe Library

The full TurboScribe day/swing conversion inventory is larger than the active M15 cartridge:

- `analysis/turboscribe/full_convertible_strategy_library.json`
- `analysis/turboscribe/full_convertible_strategy_library.md`
- `configs/strategy_manifests/turboscribe_day_swing_master.json`

Use the manifest as the master cartridge menu. It separates strategies into:

- swappable now through `turboscribe_phase1`
- disabled until multi-timeframe/session/structure data exists
- support-only research and risk modules
- separate bot families for options, equities, crypto, futures/orderflow, and short-selling logic

## Cartridge Feature Slots

These fields live on `FeatureSnapshot` and can be referenced by pack JSON:

- `top_down_bias_score`
- `entry_timeframe_alignment_score`
- `ema_9_distance`
- `ema_9_reclaim_score`
- `first_touch_quality`
- `late_touch_penalty`
- `range_width_score`
- `support_rejection_score`
- `resistance_rejection_score`
- `chop_penalty`
- `break_followthrough_score`
- `failed_break_risk`
- `post_break_acceptance_score`
- `level_touch_count`
- `two_r_available`

The top-down field is currently an M15-derived proxy. True weekly/daily/4H confirmation needs a later multi-timeframe market data pass.

## Manual Cartridge Override

Automatic routing is the production/default mode:

```bash
export ODA_TRABOT_CARTRIDGE_ROUTING=auto
```

Use manual mode only when deliberately comparing one pack:

```bash
export ODA_TRABOT_CARTRIDGE_ROUTING=manual
export ODA_TRABOT_STRATEGY_PACK=turboscribe_phase1
```

Or point to a file:

```bash
export ODA_TRABOT_STRATEGY_PACK=/home/rfing/ODA_TRABOT/configs/strategy_packs/turboscribe_phase1.json
```

Unset it to return to the compatibility pack:

```bash
unset ODA_TRABOT_STRATEGY_PACK
```

## Rule

Do not wire transcript-derived strategy logic directly into broker code. Add it to a strategy pack first, then let the pipeline load it.
