# Rebuild Blueprint

## Plain-English Goal

Build one clean OANDA practice bot that is small, understandable, and based only on proven behavior.

We are not trying to restore every old repo.
We are rebuilding only the parts that actually showed real edge.

## Evidence We Trust Most

Primary evidence family:
- `/home/rfing/PRODUCTION_BUNDLES/APRIL14_RESTORE_BALANCED_ENTRY_v1`
- `/home/rfing/backups/RESTORED_PRE10AM_TRANSFER_READY_20260430_025439/repos/OAD_DEV/analysis/oanda_loss_manager_counterfactual_apr14_session_20260421.json`
- `/home/rfing/EDGE_RECOVERY_TRUTH_CHECK_20260508/APRIL14_BASELINE_STATUS.md`

Useful challenger evidence:
- `/home/rfing/V1C002_APRIL14_EDGE_REBUILD_20260508/evidence/candidate_current_session_counterfactuals.json`
- `/home/rfing/V1C002_APRIL14_EDGE_REBUILD_20260508/reports/EDGE_REBUILD_DECISION.md`

## What The Evidence Says

The strongest proven edge was not a magical 24-hour everything-bot.

The strongest evidence points to:
- a session-shaped bot
- momentum as the main money-maker
- strongest performance from about `3:00 AM ET` to `9:00 AM ET`
- a broader `7`-pair hunting field, not just `4` pairs
- strict entry quality, not loose overtrading

Verified strong April 14 replay result:
- about `+$534.48`
- `20` closed trades
- `12` wins
- `8` losses
- strategy split: mostly `momentum`

## Phase 1 Build Contract

Version 1 of this rebuild should be:
- OANDA only
- practice only
- `7` pairs:
  - `EUR_USD`
  - `GBP_USD`
  - `USD_JPY`
  - `USD_CHF`
  - `AUD_USD`
  - `USD_CAD`
  - `NZD_USD`
- session gate:
  - `03:00 ET` to `17:00 ET`
- primary active workflows:
  - London: `continuation, second_chance, fashionably_late, scalp`
  - Overlap: `continuation, second_chance, fashionably_late, scalp`
  - New York: `continuation, second_chance, scalp`
- minimum votes: `3`
- confidence floor: strict
- max open positions: `4`
- OCO required
- simple plain-English operator output

## Phase 1 Simplifications

Version 1 should not include:
- Coinbase logic
- multi-broker logic
- Phoenix agent swarm
- LLM sentiment
- news helper scoring
- dual-system capital routing
- drifted hotfix layers from later repos

## Phase 2 Only If Version 1 Proves Itself

After the core bot is replayed and paper-validated, we may test:
- Tokyo and off-session workflows
- selected scalp expansions
- selected smart-money style lanes

These are not part of the first clean rebuild unless receipts prove they help.

## Build Order

1. lock the project contract
2. create simple config model
3. create pair/session router
4. create signal pipeline shell
5. create order sizing and broker guard shell
6. create manager / exits
7. create replay harness
8. compare against known profitable windows
9. run paper only

## Success Definition

The rebuild is successful only if it:
- matches the intended session and pair behavior
- avoids obvious churn
- replays the known profitable windows credibly
- stays understandable enough that the user can follow what it is doing
