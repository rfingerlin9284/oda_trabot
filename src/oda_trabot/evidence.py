from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HistoricalTradeReceipt:
    symbol: str
    strategy: str
    pnl_usd: float
    entry_time_et: str
    exit_reason: str
    source_variant: str
    source_label: str
    outcome: str


@dataclass(frozen=True)
class HistoricalWindow:
    variant: str
    label: str
    window_et_from: str
    window_et_to: str
    realized_pnl_usd: float
    closed_trades: int
    wins: int
    losses: int
    by_strategy: dict[str, float]
    top_winners: tuple[HistoricalTradeReceipt, ...]
    top_losers: tuple[HistoricalTradeReceipt, ...]


@dataclass(frozen=True)
class EvidenceSummary:
    window_count: int
    best_window_label: str
    best_window_pnl_usd: float
    pnl_by_strategy: dict[str, float]
    pnl_by_symbol: dict[str, float]
    best_trade: HistoricalTradeReceipt | None


def load_counterfactual_windows(path: str | Path) -> tuple[HistoricalWindow, ...]:
    raw = Path(path).read_text()
    if raw.startswith("USER OVERRIDE:"):
        raw = "\n".join(line for line in raw.splitlines() if not line.startswith("USER OVERRIDE:"))
    payload = json.loads(raw)

    windows: list[HistoricalWindow] = []
    for report in payload.get("reports", []):
        top_winners = tuple(
            HistoricalTradeReceipt(
                symbol=item["symbol"],
                strategy=item["strategy"],
                pnl_usd=float(item.get("pnl_usd", item.get("pnl", 0.0))),
                entry_time_et=str(item.get("entry_time_et", item.get("entry_time", ""))),
                exit_reason=str(item["exit_reason"]),
                source_variant=str(report["variant"]),
                source_label=str(report["label"]),
                outcome="winner",
            )
            for item in report.get("top_winners", [])
        )
        top_losers = tuple(
            HistoricalTradeReceipt(
                symbol=item["symbol"],
                strategy=item["strategy"],
                pnl_usd=float(item.get("pnl_usd", item.get("pnl", 0.0))),
                entry_time_et=str(item.get("entry_time_et", item.get("entry_time", ""))),
                exit_reason=str(item["exit_reason"]),
                source_variant=str(report["variant"]),
                source_label=str(report["label"]),
                outcome="loser",
            )
            for item in report.get("top_losers", [])
        )
        window_et = report.get("window_et", {})
        if isinstance(window_et, dict):
            window_from = str(window_et.get("from", ""))
            window_to = str(window_et.get("to", ""))
        else:
            parts = str(window_et).split(" to ")
            window_from = parts[0] if parts else ""
            window_to = parts[1] if len(parts) > 1 else ""

        windows.append(
            HistoricalWindow(
                variant=str(report["variant"]),
                label=str(report["label"]),
                window_et_from=window_from,
                window_et_to=window_to,
                realized_pnl_usd=float(report["realized_pnl_usd"]),
                closed_trades=int(report["closed_trades"]),
                wins=int(report["wins"]),
                losses=int(report["losses"]),
                by_strategy={k: float(v) for k, v in report.get("by_strategy", {}).items()},
                top_winners=top_winners,
                top_losers=top_losers,
            )
        )
    return tuple(windows)


def summarize_windows(windows: tuple[HistoricalWindow, ...]) -> EvidenceSummary:
    pnl_by_strategy: defaultdict[str, float] = defaultdict(float)
    pnl_by_symbol: defaultdict[str, float] = defaultdict(float)
    best_trade: HistoricalTradeReceipt | None = None

    for window in windows:
        for strategy, pnl in window.by_strategy.items():
            pnl_by_strategy[strategy] += pnl
        for trade in (*window.top_winners, *window.top_losers):
            pnl_by_symbol[trade.symbol] += trade.pnl_usd
            if best_trade is None or trade.pnl_usd > best_trade.pnl_usd:
                best_trade = trade

    best_window = max(windows, key=lambda window: window.realized_pnl_usd)
    return EvidenceSummary(
        window_count=len(windows),
        best_window_label=best_window.label,
        best_window_pnl_usd=best_window.realized_pnl_usd,
        pnl_by_strategy=dict(sorted(pnl_by_strategy.items(), key=lambda item: item[1], reverse=True)),
        pnl_by_symbol=dict(sorted(pnl_by_symbol.items(), key=lambda item: item[1], reverse=True)),
        best_trade=best_trade,
    )


def top_receipts_by_symbol(windows: tuple[HistoricalWindow, ...]) -> dict[str, list[HistoricalTradeReceipt]]:
    grouped: defaultdict[str, list[HistoricalTradeReceipt]] = defaultdict(list)
    for window in windows:
        for trade in (*window.top_winners, *window.top_losers):
            grouped[trade.symbol].append(trade)
    return {
        symbol: sorted(receipts, key=lambda trade: trade.pnl_usd, reverse=True)
        for symbol, receipts in grouped.items()
    }


def dominant_workflows(windows: tuple[HistoricalWindow, ...]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for window in windows:
        for trade in window.top_winners:
            counts[trade.strategy] += 1
    return dict(counts.most_common())
