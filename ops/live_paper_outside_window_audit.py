from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = Path(os.environ.get("ODA_TRABOT_LEGACY_ROOT", "/home/rfing/READ_ONLY_LEGACY"))
OUTPUT_DIR = REPO_ROOT / "analysis" / "live_paper_outside_window_audit"
ET = ZoneInfo("America/New_York")

PROTECTED_START_ET = time.fromisoformat(os.environ.get("ODA_TRABOT_PROTECTED_START_ET", "03:00"))
PROTECTED_END_ET = time.fromisoformat(os.environ.get("ODA_TRABOT_PROTECTED_END_ET", "09:00"))

OANDA_PAIRS = {
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
    "USD_CHF",
    "AUD_USD",
    "USD_CAD",
    "NZD_USD",
}

LOG_FILE_RE = re.compile(
    r"(narration|practice_session|engine|autonomy|trade|position|order|fill|manager)",
    re.IGNORECASE,
)
SKIP_PATH_RE = re.compile(
    r"(/|\\)(\.git|__pycache__|node_modules|\.pytest_cache)(/|\\)|coinbase|turboscribe",
    re.IGNORECASE,
)
JSON_PREFIX_RE = re.compile(r"(\{.*\})")


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
    strategy: str = ""
    workflow_profile: str = ""
    timeframe: str = ""
    exit_profile: str = ""
    rules: str = ""
    max_tracked_pnl_usd: float | None = None
    max_tracked_pnl_timestamp_et: str = ""
    practice_order: bool = False
    live_api: bool = False
    visible_in_oanda: bool = False
    oco_order_id: str = ""
    source_open_line: int | None = None


@dataclass(frozen=True)
class CloseReceipt:
    source_path: str
    source_line: int
    source_repo: str
    confidence_class: str
    confidence_reason: str
    trade_id: str
    symbol: str
    close_timestamp_utc: str
    close_timestamp_et: str
    close_hour_et: int
    close_session_bucket: str
    event_type: str
    close_venue: str
    pnl_usd: float
    close_reason: str
    direction: str
    strategy: str
    workflow_profile: str
    signal_session: str
    signal_confidence: float | None
    signal_votes: int | None
    signal_detectors: str
    timeframe: str
    exit_profile: str
    open_timestamp_et: str
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    units: float | None
    max_tracked_pnl_usd: float | None
    max_tracked_pnl_timestamp_et: str
    practice_order: bool
    live_api: bool
    visible_in_oanda: bool
    duplicate_source_count: int = 1
    duplicate_sources: str = ""


@dataclass(frozen=True)
class AuditStats:
    legacy_root: str
    output_dir: str
    protected_window_et: str
    files_scanned: int
    bytes_scanned: int
    lines_scanned: int
    json_records: int
    close_events_seen: int
    positive_close_events_seen: int
    outside_window_positive_events: int
    unique_outside_window_positive_trades: int
    high_confidence_unique_trades: int
    clean_high_confidence_unique_trades: int
    runtime_paper_unique_trades: int
    generated_at_utc: str


def main() -> int:
    if not LEGACY_ROOT.exists():
        print(f"Missing legacy root: {LEGACY_ROOT}", file=sys.stderr)
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = discover_log_files(LEGACY_ROOT)
    receipts, stats_counter = scan_files(files)
    unique_receipts = dedupe_receipts(receipts)
    stats = AuditStats(
        legacy_root=str(LEGACY_ROOT),
        output_dir=str(OUTPUT_DIR),
        protected_window_et=f"{PROTECTED_START_ET.strftime('%H:%M')}-{PROTECTED_END_ET.strftime('%H:%M')}",
        files_scanned=len(files),
        bytes_scanned=sum(path.stat().st_size for path in files if path.exists()),
        lines_scanned=stats_counter["lines_scanned"],
        json_records=stats_counter["json_records"],
        close_events_seen=stats_counter["close_events_seen"],
        positive_close_events_seen=stats_counter["positive_close_events_seen"],
        outside_window_positive_events=stats_counter["outside_window_positive_events"],
        unique_outside_window_positive_trades=len(unique_receipts),
        high_confidence_unique_trades=sum(1 for item in unique_receipts if item.confidence_class == "high_confidence_practice_receipt"),
        clean_high_confidence_unique_trades=sum(
            1
            for item in unique_receipts
            if item.confidence_class == "high_confidence_practice_receipt" and is_clean_deployable_receipt(item)
        ),
        runtime_paper_unique_trades=sum(1 for item in unique_receipts if item.confidence_class == "runtime_paper_close"),
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )

    write_json(OUTPUT_DIR / "outside_window_profitable_trades.json", [asdict(item) for item in unique_receipts])
    write_json(OUTPUT_DIR / "scan_stats.json", asdict(stats))
    write_csv(OUTPUT_DIR / "outside_window_profitable_trades.csv", unique_receipts)
    write_report(OUTPUT_DIR / "outside_window_audit.md", stats, unique_receipts)

    print(f"Scanned {stats.files_scanned} legacy log files")
    print(f"Found {stats.unique_outside_window_positive_trades} unique profitable outside-window paper close receipts")
    print(f"High-confidence receipts: {stats.high_confidence_unique_trades}")
    print(f"Report: {OUTPUT_DIR / 'outside_window_audit.md'}")
    return 0


def discover_log_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        path_text = path.as_posix()
        if SKIP_PATH_RE.search(path_text):
            continue
        if path.suffix.lower() not in {".jsonl", ".log", ".out"}:
            continue
        if not LOG_FILE_RE.search(path.name) and "logs" not in path_text.lower():
            continue
        files.append(path)
    return dedupe_files_by_fingerprint(sorted(files, key=lambda item: (item.stat().st_size, item.as_posix())))


def dedupe_files_by_fingerprint(files: list[Path]) -> list[Path]:
    seen: set[tuple[int, str]] = set()
    unique: list[Path] = []
    for path in files:
        fingerprint = file_fingerprint(path)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(path)
    return unique


def file_fingerprint(path: Path) -> tuple[int, str]:
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(str(size).encode())
    with path.open("rb") as handle:
        digest.update(handle.read(65536))
        if size > 65536:
            handle.seek(max(0, size - 65536))
            digest.update(handle.read(65536))
    return size, digest.hexdigest()


def scan_files(files: list[Path]) -> tuple[list[CloseReceipt], Counter[str]]:
    receipts: list[CloseReceipt] = []
    stats: Counter[str] = Counter()

    for path in files:
        trades: dict[str, TradeContext] = {}
        file_context = {"practice_endpoint_seen": False, "non_placeholder_account_seen": False}
        try:
            with path.open("r", errors="replace") as handle:
                for line_number, line in enumerate(handle, 1):
                    stats["lines_scanned"] += 1
                    obj = parse_json_line(line)
                    if obj is None:
                        continue
                    stats["json_records"] += 1
                    update_file_context(obj, file_context)
                    receipt = process_event(path, line_number, obj, trades, file_context, stats)
                    if receipt is not None:
                        receipts.append(receipt)
        except (OSError, UnicodeDecodeError) as exc:
            stats[f"read_error:{path}"] += 1
            print(f"Could not scan {path}: {exc}", file=sys.stderr)

    return receipts, stats


def parse_json_line(line: str) -> dict[str, Any] | None:
    raw = line.strip()
    if not raw:
        return None
    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None
    match = JSON_PREFIX_RE.search(raw)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def process_event(
    path: Path,
    line_number: int,
    obj: dict[str, Any],
    trades: dict[str, TradeContext],
    file_context: dict[str, bool],
    stats: Counter[str],
) -> CloseReceipt | None:
    event_type = str(obj.get("event_type") or obj.get("kind") or obj.get("type") or "")
    details = obj.get("details") if isinstance(obj.get("details"), dict) else {}
    trade_id = str(details.get("trade_id") or details.get("close_trade_id") or obj.get("trade_id") or "").strip()
    symbol = normalize_symbol(obj.get("symbol") or details.get("symbol") or details.get("instrument") or details.get("close_symbol"))

    if trade_id:
        context = trades.setdefault(trade_id, TradeContext(trade_id=trade_id, symbol=symbol))
        if symbol and not context.symbol:
            context.symbol = symbol
        enrich_trade_context(context, event_type, obj, details, line_number)

    if event_type not in {"TRADE_CLOSED", "POSITION_CLOSED"}:
        return None

    stats["close_events_seen"] += 1
    pnl = numeric(details.get("pnl_usd") or details.get("realizedPL") or details.get("realized_pl") or details.get("pnl"))
    if pnl is None or pnl <= 0:
        return None
    stats["positive_close_events_seen"] += 1

    close_utc = parse_timestamp(obj.get("timestamp") or obj.get("timestamp_utc") or details.get("closed_time"))
    if close_utc is None:
        return None
    close_et = close_utc.astimezone(ET)
    if is_protected_window(close_et):
        return None
    stats["outside_window_positive_events"] += 1

    context = trades.get(trade_id, TradeContext(trade_id=trade_id, symbol=symbol))
    if symbol and not context.symbol:
        context.symbol = symbol
    if context.symbol not in OANDA_PAIRS:
        return None

    confidence_class, confidence_reason = classify_confidence(context, obj, file_context)
    return CloseReceipt(
        source_path=str(path),
        source_line=line_number,
        source_repo=source_repo_name(path),
        confidence_class=confidence_class,
        confidence_reason=confidence_reason,
        trade_id=trade_id,
        symbol=context.symbol,
        close_timestamp_utc=close_utc.isoformat(),
        close_timestamp_et=close_et.isoformat(),
        close_hour_et=close_et.hour,
        close_session_bucket=session_bucket(close_et),
        event_type=event_type,
        close_venue=str(obj.get("venue") or ""),
        pnl_usd=round(float(pnl), 4),
        close_reason=str(details.get("reason") or details.get("close_reason") or ""),
        direction=context.direction,
        strategy=context.strategy,
        workflow_profile=context.workflow_profile,
        signal_session=context.signal_session,
        signal_confidence=context.signal_confidence,
        signal_votes=context.signal_votes,
        signal_detectors=";".join(context.signal_detectors),
        timeframe=context.timeframe,
        exit_profile=context.exit_profile,
        open_timestamp_et=context.open_timestamp_et,
        entry_price=context.entry_price,
        stop_loss=context.stop_loss,
        take_profit=context.take_profit,
        units=context.units,
        max_tracked_pnl_usd=context.max_tracked_pnl_usd,
        max_tracked_pnl_timestamp_et=context.max_tracked_pnl_timestamp_et,
        practice_order=context.practice_order,
        live_api=context.live_api,
        visible_in_oanda=context.visible_in_oanda,
    )


def enrich_trade_context(
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
        context.direction = str(details.get("direction") or context.direction)
        context.strategy = str(details.get("strategy") or context.strategy)
        context.timeframe = str(details.get("timeframe") or context.timeframe)
        context.exit_profile = str(details.get("exit_profile") or context.exit_profile)
        context.rules = str(details.get("rules") or context.rules)
        pnl = numeric(details.get("pnl"))
        if pnl is not None and (context.max_tracked_pnl_usd is None or pnl > context.max_tracked_pnl_usd):
            context.max_tracked_pnl_usd = round(float(pnl), 4)
            context.max_tracked_pnl_timestamp_et = timestamp_utc.astimezone(ET).isoformat() if timestamp_utc else ""

    workflow_profile = details.get("workflow_profile") or details.get("workflow")
    if workflow_profile:
        context.workflow_profile = str(workflow_profile)
    strategy = details.get("strategy")
    if strategy and not context.strategy:
        context.strategy = str(strategy)


def classify_confidence(
    context: TradeContext,
    obj: dict[str, Any],
    file_context: dict[str, bool],
) -> tuple[str, str]:
    if context.practice_order and context.live_api and context.visible_in_oanda:
        return (
            "high_confidence_practice_receipt",
            "close event linked to matching PRACTICE OCO order with live_api=true and visible_in_oanda=true",
        )
    if file_context.get("practice_endpoint_seen") and file_context.get("non_placeholder_account_seen"):
        venue = str(obj.get("venue") or "")
        if venue in {"oanda", "trade_manager"}:
            return (
                "runtime_paper_close",
                "close event came from runtime log that initialized api-fxpractice.oanda.com with a non-placeholder account",
            )
    return (
        "unlinked_close_candidate",
        "positive close event found, but matching practice OCO receipt was not present in the scanned file",
    )


def update_file_context(obj: dict[str, Any], file_context: dict[str, bool]) -> None:
    details = obj.get("details") if isinstance(obj.get("details"), dict) else {}
    endpoint = str(details.get("endpoint") or "")
    account_id = str(details.get("account_id") or details.get("account") or "")
    if "api-fxpractice.oanda.com" in endpoint:
        file_context["practice_endpoint_seen"] = True
    if account_id and "REPLACE_WITH" not in account_id:
        file_context["non_placeholder_account_seen"] = True


def dedupe_receipts(receipts: list[CloseReceipt]) -> list[CloseReceipt]:
    preferred_event_rank = {"TRADE_CLOSED": 3, "POSITION_CLOSED": 2}
    confidence_rank = {
        "high_confidence_practice_receipt": 3,
        "runtime_paper_close": 2,
        "unlinked_close_candidate": 1,
    }
    grouped: dict[tuple[str, str, str, float], list[CloseReceipt]] = defaultdict(list)
    for receipt in receipts:
        close_minute = receipt.close_timestamp_et[:16]
        key = (receipt.trade_id, receipt.symbol, close_minute, round(receipt.pnl_usd, 4))
        grouped[key].append(receipt)

    unique: list[CloseReceipt] = []
    for group in grouped.values():
        best = max(
            group,
            key=lambda item: (
                confidence_rank.get(item.confidence_class, 0),
                preferred_event_rank.get(item.event_type, 0),
                item.close_venue == "oanda",
            ),
        )
        sources = sorted({item.source_path for item in group})
        unique.append(
            CloseReceipt(
                **{
                    **asdict(best),
                    "duplicate_source_count": len(sources),
                    "duplicate_sources": ";".join(sources),
                }
            )
        )
    return sorted(unique, key=lambda item: (item.close_timestamp_et, item.trade_id, item.symbol))


def is_clean_deployable_receipt(receipt: CloseReceipt) -> bool:
    reason = receipt.close_reason.lower()
    return reason != "estimated" and "transcript" not in reason


def write_report(path: Path, stats: AuditStats, receipts: list[CloseReceipt]) -> None:
    high_confidence = [item for item in receipts if item.confidence_class == "high_confidence_practice_receipt"]
    clean_high_confidence = [item for item in high_confidence if is_clean_deployable_receipt(item)]
    runtime = [item for item in receipts if item.confidence_class == "runtime_paper_close"]
    unlinked = [item for item in receipts if item.confidence_class == "unlinked_close_candidate"]

    lines = [
        "# Live Paper Outside-Window Audit",
        "",
        "This audit scans read-only legacy logs for profitable OANDA practice/live paper close receipts outside the frozen 3 AM-9 AM ET momentum cartridge window.",
        "",
        "## Guardrails",
        "",
        "- Accepted evidence is log data only, not replay/result/counterfactual JSON.",
        "- Coinbase and TurboScribe paths are excluded from this pass.",
        "- The protected cartridge window is treated as 03:00 through 08:59 ET; close receipts inside that window are excluded.",
        "- `high_confidence_practice_receipt` means a profitable close was linked to a matching `PRACTICE` OCO order with `live_api=true` and `visible_in_oanda=true`.",
        "- Cartridge candidates use a stricter clean subset that excludes `estimated` closes and close reasons containing `transcript`.",
        "- `runtime_paper_close` means a profitable close came from a runtime log initialized against `api-fxpractice.oanda.com`, but the matching OCO receipt was not present in that same scanned file.",
        "",
        "## Scan Stats",
        "",
        f"- Generated UTC: `{stats.generated_at_utc}`",
        f"- Legacy root: `{stats.legacy_root}`",
        f"- Files scanned: `{stats.files_scanned}`",
        f"- Lines scanned: `{stats.lines_scanned}`",
        f"- JSON records scanned: `{stats.json_records}`",
        f"- Close events seen: `{stats.close_events_seen}`",
        f"- Positive close events seen: `{stats.positive_close_events_seen}`",
        f"- Positive close events outside window: `{stats.outside_window_positive_events}`",
        f"- Unique profitable outside-window trades: `{stats.unique_outside_window_positive_trades}`",
        f"- High-confidence practice receipts: `{stats.high_confidence_unique_trades}`",
        f"- Clean high-confidence receipts for cartridge mining: `{stats.clean_high_confidence_unique_trades}`",
        f"- Runtime paper closes: `{stats.runtime_paper_unique_trades}`",
        "",
        "## Clean Cartridge Evidence",
        "",
    ]
    lines.extend(render_table(clean_high_confidence[:40]))
    lines.extend(
        [
            "",
            "## High-Confidence Winners",
            "",
            "This full set is retained for audit traceability. Cartridge candidates below use only the clean subset above.",
            "",
        ]
    )
    lines.extend(render_table(high_confidence[:40]))
    lines.extend(
        [
            "",
            "## Session Grouping",
            "",
        ]
    )
    lines.extend(render_group_summary(clean_high_confidence))
    lines.extend(
        [
            "",
            "## Candidate Cartridges",
            "",
        ]
    )
    lines.extend(render_candidate_cartridges(clean_high_confidence))
    lines.extend(
        [
            "",
            "## Runtime Paper Candidates",
            "",
            "These are useful leads, but they need manual review or broker-history confirmation before they become cartridges.",
            "",
        ]
    )
    lines.extend(render_table(runtime[:30]))
    lines.extend(
        [
            "",
            "## Unlinked Candidates",
            "",
            "These are not deployable evidence yet because the matching practice OCO receipt was not found in the scanned source.",
            "",
            f"- Count: `{len(unlinked)}`",
            "",
            "## Output Files",
            "",
            f"- JSON: `{OUTPUT_DIR / 'outside_window_profitable_trades.json'}`",
            f"- CSV: `{OUTPUT_DIR / 'outside_window_profitable_trades.csv'}`",
            f"- Stats: `{OUTPUT_DIR / 'scan_stats.json'}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def render_table(receipts: list[CloseReceipt]) -> list[str]:
    if not receipts:
        return ["No receipts found."]
    lines = [
        "| Close ET | Pair | P&L | Strategy | Workflow | Session | Detectors | Reason | Source |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in receipts:
        lines.append(
            "| "
            + " | ".join(
                [
                    md(item.close_timestamp_et[:16]),
                    md(item.symbol),
                    f"{item.pnl_usd:.2f}",
                    md(item.strategy or "unknown"),
                    md(item.workflow_profile or "unknown"),
                    md(item.close_session_bucket),
                    md(item.signal_detectors or "unknown"),
                    md(item.close_reason or "unknown"),
                    md(item.source_repo),
                ]
            )
            + " |"
        )
    return lines


def render_group_summary(receipts: list[CloseReceipt]) -> list[str]:
    if not receipts:
        return ["No high-confidence receipts to group."]
    groups: dict[tuple[str, str, str], list[CloseReceipt]] = defaultdict(list)
    for item in receipts:
        strategy = item.strategy or "unknown"
        groups[(item.close_session_bucket, strategy, item.symbol)].append(item)

    lines = [
        "| Bucket | Strategy | Pair | Wins | P&L Sum | Avg P&L | Best P&L |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    sorted_groups = sorted(
        groups.items(),
        key=lambda pair: (len(pair[1]), sum(item.pnl_usd for item in pair[1])),
        reverse=True,
    )
    for (bucket, strategy, symbol), items in sorted_groups[:30]:
        pnl_sum = sum(item.pnl_usd for item in items)
        lines.append(
            f"| {md(bucket)} | {md(strategy)} | {md(symbol)} | {len(items)} | "
            f"{pnl_sum:.2f} | {pnl_sum / len(items):.2f} | {max(item.pnl_usd for item in items):.2f} |"
        )
    return lines


def render_candidate_cartridges(receipts: list[CloseReceipt]) -> list[str]:
    if not receipts:
        return ["No cartridge candidate cleared the high-confidence evidence bar."]

    grouped: dict[tuple[str, str], list[CloseReceipt]] = defaultdict(list)
    for item in receipts:
        grouped[(item.close_session_bucket, item.strategy or "unknown")].append(item)

    candidates: list[tuple[tuple[str, str], list[CloseReceipt]]] = []
    for key, items in grouped.items():
        pairs = {item.symbol for item in items}
        if len(items) >= 2 or len(pairs) >= 2:
            candidates.append((key, items))

    if not candidates:
        return [
            "No deployable cartridge yet. The high-confidence outside-window winners are singletons, so they should be replayed and paper-probated before activation."
        ]

    lines = [
        "| Candidate | Evidence | Pairs | P&L Sum | Activation Stance |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for (bucket, strategy), items in sorted(
        candidates,
        key=lambda pair: (len(pair[1]), sum(item.pnl_usd for item in pair[1])),
        reverse=True,
    ):
        pairs = ", ".join(sorted({item.symbol for item in items}))
        pnl_sum = sum(item.pnl_usd for item in items)
        stance = "candidate-only; build replay fixture, then paper probation"
        name = f"{bucket}_{strategy}".replace(" ", "_").replace(":", "").lower()
        lines.append(f"| {md(name)} | {len(items)} wins | {md(pairs)} | {pnl_sum:.2f} | {md(stance)} |")
    return lines


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, receipts: list[CloseReceipt]) -> None:
    fieldnames = list(asdict(receipts[0]).keys()) if receipts else list(CloseReceipt.__dataclass_fields__.keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for receipt in receipts:
            writer.writerow(asdict(receipt))


def parse_timestamp(raw: Any) -> datetime | None:
    if raw in {None, ""}:
        return None
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    text = str(raw).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_protected_window(timestamp_et: datetime) -> bool:
    current = timestamp_et.time().replace(tzinfo=None)
    return PROTECTED_START_ET <= current < PROTECTED_END_ET


def session_bucket(timestamp_et: datetime) -> str:
    current = timestamp_et.time().replace(tzinfo=None)
    if time(9, 0) <= current < time(11, 30):
        return "post_london_overlap_09_1130"
    if time(11, 30) <= current < time(14, 0):
        return "midday_new_york_1130_14"
    if time(14, 0) <= current < time(17, 0):
        return "ny_afternoon_close_14_17"
    if time(17, 0) <= current or current < time(0, 0):
        return "rollover_17_00"
    if time(0, 0) <= current < time(3, 0):
        return "tokyo_late_pre_london_00_03"
    return "outside_window_other"


def normalize_symbol(raw: Any) -> str:
    if raw is None:
        return ""
    text = str(raw).strip().upper().replace("/", "_").replace("-", "_")
    if text in OANDA_PAIRS:
        return text
    match = re.search(r"\b[A-Z]{3}_[A-Z]{3}\b", text)
    return match.group(0) if match else text


def numeric(raw: Any) -> float | None:
    if raw in {None, ""}:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace(",", ""))
    except ValueError:
        return None


def source_repo_name(path: Path) -> str:
    try:
        relative = path.relative_to(LEGACY_ROOT)
    except ValueError:
        return path.parent.name
    return relative.parts[0] if relative.parts else path.parent.name


def md(value: Any) -> str:
    text = str(value).replace("|", "/").replace("\n", " ").strip()
    return text or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
