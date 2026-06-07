from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_ROOT = REPO_ROOT / "ops"
if str(OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(OPS_ROOT))

from live_paper_outside_window_audit import parse_json_line, parse_timestamp  # noqa: E402


LIFECYCLE_JSON = REPO_ROOT / "analysis" / "strategy_lifecycle_audit" / "closed_trade_lifecycle_results.json"
OUTPUT_DIR = REPO_ROOT / "analysis" / "protection_failure_audit"
DOCS_REPORT = REPO_ROOT / "docs" / "PROTECTION_FAILURE_AUDIT_PLAIN_ENGLISH_20260607.md"


@dataclass(frozen=True)
class ProtectionResult:
    trade_id: str
    symbol: str
    strategy_family: str
    outcome: str
    pnl_usd: float
    close_timestamp_et: str
    close_reason: str
    max_tracked_pnl_usd: float | None
    max_tracked_pips: float | None
    max_rr_ratio: float | None
    initial_sl_present: bool
    initial_tp_present: bool
    oco_placed: bool
    position_synced: bool
    position_sync_sl_present: bool
    trail_candidate_count: int
    trail_current_sl_samples: int
    locked_trail_samples: int
    green_lock_events: int
    trade_stop_update_events: int
    stop_moved_events: int
    any_trailing_or_lock_applied: bool
    secondary_failure_class: str
    secondary_failure_detail: str
    source_path: str


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lifecycle_rows = json.loads(LIFECYCLE_JSON.read_text())
    clean_rows = [row for row in lifecycle_rows if row.get("clean_for_strategy_mining")]
    target_by_path: dict[str, set[str]] = defaultdict(set)
    for row in clean_rows:
        target_by_path[row["source_path"]].add(str(row["trade_id"]))

    event_context = scan_protection_events(target_by_path)
    results = [build_result(row, event_context.get((row["source_path"], str(row["trade_id"])), Counter())) for row in clean_rows]
    write_json(OUTPUT_DIR / "protection_failure_results.json", [asdict(result) for result in results])
    write_csv(OUTPUT_DIR / "protection_failure_results.csv", results)
    write_report(DOCS_REPORT, results, lifecycle_rows)
    write_report(OUTPUT_DIR / "protection_failure_audit.md", results, lifecycle_rows)
    print(f"Protection results: {len(results)}")
    print(f"Losses: {sum(1 for result in results if result.outcome == 'LOSS')}")
    print(f"Report: {DOCS_REPORT}")
    return 0


def scan_protection_events(target_by_path: dict[str, set[str]]) -> dict[tuple[str, str], Counter[str]]:
    contexts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for source_path, trade_ids in target_by_path.items():
        path = Path(source_path)
        if not path.exists():
            continue
        with path.open("r", errors="replace") as handle:
            for line in handle:
                obj = parse_json_line(line)
                if not obj:
                    continue
                details = obj.get("details") if isinstance(obj.get("details"), dict) else {}
                trade_id = str(details.get("trade_id") or details.get("close_trade_id") or obj.get("trade_id") or "").strip()
                if trade_id not in trade_ids:
                    continue
                event_type = str(obj.get("event_type") or obj.get("kind") or obj.get("type") or "")
                counter = contexts[(source_path, trade_id)]
                counter[f"event:{event_type}"] += 1
                if event_type == "OCO_PLACED":
                    counter["oco_placed"] += 1
                    if details.get("stop_loss") not in {None, ""}:
                        counter["oco_stop_loss_present"] += 1
                    if details.get("take_profit") not in {None, ""}:
                        counter["oco_take_profit_present"] += 1
                if event_type == "POSITION_SYNCED":
                    counter["position_synced"] += 1
                    if details.get("sl") not in {None, ""}:
                        counter["position_sync_sl_present"] += 1
                if event_type == "TRAIL_CANDIDATE":
                    counter["trail_candidate"] += 1
                    if details.get("current_sl") not in {None, ""}:
                        counter["trail_current_sl_present"] += 1
                    if bool(details.get("is_locked")):
                        counter["locked_trail_sample"] += 1
                if event_type == "GREEN_LOCK_ENFORCED":
                    counter["green_lock_event"] += 1
                    old_sl = details.get("old_sl")
                    new_sl = details.get("new_sl")
                    if old_sl not in {None, ""} and new_sl not in {None, ""} and str(old_sl) != str(new_sl):
                        counter["stop_moved_event"] += 1
                if event_type == "TRADE_STOP_UPDATED":
                    counter["trade_stop_updated"] += 1
                    old_sl = details.get("old_sl")
                    new_sl = details.get("new_sl")
                    if old_sl not in {None, ""} and new_sl not in {None, ""} and str(old_sl) != str(new_sl):
                        counter["stop_moved_event"] += 1
    return contexts


def build_result(row: dict[str, Any], context: Counter[str]) -> ProtectionResult:
    initial_sl_present = row.get("stop_loss") is not None or context["oco_stop_loss_present"] > 0
    initial_tp_present = row.get("take_profit") is not None or context["oco_take_profit_present"] > 0
    oco_placed = context["oco_placed"] > 0 or (initial_sl_present and initial_tp_present)
    position_synced = context["position_synced"] > 0
    position_sync_sl_present = context["position_sync_sl_present"] > 0
    trail_candidate_count = int(row.get("trail_samples") or context["trail_candidate"])
    trail_current_sl_samples = context["trail_current_sl_present"]
    locked_trail_samples = context["locked_trail_sample"]
    green_lock_events = context["green_lock_event"]
    trade_stop_update_events = context["trade_stop_updated"]
    stop_moved_events = context["stop_moved_event"]
    any_trailing_or_lock_applied = locked_trail_samples > 0 or green_lock_events > 0 or trade_stop_update_events > 0 or stop_moved_events > 0
    failure_class, detail = classify_secondary_failure(
        row=row,
        initial_sl_present=initial_sl_present,
        initial_tp_present=initial_tp_present,
        oco_placed=oco_placed,
        trail_candidate_count=trail_candidate_count,
        trail_current_sl_samples=trail_current_sl_samples,
        any_trailing_or_lock_applied=any_trailing_or_lock_applied,
        locked_trail_samples=locked_trail_samples,
        green_lock_events=green_lock_events,
        trade_stop_update_events=trade_stop_update_events,
        stop_moved_events=stop_moved_events,
    )
    return ProtectionResult(
        trade_id=str(row["trade_id"]),
        symbol=str(row["symbol"]),
        strategy_family=str(row["strategy_family"]),
        outcome=str(row["outcome"]),
        pnl_usd=float(row["pnl_usd"]),
        close_timestamp_et=str(row["close_timestamp_et"]),
        close_reason=str(row.get("close_reason") or ""),
        max_tracked_pnl_usd=row.get("max_tracked_pnl_usd"),
        max_tracked_pips=row.get("max_tracked_pips"),
        max_rr_ratio=row.get("max_rr_ratio"),
        initial_sl_present=initial_sl_present,
        initial_tp_present=initial_tp_present,
        oco_placed=oco_placed,
        position_synced=position_synced,
        position_sync_sl_present=position_sync_sl_present,
        trail_candidate_count=trail_candidate_count,
        trail_current_sl_samples=trail_current_sl_samples,
        locked_trail_samples=locked_trail_samples,
        green_lock_events=green_lock_events,
        trade_stop_update_events=trade_stop_update_events,
        stop_moved_events=stop_moved_events,
        any_trailing_or_lock_applied=any_trailing_or_lock_applied,
        secondary_failure_class=failure_class,
        secondary_failure_detail=detail,
        source_path=str(row["source_path"]),
    )


def classify_secondary_failure(
    *,
    row: dict[str, Any],
    initial_sl_present: bool,
    initial_tp_present: bool,
    oco_placed: bool,
    trail_candidate_count: int,
    trail_current_sl_samples: int,
    any_trailing_or_lock_applied: bool,
    locked_trail_samples: int,
    green_lock_events: int,
    trade_stop_update_events: int,
    stop_moved_events: int,
) -> tuple[str, str]:
    outcome = str(row["outcome"])
    pnl = float(row["pnl_usd"])
    max_pnl = row.get("max_tracked_pnl_usd")
    max_pips = row.get("max_tracked_pips")
    max_rr = row.get("max_rr_ratio")

    if not oco_placed or not initial_sl_present or not initial_tp_present:
        missing = []
        if not oco_placed:
            missing.append("OCO")
        if not initial_sl_present:
            missing.append("SL")
        if not initial_tp_present:
            missing.append("TP")
        return "missing_primary_protection", f"Missing logged {'/'.join(missing)} evidence."

    if outcome != "LOSS":
        if any_trailing_or_lock_applied:
            return "winner_with_secondary_protection", "Winning trade had SL/TP and some trailing or lock evidence."
        return "winner_static_sl_tp_only", "Winning trade had SL/TP but no logged trailing/green-lock engagement."

    if trail_candidate_count == 0:
        return "loss_no_trailing_manager_samples", "Loss had SL/TP, but no logged TRAIL_CANDIDATE manager samples."
    if trail_current_sl_samples == 0:
        return "loss_manager_saw_trade_but_no_current_sl", "Manager sampled the trade, but no current_sl was logged."
    if max_pnl is not None and max_pnl >= 5.0 and not any_trailing_or_lock_applied:
        return (
            "edge_present_but_no_trailing_or_lock",
            f"Trade reached about +${max_pnl:.2f}, then closed at ${pnl:.2f}; no green-lock, stop update, or locked trailing sample was logged.",
        )
    if max_pnl is not None and max_pnl >= 5.0 and any_trailing_or_lock_applied:
        return (
            "edge_present_but_protection_did_not_hold",
            f"Trade reached about +${max_pnl:.2f}; protection evidence exists "
            f"(green_lock={green_lock_events}, stop_update={trade_stop_update_events}, locked_samples={locked_trail_samples}, stop_moves={stop_moved_events}) "
            f"but final close was ${pnl:.2f}.",
        )
    if max_pnl is not None and max_pnl > 0:
        return "small_green_not_enough_for_lock", f"Trade only reached about +${max_pnl:.2f}; likely below meaningful lock threshold."
    if max_pips is not None and max_pips > 0:
        return "small_pip_green_not_enough_for_lock", f"Trade only reached about +{max_pips:.2f} pips; likely below meaningful lock threshold."
    if max_rr is not None and max_rr > 0:
        return "small_rr_green_not_enough_for_lock", f"Trade only reached about {max_rr:.2f}R; likely below meaningful lock threshold."
    return "entry_failed_before_secondary_could_help", "SL/TP and manager samples existed, but no favorable excursion was logged before the loss."


def write_report(path: Path, results: list[ProtectionResult], lifecycle_rows: list[dict[str, Any]]) -> None:
    losses = [result for result in results if result.outcome == "LOSS"]
    wins = [result for result in results if result.outcome == "WIN"]
    all_losses = [row for row in lifecycle_rows if row.get("outcome") == "LOSS"]
    counts = Counter(result.secondary_failure_class for result in losses)
    by_strategy: dict[str, list[ProtectionResult]] = defaultdict(list)
    for result in losses:
        by_strategy[result.strategy_family].append(result)
    direct_kill = [
        "edge_present_but_no_trailing_or_lock",
        "edge_present_but_protection_did_not_hold",
        "loss_no_trailing_manager_samples",
        "loss_manager_saw_trade_but_no_current_sl",
        "missing_primary_protection",
    ]
    killed = [result for result in losses if result.secondary_failure_class in direct_kill]
    lines = [
        "# Protection Failure Audit - Plain English",
        "",
        "Date: June 7, 2026",
        "",
        "## Operator Answer",
        "",
        "This audit checks whether losses were caused by the strategy being bad, or by secondary protection failures such as missing SL, missing TP, missing trailing stop, no green lock, or trade management failing after the trade had already gone green.",
        "",
        "## Direct Finding",
        "",
        f"- Clean trades checked: {len(results)}",
        f"- Wins checked: {len(wins)}",
        f"- Losses checked: {len(losses)}",
        f"- Losses where secondary protection likely killed or failed to preserve edge: {len(killed)}",
        f"- Losses with missing logged SL/TP/OCO in the clean high-confidence set: {counts.get('missing_primary_protection', 0)}",
        "",
        "Plain English: in the clean high-confidence OANDA practice receipts, the initial OCO/SL/TP was generally present. The bigger failure was not usually missing initial SL/TP. The bigger failure was that trades went green and then the secondary protection layer did not lock, trail, or hold the gain.",
        "",
        "## Broader SL/TP Field Check",
        "",
        "This looser check includes lower-confidence/unlinked rows too. It is useful for spotting logging or protection concerns, but it is not the clean cartridge-mining evidence set.",
        "",
        f"- All closed results checked: {len(lifecycle_rows)}",
        f"- All losses checked: {len(all_losses)}",
        f"- Rows missing logged stop-loss field: {sum(1 for row in lifecycle_rows if row.get('stop_loss') is None)}",
        f"- Rows missing logged take-profit field: {sum(1 for row in lifecycle_rows if row.get('take_profit') is None)}",
        f"- Losing rows missing logged stop-loss field: {sum(1 for row in all_losses if row.get('stop_loss') is None)}",
        f"- Losing rows missing logged take-profit field: {sum(1 for row in all_losses if row.get('take_profit') is None)}",
        "",
        "Plain English: there were some lower-confidence rows with missing SL/TP fields, but the clean broker-linked OCO rows did not show missing initial SL/TP. The bigger proven failure in the clean evidence is missing or inactive trailing/green-lock after the trade had already gone favorable.",
        "",
        "## Losses By Protection Failure Type",
        "",
    ]
    lines.extend(render_class_table(losses))
    lines.extend(
        [
            "",
            "## Protection Failure By Strategy",
            "",
        ]
    )
    lines.extend(render_strategy_table(by_strategy))
    lines.extend(
        [
            "",
            "## Biggest Edge-Giveback Losses",
            "",
        ]
    )
    edge_losses = [
        result
        for result in losses
        if result.secondary_failure_class in {"edge_present_but_no_trailing_or_lock", "edge_present_but_protection_did_not_hold"}
    ]
    lines.extend(render_trade_table(sorted(edge_losses, key=lambda item: abs((item.max_tracked_pnl_usd or 0) - item.pnl_usd), reverse=True)[:35]))
    lines.extend(
        [
            "",
            "## What This Means For The Bot",
            "",
            "Do not just ask whether a strategy label won or lost.",
            "",
            "For many losses, the better question is: did the trade first show edge, and did the protection layer fail to keep it?",
            "",
            "The evidence says yes for a meaningful subset. That means the next cartridge work needs a protection contract, not just entry logic:",
            "",
            "- every paper order must have broker-visible OCO",
            "- every open trade must sync broker SL",
            "- every open trade must have manager samples",
            "- once a trade reaches a defined green threshold, it must lock or trail",
            "- if lock/trail fails, the bot must log and flatten or block new entries",
            "- any strategy cartridge without verified SL/TP/TS behavior stays disabled",
            "",
            "## Output Files",
            "",
            f"- CSV: `{OUTPUT_DIR / 'protection_failure_results.csv'}`",
            f"- JSON: `{OUTPUT_DIR / 'protection_failure_results.json'}`",
            f"- Technical report: `{OUTPUT_DIR / 'protection_failure_audit.md'}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def render_class_table(losses: list[ProtectionResult]) -> list[str]:
    if not losses:
        return ["No losses found."]
    lines = [
        "| Failure Type | Count | P&L Impact | Plain-English Meaning |",
        "| --- | ---: | ---: | --- |",
    ]
    meanings = {
        "edge_present_but_no_trailing_or_lock": "Trade went green, then red, with no logged lock/trailing application.",
        "edge_present_but_protection_did_not_hold": "Lock/trailing evidence exists, but it still failed to preserve the trade.",
        "loss_no_trailing_manager_samples": "SL/TP existed, but trade manager did not log trailing samples.",
        "loss_manager_saw_trade_but_no_current_sl": "Manager saw the trade but did not log current stop-loss state.",
        "missing_primary_protection": "Missing logged OCO/SL/TP evidence.",
        "small_green_not_enough_for_lock": "Trade barely went green; not enough edge to blame trailing.",
        "small_pip_green_not_enough_for_lock": "Trade barely moved in pips; not enough edge to blame trailing.",
        "small_rr_green_not_enough_for_lock": "Trade barely moved in R; not enough edge to blame trailing.",
        "entry_failed_before_secondary_could_help": "Trade never showed favorable excursion; entry/setup failed first.",
    }
    for failure_class, count in Counter(result.secondary_failure_class for result in losses).most_common():
        pnl = sum(result.pnl_usd for result in losses if result.secondary_failure_class == failure_class)
        lines.append(f"| {md(failure_class)} | {count} | {pnl:.2f} | {md(meanings.get(failure_class, 'Manual review needed.'))} |")
    return lines


def render_strategy_table(by_strategy: dict[str, list[ProtectionResult]]) -> list[str]:
    if not by_strategy:
        return ["No strategy losses found."]
    lines = [
        "| Strategy | Losses | Main Protection Failure | Edge-Present Protection Failures | Missing SL/TP/OCO |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    direct = {"edge_present_but_no_trailing_or_lock", "edge_present_but_protection_did_not_hold"}
    for strategy, items in sorted(by_strategy.items(), key=lambda pair: len(pair[1]), reverse=True):
        counts = Counter(item.secondary_failure_class for item in items)
        main = counts.most_common(1)[0][0]
        edge_failures = sum(1 for item in items if item.secondary_failure_class in direct)
        missing = counts.get("missing_primary_protection", 0)
        lines.append(f"| {md(strategy)} | {len(items)} | {md(main)} | {edge_failures} | {missing} |")
    return lines


def render_trade_table(results: list[ProtectionResult]) -> list[str]:
    if not results:
        return ["No edge-giveback protection failures found."]
    lines = [
        "| Close ET | Strategy | Pair | Final P&L | Max P&L | Green Lock | Stop Updates | Locked Samples | Failure |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in results:
        max_pnl = "" if item.max_tracked_pnl_usd is None else f"{item.max_tracked_pnl_usd:.2f}"
        lines.append(
            f"| {md(item.close_timestamp_et[:16])} | {md(item.strategy_family)} | {md(item.symbol)} | "
            f"{item.pnl_usd:.2f} | {max_pnl} | {item.green_lock_events} | {item.trade_stop_update_events} | "
            f"{item.locked_trail_samples} | {md(item.secondary_failure_class)} |"
        )
    return lines


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[ProtectionResult]) -> None:
    fieldnames = list(ProtectionResult.__dataclass_fields__.keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def md(value: Any) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip() or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
