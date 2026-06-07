from __future__ import annotations

from dataclasses import dataclass

from .management import ExitPlan, build_exit_plan
from .oanda import OandaPriceSnapshot
from .planning import TradePlan
from .strategy_pack import StrategyPack, load_strategy_pack


@dataclass(frozen=True)
class OrderPreview:
    pair: str
    direction: str
    units: int
    entry_price: float
    stop_price: float
    target_price: float
    exit_plan: ExitPlan

    def to_oanda_payload(self) -> dict:
        signed_units = str(self.units if self.direction == "BUY" else -self.units)
        return {
            "order": {
                "type": "MARKET",
                "instrument": self.pair,
                "units": signed_units,
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
                "takeProfitOnFill": {"price": _fmt_price(self.target_price)},
                "stopLossOnFill": {"price": _fmt_price(self.stop_price)},
            }
        }


class OrderPreviewBuilder:
    def __init__(self, strategy_pack: StrategyPack | None = None) -> None:
        self._strategy_pack = strategy_pack or load_strategy_pack()

    def build(self, plan: TradePlan, price: OandaPriceSnapshot) -> OrderPreview:
        exit_plan = build_exit_plan(plan, strategy_pack=self._strategy_pack)
        entry_price = price.ask if plan.direction == "BUY" else price.bid
        pip = _pip_size(plan.pair)

        if plan.direction == "BUY":
            stop_price = entry_price - (exit_plan.stop_pips * pip)
            target_price = entry_price + (exit_plan.target_pips * pip)
        else:
            stop_price = entry_price + (exit_plan.stop_pips * pip)
            target_price = entry_price - (exit_plan.target_pips * pip)

        return OrderPreview(
            pair=plan.pair,
            direction=plan.direction,
            units=plan.units,
            entry_price=round(entry_price, 5 if pip == 0.0001 else 3),
            stop_price=round(stop_price, 5 if pip == 0.0001 else 3),
            target_price=round(target_price, 5 if pip == 0.0001 else 3),
            exit_plan=exit_plan,
        )


def _pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 0.0001


def _fmt_price(price: float) -> str:
    return f"{price:.5f}".rstrip("0").rstrip(".")
