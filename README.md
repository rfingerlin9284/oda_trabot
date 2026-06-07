# ODA_TRABOT

This is the new clean rebuild repo for the OANDA practice bot.

Purpose:
- rebuild a simple autonomous bot from historically proven edge
- stop patching legacy repos
- keep the old repo family as read-only evidence only

What this repo is allowed to be:
- OANDA only
- practice only
- simple
- readable
- testable
- evidence-first

What this repo is not allowed to be:
- Coinbase
- multi-broker
- Phoenix swarm
- ML hive
- news bot
- legacy patch pile

Starting point:
- use the April 14 family as the core evidence source
- use later challenger receipts only when they clearly improved the edge

Main blueprint:
- see `docs/REBUILD_BLUEPRINT.md`

Strategy swapping:
- see `docs/STRATEGY_PACKS.md`
- primary active pack: `april14_momentum_3am_9am`
- set `ODA_TRABOT_STRATEGY_PACK=turboscribe_phase1` to use the TurboScribe cartridge
- unset it to fall back to the legacy Phase 1 cartridge
