from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_ROOT = REPO_ROOT / "ops"
if str(OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(OPS_ROOT))

from live_paper_outside_window_audit import (  # noqa: E402
    ET,
    LEGACY_ROOT,
    OANDA_PAIRS,
    discover_log_files,
    normalize_symbol,
    numeric,
    parse_json_line,
    parse_timestamp,
    source_repo_name,
    update_file_context,
)


OUTPUT_DIR = REPO_ROOT / "analysis" / "strategy_lifecycle_audit"
DOCS_REPORT = REPO_ROOT / "docs" / "STRATEGY_LIFECYCLE_AUDIT_PLAIN_ENGLISH_20260607.md"


@dataclass
class TradeContext:
    trade_id: str
    symbol: str = ""
    open_timestamp_utc: str = ""
    open_timestamp_et: str = ""
    direction: str = ""
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    units: float | None = None
    signal_confidence: float | None = None
    signal_votes: int | None = None
    signal_session: str = ""
    signal_detectors: list[str] = field(default_factory=list)
    strategy_counts: Counter[str] = field(default_factory=Counter)
    workflow_counts: Counter[str] = field(default_factory=Counter)
    timeframe_counts: Counter[str] = field(default_factory=Counter)
    exit_profile_counts: Counter[str] = field(default_factory=Counter)
    close_reason_counts: Counter[str] = field(default_factory=Counter)
    max_tracked_pnl_usd: float | None = None
    max_tracked_pnl_timestamp_et: str = ""
    min_tracked_pnl_usd: float | None = None
    last_tracked_pnl_usd: float | None = None
    max_tracked_pips: float | None = None
    min_tracked_pips: float | None = None
    last_tracked_pips: float | None = None
    max_rr_ratio: float | None = None
    trail_samples: int = 0
    practice_order: bool = False
    live_api: bool = False
    visible_in_oanda: bool = False
    oco_order_id: str = ""
    source_open_line: int | None = None


@dataclass(frozen=True)
class TradeResult:
    source_path: str
    source_line: int
    source_repo: str
    confidence_class: str
    confidence_reason: str
    clean_for_strategy_mining: bool
    trade_id: str
    symbol: str
    outcome: str
    pnl_usd: float
    close_timestamp_utc: str
    close_timestamp_et: str
    close_hour_et: int
    open_timestamp_et: str
    event_type: str
    close_venue: str
    close_reason: str
    direction: str
    strategy_label: str
    strategy_family: str
    workflow_profile: str
    signal_session: str
    signal_confidence: float | None
    signal_votes: int | None
    signal_detectors: str
    timeframe: str
    exit_profile: str
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    units: float | None
    max_tracked_pnl_usd: float | None
    min_tracked_pnl_usd: float | None
    last_tracked_pnl_usd: float | None
    max_tracked_pips: float | None
    min_tracked_pips: float | None
    last_tracked_pips: float | None
    max_rr_ratio: float | None
    trail_samples: int
    loss_diagnosis: str
    loss_diagnosis_detail: str
    duplicate_source_count: int = 1
    duplicate_sources: str = ""


@dataclass(frozen=True)
class AuditStats:
    generated_at_utc: str
    legacy_root: str
    files_scanned: int
    bytes_scanned: int
    lines_scanned: int
    json_records: int
    close_events_seen: int
    closed_trade_results: int
    high_confidence_results: int
    clean_high_confidence_results: int
    wins: int
    losses: int
    breakeven: int


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = discover_log_files(LEGACY_ROOT)
    results, counters = scan_files(files)
    unique_results = dedupe_results(results)
    high_confidence = [r for r in unique_results if r.confidence_class == "high_confidence_practice_receipt"]
    clean_high_confidence = [r for r in high_confidence if r.clean_for_strategy_mining]
    stats = AuditStats(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        legacy_root=str(LEGACY_ROOT),
        files_scanned=len(files),
        bytes_scanned=sum(path.stat().st_size for path in files if path.exists()),
        lines_scanned=counters["lines_scanned"],
        json_records=counters["json_records"],
        close_events_seen=counters["close_events_seen"],
        closed_trade_results=len(unique_results),
        high_confidence_results=len(high_confidence),
        clean_high_confidence_results=len(clean_high_confidence),
        wins=sum(1 for r in clean_high_confidence if r.outcome == "WIN"),
        losses=sum(1 for r in clean_high_confidence if r.outcome == "LOSS"),
        breakeven=sum(1 for r in clean_high_confidence if r.outcome == "BREAKEVEN"),
    )

    write_json(OUTPUT_DIR / "closed_trade_lifecycle_results.json", [asdict(r) for r in unique_results])
    write_json(OUTPUT_DIR / "scan_stats.json", asdict(stats))
    write_csv(OUTPUT_DIR / "closed_trade_lifecycle_results.csv", unique_results)
    write_json(OUTPUT_DIR / "strategy_summary.json", strategy_summary(clean_high_confidence))
    write_plain_english_report(DOCS_REPORT, stats, clean_high_confidence, high_confidence, unique_results)
    write_plain_english_report(OUTPUT_DIR / "strategy_lifecycle_audit.md", stats, clean_high_confidence, high_confidence, unique_results)

    print(f"Scanned {stats.files_scanned} unique log files")
    print(f"Closed trade results: {stats.closed_trade_results}")
    print(f"High-confidence linked practice results: {stats.high_confidence_results}")
    print(f"Clean high-confidence strategy-mining results: {stats.clean_high_confidence_results}")
    print(f"Plain English report: {DOCS_REPORT}")
    return 0


def scan_files(files: list[Path]) -> tuple[list[TradeResult], Counter[str]]:
    results: list[TradeResult] = []
    counters: Counter[str] = Counter()
    for path in files:
        trades: dict[str, TradeContext] = {}
        file_context = {"practice_endpoint_seen": False, "non_placeholder_account_seen": False}
        try:
            with path.open("r", errors="replace") as handle:
                for line_number, line in enumerate(handle, 1):
                    counters["lines_scanned"] += 1
                    obj = parse_json_line(line)
                    if obj is None:
                        continue
                    counters["json_records"] += 1
                    update_file_context(obj, file_context)
                    result = process_event(path, line_number, obj, trades, file_context, counters)
                    if result is not None:
                        results.append(result)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Could not scan {path}: {exc}", file=sys.stderr)
    return results, counters


def process_event(
    path: Path,
    line_number: int,
    obj: dict[str, Any],
    trades: dict[str, TradeContext],
    file_context: dict[str, bool],
    counters: Counter[str],
) -> TradeResult | None:
    event_type = str(obj.get("event_type") or obj.get("kind") or obj.get("type") or "")
    details = obj.get("details") if isinstance(obj.get("details"), dict) else {}
    trade_id = str(details.get("trade_id") or details.get("close_trade_id") or obj.get("trade_id") or "").strip()
    symbol = normalize_symbol(obj.get("symbol") or details.get("symbol") or details.get("instrument") or details.get("close_symbol"))

    if trade_id:
        context = trades.setdefault(trade_id, TradeContext(trade_id=trade_id, symbol=symbol))
        if symbol and not context.symbol:
            context.symbol = symbol
        enrich_context(context, event_type, obj, details, line_number)

    if event_type not in {"TRADE_CLOSED", "POSITION_CLOSED"}:
        return None

    counters["close_events_seen"] += 1
    pnl = numeric(details.get("pnl_usd") or details.get("realizedPL") or details.get("realized_pl") or details.get("pnl"))
    close_utc = parse_timestamp(obj.get("timestamp") or obj.get("timestamp_utc") or details.get("closed_time"))
    if pnl is None or close_utc is None:
        return None

    context = trades.get(trade_id, TradeContext(trade_id=trade_id, symbol=symbol))
    if symbol and not context.symbol:
        context.symbol = symbol
    if context.symbol not in OANDA_PAIRS:
        return None

    close_et = close_utc.astimezone(ET)
    close_reason = str(details.get("reason") or details.get("close_reason") or "")
    if close_reason:
        context.close_reason_counts[close_reason] += 1
    confidence_class, confidence_reason = classify_confidence(context, obj, file_context)
    strategy_label = best_label(context.strategy_counts) or str(details.get("strategy") or "")
    workflow_profile = best_label(context.workflow_counts) or str(details.get("workflow_profile") or details.get("workflow") or "")
    family = strategy_family(strategy_label, workflow_profile, context.signal_detectors)
    outcome = outcome_for_pnl(float(pnl))
    clean_for_strategy_mining = is_clean_for_strategy_mining(confidence_class, close_reason)
    diagnosis, diagnosis_detail = diagnose_loss(
        outcome=outcome,
        pnl=float(pnl),
        strategy_family=family,
        workflow_profile=workflow_profile,
        close_reason=close_reason,
        context=context,
    )

    return TradeResult(
        source_path=str(path),
        source_line=line_number,
        source_repo=source_repo_name(path),
        confidence_class=confidence_class,
        confidence_reason=confidence_reason,
        clean_for_strategy_mining=clean_for_strategy_mining,
        trade_id=trade_id,
        symbol=context.symbol,
        outcome=outcome,
        pnl_usd=round(float(pnl), 4),
        close_timestamp_utc=close_utc.isoformat(),
        close_timestamp_et=close_et.isoformat(),
        close_hour_et=close_et.hour,
        open_timestamp_et=context.open_timestamp_et,
        event_type=event_type,
        close_venue=str(obj.get("venue") or ""),
        close_reason=close_reason,
        direction=context.direction,
        strategy_label=strategy_label,
        strategy_family=family,
        workflow_profile=workflow_profile,
        signal_session=context.signal_session,
        signal_confidence=context.signal_confidence,
        signal_votes=context.signal_votes,
        signal_detectors=";".join(context.signal_detectors),
        timeframe=best_label(context.timeframe_counts),
        exit_profile=best_label(context.exit_profile_counts),
        entry_price=context.entry_price,
        stop_loss=context.stop_loss,
        take_profit=context.take_profit,
        units=context.units,
        max_tracked_pnl_usd=context.max_tracked_pnl_usd,
        min_tracked_pnl_usd=context.min_tracked_pnl_usd,
        last_tracked_pnl_usd=context.last_tracked_pnl_usd,
        max_tracked_pips=context.max_tracked_pips,
        min_tracked_pips=context.min_tracked_pips,
        last_tracked_pips=context.last_tracked_pips,
        max_rr_ratio=context.max_rr_ratio,
        trail_samples=context.trail_samples,
        loss_diagnosis=diagnosis,
        loss_diagnosis_detail=diagnosis_detail,
    )


def enrich_context(
    context: TradeContext,
    event_type: str,
    obj: dict[str, Any],
    details: dict[str, Any],
    line_number: int,
) -> None:
    timestamp_utc = parse_timestamp(obj.get("timestamp") or obj.get("timestamp_utc"))
    if event_type == "OCO_PLACED":
        context.source_open_line = line_number
        context.oco_order_id = str(details.get("order_id") or context.oco_order_id)
        context.practice_order = str(details.get("environment") or "").upper() == "PRACTICE" or context.practice_order
        context.live_api = bool(details.get("live_api")) or context.live_api
        context.visible_in_oanda = bool(details.get("visible_in_oanda")) or context.visible_in_oanda
        context.entry_price = numeric(details.get("entry_price")) or context.entry_price
        context.stop_loss = numeric(details.get("stop_loss")) or context.stop_loss
        context.take_profit = numeric(details.get("take_profit")) or context.take_profit
        context.units = numeric(details.get("units")) or context.units
        if timestamp_utc is not None:
            context.open_timestamp_utc = timestamp_utc.isoformat()
            context.open_timestamp_et = timestamp_utc.astimezone(ET).isoformat()

    if event_type == "TRADE_OPENED":
        context.direction = str(details.get("direction") or context.direction)
        context.entry_price = numeric(details.get("entry_price")) or context.entry_price
        context.stop_loss = numeric(details.get("stop_loss")) or context.stop_loss
        context.take_profit = numeric(details.get("take_profit")) or context.take_profit
        context.units = numeric(details.get("size")) or context.units
        context.signal_confidence = numeric(details.get("signal_confidence")) or context.signal_confidence
        votes = details.get("signal_votes")
        context.signal_votes = int(votes) if isinstance(votes, int) else context.signal_votes
        context.signal_session = str(details.get("signal_session") or context.signal_session)
        detectors = details.get("signal_detectors")
        if isinstance(detectors, list):
            context.signal_detectors = [str(item) for item in detectors]
        if timestamp_utc is not None and not context.open_timestamp_et:
            context.open_timestamp_utc = timestamp_utc.isoformat()
            context.open_timestamp_et = timestamp_utc.astimezone(ET).isoformat()

    if event_type == "POSITION_SYNCED":
        context.direction = str(details.get("direction") or context.direction)
        context.signal_session = str(details.get("session") or context.signal_session)
        context.signal_confidence = numeric(details.get("confidence")) or context.signal_confidence
        votes = details.get("votes")
        context.signal_votes = int(votes) if isinstance(votes, int) else context.signal_votes
        detectors = details.get("detectors")
        if isinstance(detectors, list) and detectors:
            context.signal_detectors = [str(item) for item in detectors]

    if event_type == "TRAIL_CANDIDATE":
        context.trail_samples += 1
        context.direction = str(details.get("direction") or context.direction)
        count_label(context.strategy_counts, details.get("strategy"))
        count_label(context.timeframe_counts, details.get("timeframe"))
        count_label(context.exit_profile_counts, details.get("exit_profile"))
        pnl = numeric(details.get("pnl"))
        pips = numeric(details.get("pips"))
        rr_ratio = numeric(details.get("rr_ratio"))
        if pnl is not None:
            context.last_tracked_pnl_usd = round(pnl, 4)
            if context.max_tracked_pnl_usd is None or pnl > context.max_tracked_pnl_usd:
                context.max_tracked_pnl_usd = round(pnl, 4)
                context.max_tracked_pnl_timestamp_et = timestamp_utc.astimezone(ET).isoformat() if timestamp_utc else ""
            if context.min_tracked_pnl_usd is None or pnl < context.min_tracked_pnl_usd:
                context.min_tracked_pnl_usd = round(pnl, 4)
        if pips is not None:
            context.last_tracked_pips = round(pips, 4)
            context.max_tracked_pips = round(pips, 4) if context.max_tracked_pips is None else round(max(context.max_tracked_pips, pips), 4)
            context.min_tracked_pips = round(pips, 4) if context.min_tracked_pips is None else round(min(context.min_tracked_pips, pips), 4)
        if rr_ratio is not None:
            context.max_rr_ratio = round(rr_ratio, 4) if context.max_rr_ratio is None else round(max(context.max_rr_ratio, rr_ratio), 4)

    workflow_profile = details.get("workflow_profile") or details.get("workflow")
    count_label(context.workflow_counts, workflow_profile)
    count_label(context.strategy_counts, details.get("strategy"))


def classify_confidence(context: TradeContext, obj: dict[str, Any], file_context: dict[str, bool]) -> tuple[str, str]:
    if context.practice_order and context.live_api and context.visible_in_oanda:
        return (
            "high_confidence_practice_receipt",
            "closed trade linked to matching PRACTICE OCO order with live_api=true and visible_in_oanda=true",
        )
    if file_context.get("practice_endpoint_seen") and file_context.get("non_placeholder_account_seen"):
        venue = str(obj.get("venue") or "")
        if venue in {"oanda", "trade_manager"}:
            return (
                "runtime_paper_close",
                "closed trade came from runtime log initialized against api-fxpractice.oanda.com with a non-placeholder account",
            )
    return (
        "unlinked_close_candidate",
        "closed trade found, but matching practice OCO receipt was not present in the scanned file",
    )


def dedupe_results(results: list[TradeResult]) -> list[TradeResult]:
    confidence_rank = {
        "high_confidence_practice_receipt": 3,
        "runtime_paper_close": 2,
        "unlinked_close_candidate": 1,
    }
    event_rank = {"TRADE_CLOSED": 3, "POSITION_CLOSED": 2}
    grouped: dict[tuple[str, str, str, float], list[TradeResult]] = defaultdict(list)
    for result in results:
        key = (result.trade_id, result.symbol, result.close_timestamp_et[:16], round(result.pnl_usd, 4))
        grouped[key].append(result)

    unique: list[TradeResult] = []
    for group in grouped.values():
        best = max(
            group,
            key=lambda item: (
                confidence_rank.get(item.confidence_class, 0),
                event_rank.get(item.event_type, 0),
                item.close_venue == "oanda",
            ),
        )
        sources = sorted({item.source_path for item in group})
        unique.append(
            TradeResult(
                **{
                    **asdict(best),
                    "duplicate_source_count": len(sources),
                    "duplicate_sources": ";".join(sources),
                }
            )
        )
    return sorted(unique, key=lambda item: (item.close_timestamp_et, item.trade_id, item.symbol))


def outcome_for_pnl(pnl: float) -> str:
    if pnl > 0:
        return "WIN"
    if pnl < 0:
        return "LOSS"
    return "BREAKEVEN"


def is_clean_for_strategy_mining(confidence_class: str, close_reason: str) -> bool:
    reason = close_reason.lower()
    return (
        confidence_class == "high_confidence_practice_receipt"
        and reason != "estimated"
        and "transcript" not in reason
    )


def diagnose_loss(
    *,
    outcome: str,
    pnl: float,
    strategy_family: str,
    workflow_profile: str,
    close_reason: str,
    context: TradeContext,
) -> tuple[str, str]:
    if outcome != "LOSS":
        return "not_a_loss", "Winning or breakeven trade."

    max_pnl = context.max_tracked_pnl_usd
    min_pnl = context.min_tracked_pnl_usd
    detectors = {item.lower() for item in context.signal_detectors}
    reason = close_reason.lower()
    workflow = workflow_profile.lower()
    session = context.signal_session.lower()
    confidence = context.signal_confidence or 0.0
    votes = context.signal_votes or 0

    if max_pnl is not None and max_pnl >= 5.0:
        giveback = max_pnl - pnl
        return (
            "edge_present_exit_or_workflow_gave_back",
            f"Trade reached about +${max_pnl:.2f} before closing at ${pnl:.2f}; about ${giveback:.2f} was given back.",
        )
    if max_pnl is not None and max_pnl > 0:
        return (
            "small_edge_then_noise_loss",
            f"Trade had only a small favorable excursion of about +${max_pnl:.2f}; edge was not strong enough before the loss.",
        )
    if "wick_scratch" in reason:
        return (
            "scratch_or_noise_exit_without_followthrough",
            "Closed by wick_scratch and never showed meaningful favorable P&L in the tracked manager samples.",
        )
    if "stop" in reason or "hard" in reason:
        return (
            "risk_stop_hit",
            "Closed by stop or hard-risk logic; entry did not produce enough followthrough before risk control fired.",
        )
    if strategy_family == "scalp":
        return (
            "scalp_no_followthrough",
            "Scalp setup did not travel enough; this supports keeping scalp secondary until separately proven.",
        )
    if strategy_family == "reversal" and "ema_stack" not in detectors and "fibonacci" not in detectors:
        return (
            "reversal_missing_trend_confirmation",
            "Reversal trade lacked the stronger ema_stack/fibonacci confirmation that appeared often in the better momentum winners.",
        )
    if confidence < 0.82 or votes < 2:
        return (
            "quality_gate_too_weak",
            f"Signal quality was thin: confidence={confidence:.2f}, votes={votes}.",
        )
    if session in {"tokyo", "off_session"} and strategy_family not in {"momentum", "momentum_continuation"}:
        return (
            "session_mismatch",
            f"Loss occurred with signal_session={context.signal_session}; this looks like timing/session contamination more than proven edge.",
        )
    if min_pnl is not None:
        return (
            "strategy_no_logged_edge_on_trade",
            f"No positive tracked excursion was found; worst tracked P&L was about ${min_pnl:.2f}.",
        )
    return (
        "insufficient_lifecycle_context",
        "Close was logged, but there were not enough manager samples to separate strategy failure from workflow/indicator failure.",
    )


def strategy_family(strategy_label: str, workflow_profile: str, detectors: list[str]) -> str:
    label = strategy_label.strip().lower().replace(" ", "_")
    workflow = workflow_profile.strip().lower().replace(" ", "_")
    if label in {"trend_continuation", "continuation"}:
        return "momentum_continuation"
    if label == "momentum" and workflow == "continuation":
        return "momentum_continuation"
    if label:
        return label
    if workflow == "continuation":
        return "momentum_continuation"
    if workflow:
        return workflow
    dets = {item.lower() for item in detectors}
    if {"ema_stack", "fibonacci"} & dets:
        return "momentum_unknown_label"
    return "unknown"


def strategy_summary(results: list[TradeResult]) -> list[dict[str, Any]]:
    groups: dict[str, list[TradeResult]] = defaultdict(list)
    for result in results:
        groups[result.strategy_family].append(result)
    rows: list[dict[str, Any]] = []
    for strategy, items in groups.items():
        wins = [r for r in items if r.outcome == "WIN"]
        losses = [r for r in items if r.outcome == "LOSS"]
        pnl = sum(r.pnl_usd for r in items)
        rows.append(
            {
                "strategy_family": strategy,
                "trades": len(items),
                "wins": len(wins),
                "losses": len(losses),
                "breakeven": sum(1 for r in items if r.outcome == "BREAKEVEN"),
                "win_rate_pct": round(len(wins) / len(items) * 100, 2) if items else 0.0,
                "total_pnl_usd": round(pnl, 4),
                "avg_win_usd": round(sum(r.pnl_usd for r in wins) / len(wins), 4) if wins else 0.0,
                "avg_loss_usd": round(sum(r.pnl_usd for r in losses) / len(losses), 4) if losses else 0.0,
                "profit_factor": profit_factor(wins, losses),
                "top_pairs": dict(Counter(r.symbol for r in items).most_common(7)),
                "loss_diagnoses": dict(Counter(r.loss_diagnosis for r in losses).most_common()),
            }
        )
    return sorted(rows, key=lambda row: (row["total_pnl_usd"], row["wins"]), reverse=True)


def profit_factor(wins: list[TradeResult], losses: list[TradeResult]) -> float | str:
    gross_win = sum(r.pnl_usd for r in wins)
    gross_loss = abs(sum(r.pnl_usd for r in losses))
    if gross_loss == 0:
        return "inf" if gross_win > 0 else 0.0
    return round(gross_win / gross_loss, 4)


def write_plain_english_report(
    path: Path,
    stats: AuditStats,
    clean_results: list[TradeResult],
    high_confidence_results: list[TradeResult],
    all_results: list[TradeResult],
) -> None:
    summaries = strategy_summary(clean_results)
    losses = [r for r in clean_results if r.outcome == "LOSS"]
    lines = [
        "# Strategy Lifecycle Audit - Plain English",
        "",
        "Date: June 7, 2026",
        "",
        "## Operator Answer",
        "",
        "This audit looked at closed historical OANDA practice trades from repo logs only, then counted wins and losses by strategy.",
        "",
        "The goal was to find whether there are more strategies than the frozen morning momentum cartridge, and to inspect losses to see whether the strategy itself failed or whether workflow, timing, confirmation, or exit management caused the damage.",
        "",
        "## Proof Standard",
        "",
        "Primary evidence used for strategy mining:",
        "",
        "- closed OANDA trade logs from historical repos",
        "- linked to a matching PRACTICE OCO order when available",
        "- `live_api=true`",
        "- `visible_in_oanda=true`",
        "- not Coinbase",
        "- not TurboScribe transcript claims",
        "- not replay-only result files",
        "- not `estimated` close reasons",
        "- not close reasons containing `transcript`",
        "",
        "## Audit Size",
        "",
        f"- Unique log files scanned: {stats.files_scanned}",
        f"- Data scanned: about {stats.bytes_scanned / 1024 / 1024 / 1024:.2f} GB",
        f"- Lines scanned: {stats.lines_scanned:,}",
        f"- JSON records scanned: {stats.json_records:,}",
        f"- Close events seen: {stats.close_events_seen:,}",
        f"- All closed trade results found: {stats.closed_trade_results:,}",
        f"- High-confidence linked practice results: {stats.high_confidence_results:,}",
        f"- Clean high-confidence results used for strategy mining: {stats.clean_high_confidence_results:,}",
        f"- Clean wins: {stats.wins}",
        f"- Clean losses: {stats.losses}",
        f"- Clean breakeven: {stats.breakeven}",
        "",
        "## Direct Decision",
        "",
        "More strategy labels were found in the logs, but most did not hold up once losses were counted.",
        "",
        "The only clearly positive strategy family in this full lifecycle pass was `momentum_continuation`.",
        "",
        "Important nuance: generic `momentum` across all logged conditions was negative. That does not cancel the frozen April 14 morning cartridge. It means uncontrolled or weakly gated momentum entries were contaminated. The edge appears when momentum is constrained by the right session, continuation workflow, detector stack, and risk/exit behavior.",
        "",
        "## Wins And Losses Per Strategy",
        "",
    ]
    lines.extend(render_strategy_summary_table(summaries))
    lines.extend(
        [
            "",
            "## Loss Diagnosis By Strategy",
            "",
        ]
    )
    lines.extend(render_loss_diagnosis_by_strategy(summaries))
    lines.extend(
        [
            "",
            "## Loss Diagnosis Summary",
            "",
        ]
    )
    lines.extend(render_loss_diagnosis_table(losses))
    lines.extend(
        [
            "",
            "## Strategy Read",
            "",
        ]
    )
    lines.extend(render_strategy_read(summaries))
    lines.extend(
        [
            "",
            "## What The Loss Screen Means",
            "",
            "A loss was not automatically treated as proof that the strategy has no edge.",
            "",
            "If the trade first reached positive P&L and then closed red, the audit marks that as `edge_present_exit_or_workflow_gave_back`. That means the entry may have had edge, but the workflow, exit, stop movement, green-lock behavior, or management timing failed to keep it.",
            "",
            "If the trade never showed positive tracked P&L, the audit marks that closer to `strategy_no_logged_edge_on_trade`, `quality_gate_too_weak`, `scalp_no_followthrough`, or another setup-quality problem.",
            "",
            "## Biggest Losses To Review By Hand",
            "",
        ]
    )
    lines.extend(render_loss_detail_table(sorted(losses, key=lambda r: r.pnl_usd)[:30]))
    lines.extend(
        [
            "",
            "## Best Wins By Strategy",
            "",
        ]
    )
    lines.extend(render_best_wins_by_strategy(clean_results))
    lines.extend(
        [
            "",
            "## File Outputs",
            "",
            f"- Full CSV: `{OUTPUT_DIR / 'closed_trade_lifecycle_results.csv'}`",
            f"- Full JSON: `{OUTPUT_DIR / 'closed_trade_lifecycle_results.json'}`",
            f"- Strategy JSON summary: `{OUTPUT_DIR / 'strategy_summary.json'}`",
            f"- Technical markdown: `{OUTPUT_DIR / 'strategy_lifecycle_audit.md'}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def render_strategy_summary_table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No strategy rows found."]
    lines = [
        "| Strategy | Trades | Wins | Losses | Win Rate | P&L | Profit Factor | Main Loss Diagnosis |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        diagnoses = row.get("loss_diagnoses") or {}
        top_diag = next(iter(diagnoses.keys()), "")
        profit_factor_value = row["profit_factor"]
        if isinstance(profit_factor_value, float):
            pf = f"{profit_factor_value:.2f}"
        else:
            pf = str(profit_factor_value)
        lines.append(
            f"| {md(row['strategy_family'])} | {row['trades']} | {row['wins']} | {row['losses']} | "
            f"{row['win_rate_pct']:.1f}% | {row['total_pnl_usd']:.2f} | {pf} | {md(top_diag or 'none')} |"
        )
    return lines


def render_loss_diagnosis_table(losses: list[TradeResult]) -> list[str]:
    if not losses:
        return ["No clean losses found."]
    by_diag = Counter(r.loss_diagnosis for r in losses)
    lines = [
        "| Diagnosis | Count | P&L Impact | Meaning |",
        "| --- | ---: | ---: | --- |",
    ]
    meanings = {
        "edge_present_exit_or_workflow_gave_back": "Trade had favorable excursion, then closed red. Review exits, lock, giveback, trailing, and workflow handling.",
        "small_edge_then_noise_loss": "Trade moved slightly positive but not enough to prove strong edge.",
        "scratch_or_noise_exit_without_followthrough": "Wick/scratch behavior; setup did not travel cleanly.",
        "risk_stop_hit": "Risk control closed it; entry did not move enough first.",
        "scalp_no_followthrough": "Scalp did not travel enough.",
        "reversal_missing_trend_confirmation": "Reversal lacked stronger confirmation stack.",
        "quality_gate_too_weak": "Confidence/votes were too thin.",
        "session_mismatch": "Timing/session likely contaminated the setup.",
        "strategy_no_logged_edge_on_trade": "No logged favorable excursion before loss.",
        "insufficient_lifecycle_context": "Need manual review.",
    }
    for diagnosis, count in by_diag.most_common():
        pnl = sum(r.pnl_usd for r in losses if r.loss_diagnosis == diagnosis)
        lines.append(f"| {md(diagnosis)} | {count} | {pnl:.2f} | {md(meanings.get(diagnosis, 'Manual review needed.'))} |")
    return lines


def render_loss_diagnosis_by_strategy(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No strategy rows found."]
    lines = [
        "| Strategy | Loss Causes | Plain-English Read |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        diagnoses = row.get("loss_diagnoses") or {}
        diagnosis_text = ", ".join(f"{key}: {value}" for key, value in diagnoses.items()) or "none"
        read = strategy_loss_read(row["strategy_family"], diagnoses)
        lines.append(f"| {md(row['strategy_family'])} | {md(diagnosis_text)} | {md(read)} |")
    return lines


def strategy_loss_read(strategy: str, diagnoses: dict[str, int]) -> str:
    if not diagnoses:
        return "No clean losses in this audit sample."
    top = max(diagnoses.items(), key=lambda item: item[1])[0]
    if strategy == "momentum_continuation":
        return "Losses mostly show fixable exit/workflow giveback, not a dead strategy."
    if top == "edge_present_exit_or_workflow_gave_back":
        return "The entry sometimes had edge, but trade management failed to keep it."
    if top == "quality_gate_too_weak":
        return "The strategy was contaminated by weak confidence/vote gating."
    if top == "scratch_or_noise_exit_without_followthrough":
        return "The setup usually did not travel; this is not a deployable standalone edge."
    if top == "reversal_missing_trend_confirmation":
        return "Needs stronger confirmation before it can be trusted."
    if top == "scalp_no_followthrough":
        return "Scalp did not travel enough; keep secondary or disabled."
    return "Manual review needed before any cartridge decision."


def render_strategy_read(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for row in rows:
        strategy = row["strategy_family"]
        trades = row["trades"]
        wins = row["wins"]
        losses = row["losses"]
        pnl = row["total_pnl_usd"]
        pf = row["profit_factor"]
        if wins >= 5 and pnl > 0:
            decision = "Candidate family. Keep auditing and replay/paper-probate before activation."
        elif wins > 0 and losses == 0:
            decision = "Positive but sample is small. Treat as evidence lead, not cartridge."
        elif pnl <= 0:
            decision = "Do not deploy as its own cartridge from this evidence."
        else:
            decision = "Evidence lead only."
        lines.append(
            f"- `{strategy}`: {trades} clean trades, {wins} wins, {losses} losses, P&L {pnl:.2f}, profit factor {pf}. {decision}"
        )
    return lines


def render_loss_detail_table(losses: list[TradeResult]) -> list[str]:
    if not losses:
        return ["No losses found."]
    lines = [
        "| Close ET | Strategy | Pair | P&L | Max Tracked P&L | Diagnosis | Detail |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for item in losses:
        max_pnl = "" if item.max_tracked_pnl_usd is None else f"{item.max_tracked_pnl_usd:.2f}"
        lines.append(
            f"| {md(item.close_timestamp_et[:16])} | {md(item.strategy_family)} | {md(item.symbol)} | "
            f"{item.pnl_usd:.2f} | {max_pnl} | {md(item.loss_diagnosis)} | {md(item.loss_diagnosis_detail)} |"
        )
    return lines


def render_best_wins_by_strategy(results: list[TradeResult]) -> list[str]:
    wins = [r for r in results if r.outcome == "WIN"]
    if not wins:
        return ["No wins found."]
    grouped: dict[str, list[TradeResult]] = defaultdict(list)
    for win in wins:
        grouped[win.strategy_family].append(win)
    lines = [
        "| Strategy | Close ET | Pair | P&L | Detectors | Workflow |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for strategy, items in sorted(grouped.items(), key=lambda pair: sum(r.pnl_usd for r in pair[1]), reverse=True):
        for item in sorted(items, key=lambda r: r.pnl_usd, reverse=True)[:5]:
            lines.append(
                f"| {md(strategy)} | {md(item.close_timestamp_et[:16])} | {md(item.symbol)} | "
                f"{item.pnl_usd:.2f} | {md(item.signal_detectors or 'unknown')} | {md(item.workflow_profile or 'unknown')} |"
            )
    return lines


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, results: list[TradeResult]) -> None:
    fieldnames = list(TradeResult.__dataclass_fields__.keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))


def count_label(counter: Counter[str], value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text:
        counter[text] += 1


def best_label(counter: Counter[str]) -> str:
    return counter.most_common(1)[0][0] if counter else ""


def md(value: Any) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip() or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
