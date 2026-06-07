# Phase Status

## Phase 1: Clean split between active work and old repo clutter
Status: `DONE`

What happened:
- WSL root was cleaned up
- old repo families were moved into `/home/rfing/READ_ONLY_LEGACY`
- the new rebuild got its own clean home at `/home/rfing/ODA_TRABOT`

Why it matters:
- reduces path confusion
- reduces agent drift
- keeps evidence without mixing it into production

## Phase 2: Lock the proven trading contract
Status: `DONE`

What happened:
- the new repo now has one hard-coded Phase 1 contract
- it preserves:
  - `7` pairs
  - practice-only
  - `3` vote minimum
  - strict confidence floor
  - `4` max open positions
  - `2` max new trades per cycle
  - `50,000` base units

Why it matters:
- stops silent drift back to random pair counts and random settings

## Phase 3: Session router and pair gate
Status: `DONE`

What happened:
- the new bot knows:
  - London
  - overlap
  - New York
  - Tokyo
  - off-session
- it knows when the day gate is open
- it knows which workflows are allowed by session
- it knows which pairs are allowed

Why it matters:
- this is the first clean replacement for the old messy session logic

## Phase 4: Approval gate
Status: `DONE`

What happened:
- the bot can now say yes or no to a setup
- it rejects for plain reasons like:
  - wrong pair
  - wrong session
  - votes too low
  - confidence too low

Why it matters:
- we no longer need mystery blocker language

## Phase 5: Signal pipeline shell and replay shell
Status: `DONE`

What happened:
- the new repo can generate workflow-specific raw signals
- it can replay example feature packets
- it can show which ideas would be approved or rejected

Why it matters:
- this is the start of a real bot brain, not just config

## Phase 6: Ranking, slot selection, and trade planning
Status: `DONE`

What happened:
- the new repo can:
  - rank approved setups
  - avoid duplicate pair conflicts
  - respect limited open slots
  - assign unit sizes
  - produce planned trades

Why it matters:
- the bot can now say what it would actually try to open

## Phase 7: Real historical evidence ingestion
Status: `DONE`

What happened:
- the new repo can now read the actual April 14 and V1C002 counterfactual evidence files
- it can summarize:
  - strongest windows
  - strongest pairs
  - strongest strategy families
  - best historical receipts

Why it matters:
- the rebuild is no longer blind to the real historical proof set

## Phase 8: OANDA practice adapter
Status: `DONE`

What happened:
- the new repo now has a safe OANDA practice client
- it can read:
  - account summary
  - open positions
  - live spreads
  - recent candles
- it can run a live cycle probe on the current practice market
- it has a paper-order submission path that stays preview-only unless explicitly armed
- it has a runtime loop shell that can keep cycling and write a last-known status file

Why it matters:
- the new repo can now inspect the real practice environment without starting the old bot

## Phase 9: Management and exits
Status: `DONE`

What happened:
- the new repo now has:
  - workflow-based stop and target geometry
  - green-lock values
  - order previews
  - runtime trade memory
  - broker reconciliation against open trade ids
  - stop-tighten decisions
  - broker close decisions
  - a real manager loop inside the running runtime

Why it matters:
- the new bot can now remember its own paper trades and manage them without leaning on legacy code

## Phase 10: Controlled paper trial
Status: `IN PROGRESS`

What happened:
- the new repo now has a real user service:
  - `oda_trabot.service`
- it has one control script:
  - `ops/service_control.sh`
- it has one mode file:
  - `state/runtime.env`
- it is now running on OANDA practice under its own clean repo

What still needs to happen:
- collect real paper receipts over time
- compare those receipts to the known April 14 and challenger windows

## What production ready means here

Production ready does not mean live money.

For this rebuild, production ready means:
- the new repo is the only active OANDA bot repo
- it can replay the known edge windows credibly
- it can run safely on OANDA practice
- it can place, track, and manage paper trades
- its behavior is understandable enough to audit
- it has its own service and no longer depends on the legacy runtime
