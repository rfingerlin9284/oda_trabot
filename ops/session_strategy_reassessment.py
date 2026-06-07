from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_JSON = REPO_ROOT / "analysis" / "strategy_lifecycle_audit" / "closed_trade_lifecycle_results.json"
PROTECTION_JSON = REPO_ROOT / "analysis" / "protection_failure_audit" / "protection_failure_results.json"
OUTPUT_DIR = REPO_ROOT / "analysis" / "session_strategy_reassessment"
DOCS_REPORT = REPO_ROOT / "docs" / "OUTSIDE_FROZEN_SESSION_STRATEGY_REASSESSMENT_20260607.md"

FROZEN_START = time(3, 0)
FROZEN_END = time(8, 30)


SESSION_ORDER = [
    "transition_0830_0900",
    "post_london_overlap_0900_1130",
    "midday_ny_1130_1400",
    "ny_afternoon_1400_1700",
    "rollover_asia_open_1700_2100",
    "tokyo_2100_0000",
    "pre_london_0000_0300",
]

SESSION_LABELS = {
    "transition_0830_0900": "8:30-9:00 AM transition",
    "post_london_overlap_0900_1130": "9:00-11:30 AM post-London / NY overlap",
    "midday_ny_1130_1400": "11:30 AM-2:00 PM New York midday",
    "ny_afternoon_1400_1700": "2:00-5:00 PM New York afternoon",
    "rollover_asia_open_1700_2100": "5:00-9:00 PM rollover / Asia open",
    "tokyo_2100_0000": "9:00 PM-midnight Tokyo",
    "pre_london_0000_0300": "midnight-3:00 AM pre-London",
}


@dataclass(frozen=True)
class SummaryRow:
    bucket: str
    strategy_family: str
    trades: int
    wins: int
    losses: int
    pnl_usd: float
    win_rate_pct: float
    profit_factor: float | str
    pairs: str
    edge_giveback_losses: int
    missing_primary_protection_losses: int
    no_trailing_manager_losses: int
    decision: str


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lifecycle_rows = json.loads(LIFECYCLE_JSON.read_text())
    protection_rows = json.loads(PROTECTION_JSON.read_text())
    protection = {protection_key(row): row for row in protection_rows}

    clean_rows = [row for row in lifecycle_rows if row.get("clean_for_strategy_mining") and entry_bucket(row) != "frozen_0300_0830"]
    summaries = build_summaries(clean_rows, protection)
    core_rows = [row for row in clean_rows if is_core_ema_fib_continuation(row)]
    core_summaries = build_summaries(core_rows, protection)

    write_json(OUTPUT_DIR / "session_strategy_summary.json", [asdict_like(row) for row in summaries])
    write_json(OUTPUT_DIR / "core_ema_fib_continuation_summary.json", [asdict_like(row) for row in core_summaries])
    write_csv(OUTPUT_DIR / "outside_frozen_clean_trades.csv", clean_rows)
    write_report(DOCS_REPORT, lifecycle_rows, clean_rows, summaries, core_rows, core_summaries, protection)
    write_report(
        OUTPUT_DIR / "outside_frozen_session_strategy_reassessment.md",
        lifecycle_rows,
        clean_rows,
        summaries,
        core_rows,
        core_summaries,
        protection,
    )

    print(f"Outside-frozen clean entries: {len(clean_rows)}")
    print(f"Report: {DOCS_REPORT}")
    return 0


def build_summaries(rows: list[dict[str, Any]], protection: dict[tuple[str, str, str, float], dict[str, Any]]) -> list[SummaryRow]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(entry_bucket(row), str(row.get("strategy_family") or "unknown"))].append(row)

    summaries: list[SummaryRow] = []
    for (bucket, strategy), items in grouped.items():
        wins = [item for item in items if item.get("outcome") == "WIN"]
        losses = [item for item in items if item.get("outcome") == "LOSS"]
        pnl = sum(float(item.get("pnl_usd") or 0.0) for item in items)
        gross_win = sum(float(item.get("pnl_usd") or 0.0) for item in wins)
        gross_loss = abs(sum(float(item.get("pnl_usd") or 0.0) for item in losses))
        pf: float | str
        if gross_loss == 0:
            pf = "inf" if gross_win > 0 else 0.0
        else:
            pf = round(gross_win / gross_loss, 2)
        edge_giveback = 0
        missing_primary = 0
        no_manager = 0
        for item in losses:
            prot = protection.get(protection_key(item), {})
            failure = str(prot.get("secondary_failure_class") or "")
            if failure in {"edge_present_but_no_trailing_or_lock", "edge_present_but_protection_did_not_hold"}:
                edge_giveback += 1
            if failure == "missing_primary_protection":
                missing_primary += 1
            if failure == "loss_no_trailing_manager_samples":
                no_manager += 1
        summaries.append(
            SummaryRow(
                bucket=bucket,
                strategy_family=strategy,
                trades=len(items),
                wins=len(wins),
                losses=len(losses),
                pnl_usd=round(pnl, 4),
                win_rate_pct=round(len(wins) / len(items) * 100, 2) if items else 0.0,
                profit_factor=pf,
                pairs=", ".join(sorted({str(item.get("symbol")) for item in items})),
                edge_giveback_losses=edge_giveback,
                missing_primary_protection_losses=missing_primary,
                no_trailing_manager_losses=no_manager,
                decision=decision_for(bucket, strategy, len(items), len(wins), len(losses), pnl, pf),
            )
        )
    return sorted(summaries, key=lambda row: (SESSION_ORDER.index(row.bucket), -row.pnl_usd, row.strategy_family))


def write_report(
    path: Path,
    lifecycle_rows: list[dict[str, Any]],
    clean_rows: list[dict[str, Any]],
    summaries: list[SummaryRow],
    core_rows: list[dict[str, Any]],
    core_summaries: list[SummaryRow],
    protection: dict[tuple[str, str, str, float], dict[str, Any]],
) -> None:
    frozen_rows = [row for row in lifecycle_rows if row.get("clean_for_strategy_mining") and entry_bucket(row) == "frozen_0300_0830"]
    lines = [
        "# Outside-Frozen Session Strategy Reassessment",
        "",
        "Date: June 7, 2026",
        "",
        "## Operator Answer",
        "",
        "I reassessed strategies by entry time outside the frozen 3:00 AM-8:30 AM ET momentum cartridge.",
        "",
        "The deployable read is not \"trade momentum all day.\"",
        "",
        "The clean outside-frozen edge is narrower:",
        "",
        "`9:00-11:30 AM ET EMA/Fibonacci momentum continuation`",
        "",
        "That is the only outside-frozen session/strategy combination that clearly survives this pass.",
        "",
        "## Method",
        "",
        "- Used historical OANDA repo logs only.",
        "- Used clean high-confidence closed trade results from the lifecycle audit.",
        "- Grouped by trade open time, not close time.",
        "- Excluded entries opened from 3:00 AM through 8:29 AM ET.",
        "- Folded in protection-failure classifications from the SL/TP/trailing audit.",
        "- Split clean EMA/Fibonacci continuation away from detector-contaminated continuation labels.",
        "",
        "## Audit Counts",
        "",
        f"- Clean trades in frozen 3:00-8:30 AM window: {len(frozen_rows)}",
        f"- Clean trades opened outside frozen window: {len(clean_rows)}",
        f"- Clean core EMA/Fibonacci continuation trades outside frozen window: {len(core_rows)}",
        "",
        "## Session-Level Result",
        "",
    ]
    lines.extend(render_session_rollup(clean_rows))
    lines.extend(
        [
            "",
            "## Strategy Result By Session",
            "",
        ]
    )
    lines.extend(render_summary_table(summaries))
    lines.extend(
        [
            "",
            "## Clean EMA/Fibonacci Continuation Only",
            "",
            "This is the cleaner version of the edge. It requires `ema_stack` and `fibonacci`, and it avoids treating reversal/trap labels as continuation just because an old log named them that way.",
            "",
        ]
    )
    lines.extend(render_summary_table(core_summaries))
    lines.extend(
        [
            "",
            "## Reassessment Decision",
            "",
            "### Build First",
            "",
            "`post_9am_ema_fib_momentum_continuation`",
            "",
            "- Entry window: 9:00-11:30 AM ET",
            "- Clean core sample: 7 wins, 0 losses",
            "- P&L: about +$562.31",
            "- Pairs: AUD_USD, EUR_USD, NZD_USD, USD_CAD, USD_CHF",
            "- Required detectors: `ema_stack` + `fibonacci`",
            "- Stronger when `momentum_sma` is also present",
            "- Required workflow: `continuation`",
            "- Exclude `trap_reversal`, `rsi_extreme`, and scalp detectors from this cartridge",
            "- Practice only",
            "",
            "### Watch But Do Not Deploy Yet",
            "",
            "`ny_afternoon_ema_fib_continuation`",
            "",
            "- Entry window: 2:00-5:00 PM ET",
            "- Clean core sample: 2 wins, 0 losses",
            "- P&L: about +$117.84",
            "- Pair evidence: EUR_USD only",
            "- Too small to activate as a separate cartridge yet",
            "",
            "### Do Not Deploy",
            "",
            "- 8:30-9:00 AM transition: negative and unstable.",
            "- 11:30 AM-2:00 PM midday: not cleared once detector contamination is removed.",
            "- 5:00-9:00 PM rollover / Asia open: negative.",
            "- 9:00 PM-midnight Tokyo: 0 wins in the clean outside-frozen set.",
            "- midnight-3:00 AM pre-London: negative overall.",
            "- scalp: negative in every outside-frozen bucket.",
            "- reversal: negative in every outside-frozen bucket.",
            "- generic momentum: negative outside frozen because it was weakly gated and contaminated.",
            "",
            "## Protection Read",
            "",
        ]
    )
    lines.extend(render_protection_read(clean_rows, protection))
    lines.extend(
        [
            "",
            "## Core 9:00-11:30 Evidence Trades",
            "",
        ]
    )
    lines.extend(render_trade_table([row for row in core_rows if entry_bucket(row) == "post_london_overlap_0900_1130"], protection))
    lines.extend(
        [
            "",
            "## Final Rule",
            "",
            "The frozen 3:00-8:30 AM cartridge stays untouched.",
            "",
            "The only new outside-frozen cartridge that earns construction is a separate, narrow practice-only cartridge:",
            "",
            "`post_9am_ema_fib_momentum_continuation`",
            "",
            "Anything broader is contamination.",
            "",
            "## Output Files",
            "",
            f"- Session summary JSON: `{OUTPUT_DIR / 'session_strategy_summary.json'}`",
            f"- Core continuation JSON: `{OUTPUT_DIR / 'core_ema_fib_continuation_summary.json'}`",
            f"- Outside-frozen trade CSV: `{OUTPUT_DIR / 'outside_frozen_clean_trades.csv'}`",
            f"- Technical report: `{OUTPUT_DIR / 'outside_frozen_session_strategy_reassessment.md'}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def render_session_rollup(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Session | Trades | Wins | Losses | P&L | Decision |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_bucket[entry_bucket(row)].append(row)
    for bucket in SESSION_ORDER:
        items = by_bucket.get(bucket, [])
        wins = sum(1 for item in items if item.get("outcome") == "WIN")
        losses = sum(1 for item in items if item.get("outcome") == "LOSS")
        pnl = sum(float(item.get("pnl_usd") or 0.0) for item in items)
        decision = session_decision(bucket, items, pnl)
        lines.append(f"| {md(SESSION_LABELS[bucket])} | {len(items)} | {wins} | {losses} | {pnl:.2f} | {md(decision)} |")
    return lines


def render_summary_table(rows: list[SummaryRow]) -> list[str]:
    if not rows:
        return ["No rows found."]
    lines = [
        "| Session | Strategy | Trades | W | L | P&L | PF | Edge Giveback Losses | Decision |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        pf = f"{row.profit_factor:.2f}" if isinstance(row.profit_factor, float) else str(row.profit_factor)
        lines.append(
            f"| {md(SESSION_LABELS[row.bucket])} | {md(row.strategy_family)} | {row.trades} | {row.wins} | {row.losses} | "
            f"{row.pnl_usd:.2f} | {pf} | {row.edge_giveback_losses} | {md(row.decision)} |"
        )
    return lines


def render_protection_read(rows: list[dict[str, Any]], protection: dict[tuple[str, str, str, float], dict[str, Any]]) -> list[str]:
    losses = [row for row in rows if row.get("outcome") == "LOSS"]
    counts: Counter[str] = Counter()
    for row in losses:
        prot = protection.get(protection_key(row), {})
        counts[str(prot.get("secondary_failure_class") or "unknown")] += 1
    if not counts:
        return ["No outside-frozen losses found."]
    lines = [
        "| Protection Class | Count | Meaning |",
        "| --- | ---: | --- |",
    ]
    meanings = {
        "entry_failed_before_secondary_could_help": "Entry/setup failed before protection could help.",
        "edge_present_but_no_trailing_or_lock": "Trade went green, then red, with no logged lock/trailing.",
        "small_pip_green_not_enough_for_lock": "Small pip movement, not enough to blame trailing.",
        "small_green_not_enough_for_lock": "Small positive P&L, not enough to blame trailing.",
        "loss_no_trailing_manager_samples": "SL/TP existed, but manager did not log trailing samples.",
    }
    for key, count in counts.most_common():
        lines.append(f"| {md(key)} | {count} | {md(meanings.get(key, 'Manual review needed.'))} |")
    return lines


def render_trade_table(rows: list[dict[str, Any]], protection: dict[tuple[str, str, str, float], dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No evidence trades found."]
    lines = [
        "| Open ET | Close ET | Pair | P&L | Detectors | Protection Class |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in sorted(rows, key=lambda item: item.get("open_timestamp_et") or ""):
        prot = protection.get(protection_key(row), {})
        lines.append(
            f"| {md(str(row.get('open_timestamp_et'))[:16])} | {md(str(row.get('close_timestamp_et'))[:16])} | "
            f"{md(row.get('symbol'))} | {float(row.get('pnl_usd') or 0.0):.2f} | "
            f"{md(row.get('signal_detectors'))} | {md(prot.get('secondary_failure_class') or '')} |"
        )
    return lines


def entry_bucket(row: dict[str, Any]) -> str:
    dt = parse_dt(row.get("open_timestamp_et"))
    if dt is None:
        dt = parse_dt(row.get("close_timestamp_et"))
    if dt is None:
        return "unknown"
    current = dt.time()
    if FROZEN_START <= current < FROZEN_END:
        return "frozen_0300_0830"
    if time(8, 30) <= current < time(9, 0):
        return "transition_0830_0900"
    if time(9, 0) <= current < time(11, 30):
        return "post_london_overlap_0900_1130"
    if time(11, 30) <= current < time(14, 0):
        return "midday_ny_1130_1400"
    if time(14, 0) <= current < time(17, 0):
        return "ny_afternoon_1400_1700"
    if time(17, 0) <= current < time(21, 0):
        return "rollover_asia_open_1700_2100"
    if time(21, 0) <= current:
        return "tokyo_2100_0000"
    return "pre_london_0000_0300"


def parse_dt(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def is_core_ema_fib_continuation(row: dict[str, Any]) -> bool:
    if row.get("strategy_family") != "momentum_continuation":
        return False
    detectors = {item for item in str(row.get("signal_detectors") or "").split(";") if item}
    return "ema_stack" in detectors and "fibonacci" in detectors


def decision_for(bucket: str, strategy: str, trades: int, wins: int, losses: int, pnl: float, pf: float | str) -> str:
    if bucket == "post_london_overlap_0900_1130" and strategy == "momentum_continuation" and wins >= 7 and pnl > 0:
        return "build narrow cartridge after detector cleanup"
    if strategy in {"scalp", "reversal"}:
        return "do not deploy"
    if pnl <= 0:
        return "do not deploy"
    if trades < 5:
        return "small-sample watch only"
    if isinstance(pf, float) and pf < 1.5:
        return "not enough edge after losses"
    return "paper probation only"


def session_decision(bucket: str, items: list[dict[str, Any]], pnl: float) -> str:
    if bucket == "post_london_overlap_0900_1130":
        return "only EMA/Fib continuation survives; all-session bucket is negative if contaminated"
    if bucket == "ny_afternoon_1400_1700":
        return "watch only; tiny positive continuation sample"
    if pnl <= 0:
        return "do not trade this whole session bucket"
    return "manual review"


def protection_key(row: dict[str, Any]) -> tuple[str, str, str, float]:
    return (
        str(row.get("source_path") or ""),
        str(row.get("trade_id") or ""),
        str(row.get("close_timestamp_et") or "")[:16],
        round(float(row.get("pnl_usd") or 0.0), 4),
    )


def asdict_like(row: SummaryRow) -> dict[str, Any]:
    return {
        "bucket": row.bucket,
        "strategy_family": row.strategy_family,
        "trades": row.trades,
        "wins": row.wins,
        "losses": row.losses,
        "pnl_usd": row.pnl_usd,
        "win_rate_pct": row.win_rate_pct,
        "profit_factor": row.profit_factor,
        "pairs": row.pairs,
        "edge_giveback_losses": row.edge_giveback_losses,
        "missing_primary_protection_losses": row.missing_primary_protection_losses,
        "no_trailing_manager_losses": row.no_trailing_manager_losses,
        "decision": row.decision,
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    keys = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def md(value: Any) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip() or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
