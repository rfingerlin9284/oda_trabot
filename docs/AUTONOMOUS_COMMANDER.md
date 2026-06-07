# Autonomous Commander

## Purpose

The commander lets the bot stay online 24/5 without forcing it to trade 24/5.

It sits after the signal engine and before broker submission:

`market data -> signal engine -> trade planner -> commander -> order preview -> OANDA practice`

The signal engine may find possible trades. The commander decides whether those trades are allowed to become orders.

## Default Behavior

Default is `NO_TRADE`.

The commander approves new entries only when a planned trade matches a verified grade and passes global guardrails.

## Global Guardrails

- Forex market must be open: Sunday 5 PM ET to Friday 5 PM ET.
- Session must be enabled by the Phase 1 contract.
- Pair and workflow must be allowed in that session.
- Average spread regime must not be too wide.
- Trade-level spread must not be too wide.
- Optional unrealized-loss lock can block new entries.

Open-trade management still runs separately, so the bot can manage existing trades even when new entries are blocked.

## Trade Grades

`A-grade momentum continuation`

- Core verified window: 3 AM to 9 AM ET.
- Uses historically verified April 14 momentum/continuation behavior.
- Requires strong confidence, votes, trend, and momentum.
- Uses the strongest verified OANDA pairs except symbols with weak historical evidence.
- This is the primary grade for `april14_momentum_3am_9am`.

`B-grade TurboScribe filtered trend`

- Requires the TurboScribe strategy pack.
- Uses top-down bias, EMA reclaim, false-break, and chop filters.
- This is a structured transcript-derived path, not direct transcript trading.

`C-grade controlled scalp`

- Only allowed in enabled day sessions.
- Requires clean spread and 2R availability.
- Treated as secondary until paper receipts prove expectancy.

`NO_TRADE`

- Any planned setup that does not pass a grade lands here.
- The runtime logs the reason instead of silently skipping.

## Runtime Logging

Each cycle now writes commander status into `state/last_runtime_status.json`:

- market open
- bad spread regime
- cycle status
- commander reasons
- per-plan approve/block decisions

The console log also prints commander decisions each cycle.

## Rule

The bot may stay awake 24/5.

The edge does not have to trade 24/5.
