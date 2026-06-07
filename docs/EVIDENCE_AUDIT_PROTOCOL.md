# Evidence Audit Protocol

## Goal

Find what actually produced winning trades in the old material, then rebuild only the verified behavior inside the clean OANDA practice bot.

This repo should learn from old systems without becoming an old system.

## Two-Persona Standard

Trader standard:

- prove the setup had edge in the right market and session
- identify why the trade was taken, where it was invalid, and how profit was protected
- reject claims that do not show receipts, replay results, or closed-trade evidence

Bot-builder standard:

- convert every idea into deterministic fields and checks
- keep strategy logic inside strategy packs
- keep broker execution generic and practice-only
- never import old repo runtime code directly

## Evidence Grades

`A - verified receipt`

- closed trade or replay window has symbol, direction, timestamp, strategy, and P&L
- source file is known and reproducible
- can be compared with the April 14 or V1C002 evidence set

`B - structured candidate`

- transcript or old doc gives clear rules
- rules can be mapped to deterministic detectors
- still needs replay and paper receipts

`C - research only`

- concept is useful but lacks data, detectors, or OANDA relevance
- can guide later design but cannot trade

`D - reject`

- no receipt
- vague profit claim
- mixed broker logic
- impossible to reproduce cleanly

## Promotion Path

1. Source inventory
2. Deduplication by path and archive hash
3. Trade receipt extraction
4. Setup ingredient extraction
5. Deterministic detector mapping
6. Strategy-pack entry
7. Replay against known windows
8. OANDA practice paper run
9. Only then consider stronger activation

## Contamination Rules

- Legacy folders stay read-only.
- Old code is evidence, not runtime.
- No Coinbase, options, equities, futures, or multi-broker execution in this OANDA bot.
- Transcript rules cannot call broker code.
- Every rule must pass through a strategy pack.
- Every strategy pack must be replayed and paper-tested.

## Current Audit Command

```bash
PYTHONPATH=src python3 ops/evidence_audit.py
```

Outputs:

- `analysis/evidence_audit/legacy_evidence_audit.json`
- `analysis/evidence_audit/legacy_evidence_audit.md`

## What We Are Trying To Replicate

The current best thesis is:

- session-shaped trading, not always-on trading
- London ramp and early New York, especially 3 AM to 9 AM ET
- momentum and continuation as the main money lane
- controlled scalp only when receipts prove it helps
- seven-pair OANDA field, with pair and slot controls
- strict confidence, vote, spread, range, and false-break filters
- stop/target/profit-lock behavior that is explainable and testable

## What Comes Next

Use the audit output to build a ledger of:

- which old source produced the trade
- which setup ingredient mattered
- which detector would reproduce it
- which strategy pack owns it
- whether replay and paper receipts confirm it

Anything that cannot survive that ledger does not get promoted.
