from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from oda_trabot.evidence import (  # noqa: E402
    HistoricalTradeReceipt,
    HistoricalWindow,
    dominant_workflows,
    load_counterfactual_windows,
    summarize_windows,
    top_receipts_by_symbol,
)


TURBOSCRIBE_DIR = REPO_ROOT / "analysis" / "turboscribe"
OUTPUT_DIR = REPO_ROOT / "analysis" / "evidence_audit"
LEGACY_ROOT = Path(os.environ.get("ODA_TRABOT_LEGACY_ROOT", "/home/rfing/READ_ONLY_LEGACY"))

KNOWN_EVIDENCE_SOURCES = {
    "april14_baseline": Path(
        "/home/rfing/READ_ONLY_LEGACY/backups/"
        "RESTORED_PRE10AM_TRANSFER_READY_20260430_025439/repos/"
        "OAD_DEV/analysis/oanda_loss_manager_counterfactual_apr14_session_20260421.json"
    ),
    "v1c002_challenger": Path(
        "/home/rfing/READ_ONLY_LEGACY/V1C002_APRIL14_EDGE_REBUILD_20260508/"
        "evidence/candidate_current_session_counterfactuals.json"
    ),
}

TRADE_EVIDENCE_RE = re.compile(
    r"(counterfactual|receipt|trade|trades|pnl|profit|performance|backtest|"
    r"result|results|report|oanda|paper|live|fills?)",
    re.IGNORECASE,
)
SOURCE_EXTENSIONS = {".json", ".jsonl", ".csv", ".txt", ".md", ".log"}
MAX_LEGACY_CANDIDATES = int(os.environ.get("ODA_TRABOT_AUDIT_MAX_CANDIDATES", "350"))


@dataclass(frozen=True)
class EvidenceSourceSummary:
    source_id: str
    path: str
    exists: bool
    window_count: int = 0
    best_window_label: str = ""
    best_window_pnl_usd: float = 0.0
    best_trade: dict[str, Any] | None = None
    pnl_by_strategy: dict[str, float] | None = None
    pnl_by_symbol: dict[str, float] | None = None
    winning_workflow_counts: dict[str, int] | None = None
    best_receipts_by_symbol: dict[str, list[dict[str, Any]]] | None = None


@dataclass(frozen=True)
class LegacyCandidateFile:
    path: str
    size_bytes: int
    mtime_utc: str
    reason: str


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if hasattr(value, "__len__"):
        return len(value)
    return 0


def _utc_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _receipt_to_dict(receipt: HistoricalTradeReceipt) -> dict[str, Any]:
    return asdict(receipt)


def _window_to_rows(source_id: str, windows: tuple[HistoricalWindow, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in windows:
        for outcome, receipts in (("winner", window.top_winners), ("loser", window.top_losers)):
            for receipt in receipts:
                rows.append(
                    {
                        "source_id": source_id,
                        "window_variant": window.variant,
                        "window_label": window.label,
                        "window_from_et": window.window_et_from,
                        "window_to_et": window.window_et_to,
                        "window_realized_pnl_usd": window.realized_pnl_usd,
                        "window_closed_trades": window.closed_trades,
                        "window_wins": window.wins,
                        "window_losses": window.losses,
                        "outcome": outcome,
                        **_receipt_to_dict(receipt),
                    }
                )
    return rows


def summarize_known_sources() -> tuple[list[EvidenceSourceSummary], list[dict[str, Any]]]:
    summaries: list[EvidenceSourceSummary] = []
    receipt_rows: list[dict[str, Any]] = []

    for source_id, path in KNOWN_EVIDENCE_SOURCES.items():
        if not path.exists():
            summaries.append(EvidenceSourceSummary(source_id=source_id, path=str(path), exists=False))
            continue

        windows = load_counterfactual_windows(path)
        summary = summarize_windows(windows)
        receipts = top_receipts_by_symbol(windows)
        receipt_rows.extend(_window_to_rows(source_id, windows))

        best_receipts = {
            symbol: [_receipt_to_dict(receipt) for receipt in symbol_receipts[:5]]
            for symbol, symbol_receipts in receipts.items()
        }
        summaries.append(
            EvidenceSourceSummary(
                source_id=source_id,
                path=str(path),
                exists=True,
                window_count=summary.window_count,
                best_window_label=summary.best_window_label,
                best_window_pnl_usd=summary.best_window_pnl_usd,
                best_trade=_receipt_to_dict(summary.best_trade) if summary.best_trade else None,
                pnl_by_strategy=summary.pnl_by_strategy,
                pnl_by_symbol=summary.pnl_by_symbol,
                winning_workflow_counts=dominant_workflows(windows),
                best_receipts_by_symbol=best_receipts,
            )
        )

    return summaries, receipt_rows


def summarize_turboscribe_inventory() -> dict[str, Any]:
    extraction_summary = _load_json(TURBOSCRIBE_DIR / "extraction_summary.json")
    archive_inventory = _load_json(TURBOSCRIBE_DIR / "archive_inventory.json")
    zip_manifest = _load_json(TURBOSCRIBE_DIR / "zip_manifest_turboscribe_hits_wsl_home.json")
    strategy_specs = _load_json(TURBOSCRIBE_DIR / "strategy_specs.json")

    rows: list[dict[str, str]] = []
    with (TURBOSCRIBE_DIR / "document_inventory.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)

    relevance_counts = Counter(row.get("trading_relevance", "") for row in rows)
    term_counts: Counter[str] = Counter()
    archive_doc_counts: Counter[str] = Counter()
    read_errors = []

    for row in rows:
        archive_doc_counts[row.get("archive_sha256_prefix", "")] += 1
        for term in row.get("relevance_hits", "").split(";"):
            if term:
                term_counts[term] += 1
        if row.get("read_error"):
            read_errors.append(row)

    top_documents = sorted(
        rows,
        key=lambda row: (
            row.get("trading_relevance") == "trading_candidate",
            int(row.get("chars") or 0),
            len(row.get("relevance_hits", "").split(";")),
        ),
        reverse=True,
    )[:25]

    return {
        "extraction_summary": extraction_summary,
        "archive_inventory_counts": {
            "turboscribe_named_matches": _count(archive_inventory.get("turboscribe_named_matches")),
            "zip_matches": _count(archive_inventory.get("zip_matches")),
            "unique_archive_hashes": archive_inventory.get("unique_archive_hashes"),
            "non_zip_matches": _count(archive_inventory.get("non_zip_matches")),
        },
        "zip_manifest_counts": {
            "zip_files_scanned": zip_manifest.get("zip_files_scanned"),
            "hits": len(zip_manifest.get("hits", [])),
            "bad_turboscribe_named_zips": len(zip_manifest.get("bad_turboscribe_named_zips", [])),
        },
        "document_counts": {
            "total_documents": len(rows),
            "relevance_counts": dict(relevance_counts),
            "archives_with_documents": len(archive_doc_counts),
            "read_errors": len(read_errors),
        },
        "top_relevance_terms": dict(term_counts.most_common(25)),
        "top_documents": top_documents,
        "strategy_count": len(strategy_specs.get("strategies", [])),
        "strategy_ids": [item.get("strategy_id") for item in strategy_specs.get("strategies", [])],
    }


def scan_legacy_candidate_files() -> list[LegacyCandidateFile]:
    candidates: list[LegacyCandidateFile] = []
    if not LEGACY_ROOT.exists():
        return candidates

    for root, dirnames, filenames in os.walk(LEGACY_ROOT):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in {".git", "__pycache__", "node_modules", ".venv", "venv"}
        ]
        for filename in filenames:
            path = Path(root) / filename
            if path.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            rel = str(path)
            if not TRADE_EVIDENCE_RE.search(rel):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            candidates.append(
                LegacyCandidateFile(
                    path=rel,
                    size_bytes=stat.st_size,
                    mtime_utc=_utc_from_timestamp(stat.st_mtime),
                    reason="filename/path matches trade evidence terms",
                )
            )

    candidates.sort(key=lambda item: (item.mtime_utc, item.size_bytes), reverse=True)
    return candidates[:MAX_LEGACY_CANDIDATES]


def write_json_report(payload: dict[str, Any]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "legacy_evidence_audit.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def write_markdown_report(payload: dict[str, Any]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "legacy_evidence_audit.md"
    sources = payload["known_trade_sources"]
    turbo = payload["turboscribe_inventory"]
    candidates = payload["legacy_candidate_files"]

    lines = [
        "# Legacy Evidence Audit",
        "",
        f"Generated UTC: `{payload['generated_at_utc']}`",
        "",
        "## Scope",
        "",
        "- Legacy folders are read-only evidence.",
        "- Transcript rules enter runtime only through strategy packs.",
        "- Old repo code is never imported directly into the clean bot.",
        "- Live-money activation is outside this audit; OANDA practice only.",
        "",
        "## TurboScribe Coverage",
        "",
        f"- Zip files scanned: `{turbo['extraction_summary']['wsl_home_zip_manifest_scan']['zip_files_scanned']}`",
        f"- TurboScribe-related zip hits: `{turbo['extraction_summary']['wsl_home_zip_manifest_scan']['turboscribe_related_hits']}`",
        f"- Direct TurboScribe-named zip hits: `{turbo['extraction_summary']['wsl_home_zip_manifest_scan']['direct_turboscribe_named_zip_hits']}`",
        f"- Unique archive hashes: `{turbo['archive_inventory_counts']['unique_archive_hashes']}`",
        f"- Indexed transcript/docs rows: `{turbo['document_counts']['total_documents']}`",
        "",
        "Top transcript evidence terms:",
    ]
    for term, count in list(turbo["top_relevance_terms"].items())[:12]:
        lines.append(f"- `{term}`: `{count}`")

    lines.extend(["", "## Verified Trade Sources", ""])
    for source in sources:
        if not source["exists"]:
            lines.append(f"- `{source['source_id']}` missing: `{source['path']}`")
            continue
        lines.append(
            f"- `{source['source_id']}`: best `{source['best_window_label']}` "
            f"at `${source['best_window_pnl_usd']:.2f}` across `{source['window_count']}` windows"
        )
        lines.append(f"  - P&L by strategy: `{source['pnl_by_strategy']}`")
        lines.append(f"  - P&L by symbol: `{source['pnl_by_symbol']}`")

    lines.extend(
        [
            "",
            "## What Can Be Promoted",
            "",
            "Promote only evidence that has all of these:",
            "",
            "1. A source file path and hash or deterministic source id.",
            "2. A closed-trade receipt or replay window with P&L, symbol, session, and strategy.",
            "3. A plain-English rule that maps to a deterministic detector.",
            "4. A strategy-pack entry, not broker-code edits.",
            "5. A replay receipt against the known edge window.",
            "6. A paper-trading receipt before any stronger activation.",
            "",
            "## Current Replication Thesis",
            "",
            "- Keep the clean bot session-shaped.",
            "- Prioritize London and early New York, especially 3 AM to 9 AM ET.",
            "- Treat momentum/continuation as the primary money lane.",
            "- Treat scalp as a narrow helper unless receipts prove it is carrying expectancy.",
            "- Add top-down bias, 9 EMA first-touch quality, false-break filters, and range/chop filters through strategy packs.",
            "- Keep order block, liquidity sweep, FVG, and orderflow logic disabled until deterministic detectors and replay data exist.",
            "",
            "## Legacy Candidate File Queue",
            "",
            f"Candidate files listed: `{len(candidates)}`",
        ]
    )
    for candidate in candidates[:40]:
        lines.append(f"- `{candidate['path']}`")

    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> None:
    known_sources, receipt_rows = summarize_known_sources()
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "legacy_root": str(LEGACY_ROOT),
        "known_trade_sources": [asdict(source) for source in known_sources],
        "known_receipt_rows": receipt_rows,
        "turboscribe_inventory": summarize_turboscribe_inventory(),
        "legacy_candidate_files": [asdict(item) for item in scan_legacy_candidate_files()],
        "promotion_policy": {
            "allowed_path": "transcript/source -> structured strategy spec -> deterministic detector -> replay -> paper receipts -> strategy pack",
            "blocked_paths": [
                "direct import from legacy repos",
                "broker-code edits from transcript claims",
                "promotion from screenshots or claims without receipts",
                "mixing Coinbase or multi-broker logic into OANDA practice runtime",
            ],
        },
    }
    json_path = write_json_report(payload)
    md_path = write_markdown_report(payload)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
