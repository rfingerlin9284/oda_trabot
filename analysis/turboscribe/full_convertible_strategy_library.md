# TurboScribe Full Convertible Strategy Library

This is the human-readable conversion pass over the TurboScribe transcript inventory. It captures every method that has enough rule structure to become a deterministic strategy, detector, filter, risk module, or separate bot family.

The current ODA_TRABOT runtime fetches M15 candles only, so only the M15-safe proxies belong in the active `turboscribe_phase1` cartridge. The rest are not discarded. They are preserved here as buildable cartridges that stay disabled until their required data modules exist.

## Conversion Policy

- Convert rules into deterministic detectors before they can trade.
- Keep transcript logic out of broker code.
- Plug strategies through `ODA_TRABOT_STRATEGY_PACK` and the existing main pipeline only.
- Require replay/backtest receipts, paper-trading receipts, OCO protection, exposure limits, and a daily loss breaker before any live-money use.
- Treat options, equities, futures, and crypto-specific methods as separate bot families unless OANDA-compatible data and execution exist.

## Active Now: M15-Compatible Cartridge

These methods are already represented in `configs/strategy_packs/turboscribe_phase1.json` using M15 candle-derived fields.

| Strategy | Current Conversion | Runtime Fields |
| --- | --- | --- |
| `ema9_first_touch_continuation` | Partially active | `ema_9_reclaim_score`, `first_touch_quality`, `late_touch_penalty`, `momentum_score` |
| `prop_desk_scalp_playbook` | Partially active | `spread_score`, `momentum_score`, `post_break_acceptance_score`, `two_r_available` |
| `false_breakout_filter` | Partially active | `level_touch_count`, `break_followthrough_score`, `failed_break_risk`, `post_break_acceptance_score` |
| `range_bounce_breakout_classifier` | Partially active | `range_width_score`, `support_rejection_score`, `resistance_rejection_score`, `chop_penalty` |
| `systematic_risk_reward_ev_filter` | Active as risk gate | `risk_reward`, `two_r_available`, sizing tiers, exit profiles |

## Highest-Priority Day/Swing Builds

These are the next strategies that can become strong OANDA day/swing cartridges once the missing data modules are added.

| Priority | Strategy | Edge Being Converted | Missing Data/Detector |
| --- | --- | --- | --- |
| 1 | `top_down_bias_stack` | Trade only with weekly/daily/H4 structure and use lower timeframes for entries | Weekly, daily, H4, H1/M30 candle fetcher; multi-timeframe bias detector |
| 2 | `simple_5m_first_15m_bias_scalp` | First 15-minute session candle defines the intraday bias; execute on 5-minute retest/continuation | Session calendar, M5 candles, first-session-candle detector |
| 3 | `order_block_retest` | Trade retests of the last displacement origin after structure break | Swing structure, displacement candle, order-block zone detector |
| 4 | `liquidity_sweep_fvg_midpoint` | Sweep liquidity, displace, then enter near FVG midpoint if bias agrees | Swing highs/lows, sweep detector, fair-value-gap detector |
| 5 | `supply_demand_zone_rejection` | Enter when price rejects a fresh zone with imbalance and clean invalidation | Zone freshness, imbalance, touch-count, rejection detector |
| 6 | `liquidity_manipulation_structure_to_structure` | Avoid obvious retail breakout traps; trade from engineered liquidity grab to next structure | Liquidity pool map, sweep confirmation, structure targets |
| 7 | `opening_range_ai_alert_model` | Generate only precise alerts when opening range, time, momentum, and retest conditions align | Session open/range builder, alert-condition compiler |
| 8 | `swing_pullback_continuation` | Hold swing continuation only when higher-timeframe trend, pullback quality, and R:R align | Daily/H4/H1 trend stack, pullback-depth detector |

## Full Strategy Families

### `top_down_bias_stack`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: weekly/daily/H4 bias filters lower-timeframe entries.
- Convert to: multi-timeframe bias gate, entry-timeframe alignment gate, counter-bias rejection.
- Status: disabled until multi-timeframe candles are fetched.

### `ema9_first_touch_continuation`

- Style: day
- Markets: forex, futures, stocks, crypto
- Core edge: strong impulse, first pullback or reclaim of 9 EMA, then continuation confirmation.
- Convert to: 9 EMA reclaim detector, first-touch quality score, late-touch penalty.
- Status: partially active in `turboscribe_phase1`.

### `prop_desk_scalp_playbook`

- Style: day
- Markets: forex, futures, stocks
- Core edge: scalp only when timing, liquidity, momentum, spread, and invalidation are aligned.
- Convert to: session gate, micro-momentum detector, spread/slippage gate, scratch-if-no-followthrough rule.
- Status: partially active in `turboscribe_phase1`; full build needs M1/M5 and tighter execution telemetry.

### `simple_5m_first_15m_bias_scalp`

- Style: day
- Markets: forex, futures, stocks
- Core edge: first 15-minute candle sets session bias; 5-minute retest/continuation becomes the trigger.
- Convert to: session-open 15M bias, M5 retest score, 2R availability gate.
- Status: high-priority disabled cartridge until M5/session data exists.

### `opening_range_ai_alert_model`

- Style: day
- Markets: forex, futures, stocks, crypto
- Core edge: precise alert logic beats broad price-cross alerts.
- Convert to: opening range high/low, break/retest/acceptance conditions, alert-only candidate generation.
- Status: support module, not direct execution.

### `false_breakout_filter`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: avoid breaks that immediately fail, drift, or close back inside the level.
- Convert to: touch count, follow-through, acceptance/rejection, failed-break risk.
- Status: partially active in `turboscribe_phase1`.

### `range_bounce_breakout_classifier`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: wide ranges favor bounces; narrow compressed ranges favor breakout prep.
- Convert to: range width score, support/resistance rejection, chop penalty, breakout readiness.
- Status: partially active in `turboscribe_phase1`.

### `order_block_retest`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: after displacement and structure break, retest the last opposing candle/zone that launched the move.
- Convert to: market-structure break, displacement score, order-block bounds, retest/rejection trigger.
- Status: disabled until structure and zone detectors exist.

### `liquidity_sweep_fvg_midpoint`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: liquidity sweep plus displacement creates an imbalance; enter near midpoint only with bias.
- Convert to: sweep detector, fair-value-gap detector, midpoint entry zone, invalidation on sweep extreme.
- Status: disabled until FVG/liquidity detectors exist.

### `ict_opening_gap_discount_premium`

- Style: day
- Markets: futures, indices, forex where session gaps are meaningful
- Core edge: session opening gap and premium/discount zones guide directional setups.
- Convert to: opening gap, equilibrium, premium/discount, time-window filters.
- Status: disabled until session-aware data exists.

### `supply_demand_zone_rejection`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: fresh supply/demand zones with imbalance and clean rejection offer defined invalidation.
- Convert to: zone creation, freshness, touch count, rejection strength.
- Status: disabled until zone detector exists.

### `liquidity_manipulation_structure_to_structure`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: trade after liquidity engineering and structure confirmation, targeting next obvious structure.
- Convert to: retail-liquidity pool map, sweep/stop-run confirmation, structure-to-structure target.
- Status: disabled until liquidity map exists.

### `orderflow_value_area_auction`

- Style: day
- Markets: futures, stocks, crypto; limited forex spot fit without volume/orderflow feed
- Core edge: auction context, value area, delta/volume, and price acceptance filter entries.
- Convert to: VWAP/value area, volume profile, delta/orderflow confirmation.
- Status: separate module; requires volume/orderflow source.

### `ma_crossover_trend_filter`

- Style: day, swing
- Markets: forex, futures, stocks, crypto
- Core edge: moving-average crossovers filter trend direction but need volatility and structure gates.
- Convert to: trend state, slope, crossover age, chop filter.
- Status: convertible support filter, not a standalone high-edge entry.

### `fractal_sma_crossover_scalp`

- Style: day
- Markets: forex, futures, crypto
- Core edge: fractal swing points and SMA cross identify short-term momentum shifts.
- Convert to: fractal pivot detector, SMA cross, whipsaw/chop filter.
- Status: lower-priority cartridge; needs M1/M5 replay before activation.

### `parabolic_sar_cci_scalp`

- Style: day
- Markets: forex, futures, crypto
- Core edge: SAR trend flip plus CCI momentum confirmation creates a mechanical scalp trigger.
- Convert to: SAR flip, CCI regime, trend/chop filter, fixed invalidation.
- Status: lower-priority cartridge; needs M1/M5 replay before activation.

### `swing_ladder_core_overlay`

- Style: swing
- Markets: stocks, crypto, forex
- Core edge: build positions in favorable trend regimes rather than all at once.
- Convert to: trend regime, add-on trigger, max exposure, de-risk trigger.
- Status: separate swing risk overlay.

### `swing_pullback_continuation`

- Style: swing
- Markets: forex, futures, stocks, crypto
- Core edge: higher-timeframe trend plus controlled pullback and continuation trigger.
- Convert to: trend stack, pullback depth, reclaim confirmation, swing R:R gate.
- Status: disabled until daily/H4/H1 candles exist.

### `systematic_risk_reward_ev_filter`

- Style: day, swing
- Markets: all
- Core edge: method quality depends on repeatable risk/reward, expectancy, and drawdown limits.
- Convert to: minimum 2R availability, position-sizing tiers, daily loss breaker, strategy-level telemetry.
- Status: active as a risk module; should be expanded before live use.

### `smb_quant_modeling_process`

- Style: research
- Markets: all
- Core edge: hypotheses must become testable features, backtests, and monitored live/paper experiments.
- Convert to: experiment registry, feature store, replay metrics, out-of-sample validation.
- Status: research framework, not an entry strategy.

### `crypto_rotation_trend_model`

- Style: day, swing
- Markets: crypto
- Core edge: rotate into stronger crypto assets based on trend, liquidity, relative strength, and risk.
- Convert to: crypto universe scanner, relative-strength ranks, volatility sizing.
- Status: separate crypto bot family.

### `equity_catalyst_sector_swing`

- Style: day, swing
- Markets: stocks, ETFs
- Core edge: catalyst, sector strength, news/earnings context, and technical trigger align.
- Convert to: equity universe scanner, catalyst tags, sector-relative strength, earnings/news calendar.
- Status: separate equities bot family.

### `defined_risk_options_income`

- Style: swing/income
- Markets: options
- Core edge: defined-risk spreads and iron condors use volatility, probability, and event-risk filters.
- Convert to: options chain parser, Greeks, IV rank, expiration/event filters, spread builder.
- Status: separate options bot family.

### `short_selling_risk_framework`

- Style: day, swing
- Markets: stocks, ETFs, futures
- Core edge: short setups need borrow/liquidity constraints, squeeze-risk filters, and hard stops.
- Convert to: weakness scanner, liquidity/borrow gate, squeeze-risk detector, exposure cap.
- Status: separate equities/futures risk module.

## Rejected Or Not Used As Strategy

- "100% winning trades" claims are rejected unless they reduce to measurable conditions.
- Pure mindset, motivational, ecommerce, game development, and long-term passive-investing transcripts are not converted into day/swing execution logic.
- Broad "AI makes money" content is used only when it yields explicit alert logic, data requirements, or testing workflow.

## Build Order

1. Keep `turboscribe_phase1` active as the M15-safe cartridge.
2. Add multi-timeframe candle fetcher and activate `top_down_bias_stack`.
3. Add M5/session support and activate `simple_5m_first_15m_bias_scalp`.
4. Add structure, order-block, liquidity sweep, and FVG detectors.
5. Add supply/demand zone freshness and rejection scoring.
6. Add M1/M5 micro-scalping replay for SAR/CCI and fractal/SMA methods.
7. Build separate crypto, equity, options, and orderflow bot families only after the OANDA day/swing stack is stable.
