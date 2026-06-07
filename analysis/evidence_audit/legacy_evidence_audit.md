# Legacy Evidence Audit

Generated UTC: `2026-06-07T01:01:54.503582+00:00`

## Scope

- Legacy folders are read-only evidence.
- Transcript rules enter runtime only through strategy packs.
- Old repo code is never imported directly into the clean bot.
- Live-money activation is outside this audit; OANDA practice only.

## TurboScribe Coverage

- Zip files scanned: `374`
- TurboScribe-related zip hits: `78`
- Direct TurboScribe-named zip hits: `73`
- Unique archive hashes: `9`
- Indexed transcript/docs rows: `102`

Top transcript evidence terms:
- `trading`: `79`
- `trade`: `76`
- `strategy`: `41`
- `sma`: `34`
- `ema`: `26`
- `order`: `25`
- `risk`: `23`
- `scalp`: `15`
- `scalping`: `13`
- `forex`: `13`
- `range`: `9`
- `liquidity`: `8`

## Verified Trade Sources

- `april14_baseline`: best `Peak giveback lock: arm +$350, trip -$175 from peak` at `$681.30` across `5` windows
  - P&L by strategy: `{'momentum': 1895.46, 'scalp': 20.11}`
  - P&L by symbol: `{'USD_CHF': 1070.6000000000001, 'GBP_USD': 828.0, 'NZD_USD': 522.0, 'EUR_USD': 459.0, 'USD_CAD': 225.79, 'AUD_USD': 126.75, 'USD_JPY': -112.74999999999997}`
- `v1c002_challenger`: best `Current Live Logic` at `$338.41` across `4` windows
  - P&L by strategy: `{'momentum': 735.09, 'scalp': 100.22999999999999}`
  - P&L by symbol: `{'GBP_USD': 987.0, 'EUR_USD': 432.0, 'USD_CAD': 140.14000000000001, 'AUD_USD': 111.5}`

## What Can Be Promoted

Promote only evidence that has all of these:

1. A source file path and hash or deterministic source id.
2. A closed-trade receipt or replay window with P&L, symbol, session, and strategy.
3. A plain-English rule that maps to a deterministic detector.
4. A strategy-pack entry, not broker-code edits.
5. A replay receipt against the known edge window.
6. A paper-trading receipt before any stronger activation.

## Current Replication Thesis

- Keep the clean bot session-shaped.
- Prioritize London and early New York, especially 3 AM to 9 AM ET.
- Treat momentum/continuation as the primary money lane.
- Treat scalp as a narrow helper unless receipts prove it is carrying expectancy.
- Add top-down bias, 9 EMA first-touch quality, false-break filters, and range/chop filters through strategy packs.
- Keep order block, liquidity sweep, FVG, and orderflow logic disabled until deterministic detectors and replay data exist.

## Legacy Candidate File Queue

Candidate files listed: `350`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/autonomy_state.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/engine_heartbeat.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/narration.jsonl`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/free_market_news_snapshot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/pair_stats.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/session_fingerprint_lock.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/daily_risk_state.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/autonomy_events.jsonl`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/boot_history.jsonl`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/session_guard_status.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/index.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_012515__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/LAST_USED/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_012515__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/LAST_USED/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/logs/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_003827__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_003827__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_003316__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_003316__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_002805__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_002805__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_002254__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260603_002254__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_233703__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_233703__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_233152__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_233152__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_232642__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_232642__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_232131__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_232131__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_223530__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_223530__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_223019__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_223019__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_222459__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/backups/restore_points/RECENT_VERSIONS/20260602_222459__OANDA_V1C002_FREQ_PLUS_APRIL14_ENTRY_EXIT_20260508/active_boot.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/STATE_SNAPSHOT/production_lock_manifest.json`
- `/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/STATE_SNAPSHOT/production_identity.json`
