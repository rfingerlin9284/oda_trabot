from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from oda_trabot import PHASE1_CONTRACT

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = REPO_ROOT / "state"
LOG_FILE = REPO_ROOT / "logs" / "runtime.log"
STATUS_FILE = STATE_DIR / "last_runtime_status.json"
RUNTIME_STATE_FILE = STATE_DIR / "runtime_state.json"
RUNTIME_ENV_FILE = STATE_DIR / "runtime.env"
PHASE_FILE = REPO_ROOT / "docs" / "PHASE_STATUS.md"
SERVICE_SCRIPT = REPO_ROOT / "ops" / "service_control.sh"
SERVICE_NAME = "oda_trabot.service"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "main"
    if mode == "main":
        watch_main()
        return
    if mode == "why":
        watch_why()
        return
    if mode == "settings":
        watch_settings()
        return
    if mode == "commands":
        commands_menu()
        return
    if mode == "rick":
        ask_rick()
        return
    raise SystemExit(f"Unknown desktop console mode: {mode}")


def watch_main() -> None:
    while True:
        clear_screen()
        status = load_json(STATUS_FILE)
        runtime_state = load_json(RUNTIME_STATE_FILE)
        recent_tail = load_tail(LOG_FILE, 14)
        print("ODA_TRABOT MAIN BOARD")
        print()
        print(f"Service: {service_state_plain()}")
        print(f"Mode: {mode_plain()}")
        print(f"Last update: {status.get('generated_at_et', 'unknown')}")
        print(f"Pairs watched: {', '.join(PHASE1_CONTRACT.trading_pairs)}")
        print()
        print("What the bot is doing right now:")
        print(indent_block(status.get("cycle_summary", "No runtime status yet.")))
        print()
        open_positions = status.get("open_positions", [])
        if open_positions:
            print("Open broker trades:")
            for trade in open_positions:
                print(
                    f"- {trade.get('pair')} {trade.get('direction')} {trade.get('units'):,} units | "
                    f"entry {trade.get('entry_price')} | open P&L {trade.get('unrealized_pl')}"
                )
        else:
            print("Open broker trades: none")
        print()
        active_trades = runtime_state.get("active_trades", [])
        print(f"Bot-managed trades in memory: {len(active_trades)}")
        if active_trades:
            for record in active_trades:
                print(
                    f"- {record.get('pair')} {record.get('direction')} via {record.get('workflow')} | "
                    f"stop {record.get('stop_price')} | target {record.get('target_price')} | "
                    f"last action {record.get('last_action')}"
                )
        print()
        management_actions = status.get("management_actions", [])
        if management_actions:
            print("Latest management actions:")
            for action in management_actions:
                print(
                    f"- {action.get('pair')} {action.get('action')}: "
                    f"{action.get('reason')} -> {action.get('outcome')}"
                )
        else:
            print("Latest management actions: none this cycle")
        print()
        print("LIVE TERMINAL TAIL")
        print()
        if recent_tail:
            for line in recent_tail:
                print(line)
        else:
            print("No live log lines yet.")
        print()
        print("This window self-refreshes every 5 seconds.")
        print("Press Ctrl+C to close this window.")
        time.sleep(5)


def watch_why() -> None:
    while True:
        clear_screen()
        status = load_json(STATUS_FILE)
        runtime_state = load_json(RUNTIME_STATE_FILE)
        print("WHY THIS TRADE")
        print()
        active_trades = runtime_state.get("active_trades", [])
        planned = status.get("planned_trades", [])
        if active_trades:
            print("Why the current trades exist:")
            for record in active_trades:
                rationale = ", ".join(record.get("rationale", [])) or "No saved rationale text."
                print(f"- {record.get('pair')} {record.get('direction')} using {record.get('workflow')}")
                print(f"  Confidence: {record.get('confidence')} | Votes: {record.get('votes')}")
                print(f"  Reason: {rationale}")
                print(f"  Plan: stop {record.get('stop_price')} | target {record.get('target_price')}")
                print(f"  Last action: {record.get('last_action')}")
                print()
        elif planned:
            print("No trade is open yet, but these were the latest planned ideas:")
            for preview in planned:
                print(
                    f"- {preview.get('pair')} {preview.get('direction')} {preview.get('units'):,} units | "
                    f"entry {preview.get('entry_price')} | stop {preview.get('stop_price')} | "
                    f"target {preview.get('target_price')} | profile {preview.get('profile_name')}"
                )
        else:
            print("No active bot-managed trades right now.")
            print()
            print("Plain-English reason:")
            print(indent_block(status.get("cycle_summary", "No runtime status yet.")))
        print()
        print("Press Ctrl+C to close this window.")
        time.sleep(5)


def watch_settings() -> None:
    while True:
        clear_screen()
        runtime_env = load_env(RUNTIME_ENV_FILE)
        status = load_json(STATUS_FILE)
        print("BOT SETTINGS + SAFETY")
        print()
        print(f"Service: {service_state_plain()}")
        print(f"Armed for paper orders: {'YES' if status.get('armed') else 'NO'}")
        print(f"Runtime loop seconds: {runtime_env.get('ODA_TRABOT_LOOP_SECONDS', 'unknown')}")
        print()
        print("Locked Phase 1 contract:")
        print(f"- Practice only: YES")
        print(f"- Pairs: {', '.join(PHASE1_CONTRACT.trading_pairs)}")
        print(f"- Min votes: {PHASE1_CONTRACT.min_votes}")
        print(f"- Confidence floor: {PHASE1_CONTRACT.min_signal_confidence:.2f}")
        print(f"- Max open positions: {PHASE1_CONTRACT.max_positions}")
        print(f"- Max new trades per cycle: {PHASE1_CONTRACT.max_new_trades_per_cycle}")
        print(f"- Base units: {PHASE1_CONTRACT.base_units:,}")
        print()
        print("Allowed workflows by session:")
        for session in PHASE1_CONTRACT.sessions:
            allowed = ", ".join(session.workflows) if session.workflows else "none"
            print(f"- {session.name.value}: {'ON' if session.enabled else 'OFF'} | {allowed}")
        print()
        print("Transcript strategy coverage right now:")
        for line in transcript_coverage_lines():
            print(f"- {line}")
        print()
        print("Live market data actually used:")
        for line in live_market_data_lines():
            print(f"- {line}")
        print()
        print("Last runtime status:")
        print(indent_block(status.get("cycle_summary", "No runtime status yet.")))
        print()
        print("Press Ctrl+C to close this window.")
        time.sleep(10)


def commands_menu() -> None:
    while True:
        clear_screen()
        print("BOT COMMANDS")
        print()
        print("1. Show bot status")
        print("2. Start preview mode")
        print("3. Start live paper mode")
        print("4. Restart preview mode")
        print("5. Restart live paper mode")
        print("6. Stop bot")
        print("7. Run broker probe")
        print("8. Run one live cycle preview")
        print("9. Show last 40 log lines")
        print("Q. Quit")
        print()
        choice = input("Choose one task: ").strip().lower()
        if choice == "1":
            run_and_pause([str(SERVICE_SCRIPT), "status"])
        elif choice == "2":
            run_and_pause([str(SERVICE_SCRIPT), "start-preview"])
        elif choice == "3":
            run_and_pause([str(SERVICE_SCRIPT), "start-paper"])
        elif choice == "4":
            run_and_pause([str(SERVICE_SCRIPT), "restart-preview"])
        elif choice == "5":
            run_and_pause([str(SERVICE_SCRIPT), "restart-paper"])
        elif choice == "6":
            run_and_pause([str(SERVICE_SCRIPT), "stop"])
        elif choice == "7":
            run_and_pause(["python3", "ops/oanda_probe.py"])
        elif choice == "8":
            run_and_pause(["python3", "ops/oanda_live_cycle.py"])
        elif choice == "9":
            run_and_pause(["bash", "-lc", f"tail -n 40 {LOG_FILE}"])
        elif choice == "q":
            return


def ask_rick() -> None:
    print("ASK RICK")
    print()
    print("Type a plain-English question. Examples:")
    print("- is the bot running")
    print("- what pairs is it watching")
    print("- why are there no trades")
    print("- what mode is it in")
    print("- open trades")
    print("- settings")
    print("- commands")
    print("- quit")
    print()
    while True:
        question = input("You: ").strip()
        if not question:
            continue
        lowered = question.lower()
        if lowered in {"quit", "exit", "q"}:
            return
        print()
        print(f"Rick: {answer_rick(lowered)}")
        print()


def answer_rick(lowered: str) -> str:
    status = load_json(STATUS_FILE)
    runtime_state = load_json(RUNTIME_STATE_FILE)
    if "running" in lowered or "status" in lowered:
        return f"The bot service is {service_state_plain().lower()}. Mode is {mode_plain().lower()}."
    if "pair" in lowered or "watch" in lowered or "scan" in lowered:
        return f"It is watching these 7 pairs: {', '.join(PHASE1_CONTRACT.trading_pairs)}."
    if "mode" in lowered or "armed" in lowered:
        return f"It is currently {'armed for live paper orders' if status.get('armed') else 'in preview mode only'}."
    if "open trade" in lowered or "position" in lowered:
        open_positions = status.get("open_positions", [])
        if not open_positions:
            return "There are no open broker trades right now."
        return "Open trades: " + "; ".join(
            f"{trade.get('pair')} {trade.get('direction')} {trade.get('units'):,} units"
            for trade in open_positions
        )
    if "why" in lowered and "no trade" in lowered:
        return status.get("cycle_summary", "I do not have a runtime summary yet.")
    if "setting" in lowered or "safety" in lowered:
        return (
            f"Practice only is ON. Min votes are {PHASE1_CONTRACT.min_votes}. "
            f"Confidence floor is {PHASE1_CONTRACT.min_signal_confidence:.2f}. "
            f"Max positions are {PHASE1_CONTRACT.max_positions}."
        )
    if "transcript" in lowered or "indicator" in lowered or "strategy" in lowered:
        return "Transcript truth: LIVE now = continuation, second_chance, fashionably_late, scalp. PARTIAL support = session router, scalp math, sizing. OFF right now = liquidity sweep, order block sniper, range bounce, VWAP suite, prop desk scalps, swing ladder."
    if "command" in lowered or "task" in lowered:
        return "Use the Commands icon for start, stop, restart, probe, live cycle preview, and log viewing."
    if "trade memory" in lowered or "state" in lowered:
        return f"The bot is tracking {len(runtime_state.get('active_trades', []))} active managed trades in its own runtime state file."
    return "I can answer status, pairs, mode, open trades, why no trades, settings, commands, or trade state."


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value.strip()
    return values


def load_tail(path: Path, lines: int) -> list[str]:
    if not path.exists():
        return []
    try:
        content = path.read_text(errors="replace").splitlines()
        return content[-lines:]
    except Exception:
        return []


def service_state_plain() -> str:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", SERVICE_NAME],
        capture_output=True,
        text=True,
        check=False,
    )
    state = result.stdout.strip() or "unknown"
    if state == "active":
        return "RUNNING"
    if state == "inactive":
        return "STOPPED"
    return state.upper()


def mode_plain() -> str:
    runtime_env = load_env(RUNTIME_ENV_FILE)
    return "LIVE PAPER" if runtime_env.get("ODA_TRABOT_ALLOW_PAPER_ORDERS", "").upper() == "YES" else "PREVIEW ONLY"


def transcript_coverage_lines() -> tuple[str, ...]:
    return (
        "continuation: LIVE but simplified. Uses trend, momentum, breakout, and retest scores from live M15 candles.",
        "second_chance: LIVE but simplified. Uses trend, retest, momentum, and breakout scores.",
        "fashionably_late: LIVE but simplified. Uses trend, retest, momentum, and breakout scores.",
        "scalp: LIVE but simplified. Uses scalp pressure, momentum, spread, and volatility scores.",
        "session killzone filter: PARTIAL. London, overlap, and New York day window are enforced, but detailed killzone weighting is not wired.",
        "workflow router / top-down bias: PARTIAL. Session routing is live, but full Daily-H4-H1-M15 top-down bias stack is not wired.",
        "scalp math rules: PARTIAL. Vote floor, confidence floor, stop, target, and slot gating exist, but not every transcript math rule is wired.",
        "position sizing engine: PARTIAL. Base size, max positions, and per-trade planning exist, but no full adaptive compounding engine yet.",
        "liquidity sweep entry: OFF. No PDH/PDL sweep map, FVG entry, or MSS retracement logic in the live bot yet.",
        "order block sniper: OFF. No H1-H4 order block detection or lower-timeframe OB refinement is wired yet.",
        "range bounce and breakout: OFF. No sideways regime range strategy is wired in the live bot yet.",
        "VWAP strategy suite: OFF. No VWAP calculation or VWAP-based trigger is wired in the live bot yet.",
        "prop desk scalps: OFF. No rubber band, big dog, above the clouds, or other transcript-specific prop desk patterns are wired yet.",
        "swing trade ladder: OFF. No swing ladder workflow is wired into the live bot yet.",
        "market news or AI hive confidence: OFF. No transcript-driven news helper, sentiment, or LLM weighting is active.",
    )


def live_market_data_lines() -> tuple[str, ...]:
    return (
        "all 7 phase-1 pairs are scanned every cycle",
        "live OANDA spread for each pair is used",
        "40 recent M15 candles per pair are used",
        "trend_score is built from directional move across the last 12 closes",
        "momentum_score is built from the last 4 closes",
        "breakout_score is built from the recent 8-bar high-low range",
        "retest_score is built from distance to the recent 8-bar average close",
        "scalp_score is built from the latest bar range versus average range",
        "volatility_score is built from average candle range in pip terms",
        "no Daily, H4, H1, VWAP, volume, tape, FVG, or order-book data is in the live confidence score yet",
    )


def run_and_pause(command: list[str]) -> None:
    clear_screen()
    print("Running task...")
    print()
    subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    print()
    input("Press Enter to return to the command menu...")


def indent_block(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines()) if text else "  none"


def clear_screen() -> None:
    os.system("clear")


if __name__ == "__main__":
    main()
