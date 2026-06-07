# Frozen ODA_TRABOT Two-Cartridge Backup

Created ET: 2026-06-07T14:14:54-04:00
Source repo: /home/rfing/ODA_TRABOT
Purpose: frozen GitHub-ready backup of the current clean OANDA practice bot repo.

Included: Git-eligible source, configs, docs, tests, ops, analysis, fixtures, and audit reports.
Excluded by repo .gitignore: state/, live runtime env/state, runtime logs, pycache, virtualenvs, and local .env files.

Active cartridges:
- april14_momentum_3am_9am: 3:00 AM-8:30:59 AM ET, momentum only.
- post_9am_ema_fib_momentum_continuation: 9:00 AM-11:29:59 AM ET, continuation only.

Runtime routing: ODA_TRABOT_CARTRIDGE_ROUTING=auto.
