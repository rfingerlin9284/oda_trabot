from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, time

from .router import to_eastern
from .strategy_pack import StrategyPack, load_strategy_pack


CARTRIDGE_ROUTING_ENV = "ODA_TRABOT_CARTRIDGE_ROUTING"
MANUAL_ROUTING_VALUE = "manual"


@dataclass(frozen=True)
class CartridgeWindow:
    window_id: str
    pack_name: str
    label: str
    start_et: time
    end_et: time
    end_inclusive: bool = False

    def contains(self, moment: datetime) -> bool:
        current = to_eastern(moment).time()
        if self.start_et <= self.end_et:
            if self.end_inclusive:
                return self.start_et <= current <= self.end_et
            return self.start_et <= current < self.end_et
        if self.end_inclusive:
            return current >= self.start_et or current <= self.end_et
        return current >= self.start_et or current < self.end_et


@dataclass(frozen=True)
class CartridgeSelection:
    observed_at_et: datetime
    routing_mode: str
    entry_allowed: bool
    window: CartridgeWindow | None
    strategy_pack: StrategyPack | None
    reason: str

    @property
    def pack_id(self) -> str:
        if self.strategy_pack is None:
            return "NO_ACTIVE_ENTRY_CARTRIDGE"
        return self.strategy_pack.pack_id

    @property
    def label(self) -> str:
        if self.strategy_pack is None:
            return "No active entry cartridge"
        return self.strategy_pack.label


DEFAULT_CARTRIDGE_WINDOWS: tuple[CartridgeWindow, ...] = (
    CartridgeWindow(
        window_id="frozen_3am_830am_momentum",
        pack_name="april14_momentum_3am_9am",
        label="Frozen 3 AM-8:30 AM ET April 14 momentum cartridge",
        start_et=time(3, 0),
        end_et=time(8, 30, 59, 999999),
        end_inclusive=True,
    ),
    CartridgeWindow(
        window_id="post_9am_ema_fib_momentum_continuation",
        pack_name="post_9am_ema_fib_momentum_continuation",
        label="Post-9 AM EMA/Fibonacci momentum continuation cartridge",
        start_et=time(9, 0),
        end_et=time(11, 30),
    ),
)


def select_active_cartridge(
    observed_at: datetime,
    *,
    routing_mode: str | None = None,
    windows: tuple[CartridgeWindow, ...] = DEFAULT_CARTRIDGE_WINDOWS,
) -> CartridgeSelection:
    selected_mode = (routing_mode or os.getenv(CARTRIDGE_ROUTING_ENV, "auto")).strip().lower()
    observed_at_et = to_eastern(observed_at)
    if selected_mode == MANUAL_ROUTING_VALUE:
        pack = load_strategy_pack()
        return CartridgeSelection(
            observed_at_et=observed_at_et,
            routing_mode=selected_mode,
            entry_allowed=True,
            window=None,
            strategy_pack=pack,
            reason=f"manual routing selected strategy pack {pack.pack_id}",
        )

    for window in windows:
        if window.contains(observed_at_et):
            pack = load_strategy_pack(window.pack_name)
            return CartridgeSelection(
                observed_at_et=observed_at_et,
                routing_mode=selected_mode,
                entry_allowed=True,
                window=window,
                strategy_pack=pack,
                reason=f"active entry cartridge window: {window.label}",
            )

    return CartridgeSelection(
        observed_at_et=observed_at_et,
        routing_mode=selected_mode,
        entry_allowed=False,
        window=None,
        strategy_pack=None,
        reason="no active entry cartridge window; manage existing trades only",
    )


def load_management_strategy_pack(selection: CartridgeSelection) -> StrategyPack:
    if selection.strategy_pack is not None:
        return selection.strategy_pack
    return load_strategy_pack("april14_momentum_3am_9am")
