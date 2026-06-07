from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PRACTICE_API_BASE = "https://api-fxpractice.oanda.com"


@dataclass(frozen=True)
class OandaPracticeConfig:
    account_id: str
    api_token: str
    api_base: str = PRACTICE_API_BASE
    timeout_seconds: int = 20

    @classmethod
    def from_env_file(cls, env_path: str | Path | None = None) -> "OandaPracticeConfig":
        env_values = _read_env_file(env_path)
        account_id = (
            env_values.get("OANDA_ACCOUNT_ID")
            or env_values.get("OANDA_PRACTICE_ACCOUNT_ID")
            or os.getenv("OANDA_ACCOUNT_ID")
            or os.getenv("OANDA_PRACTICE_ACCOUNT_ID")
        )
        api_token = (
            env_values.get("OANDA_TOKEN")
            or env_values.get("OANDA_PRACTICE_TOKEN")
            or os.getenv("OANDA_TOKEN")
            or os.getenv("OANDA_PRACTICE_TOKEN")
        )
        api_base = (
            env_values.get("OANDA_BASE_URL")
            or env_values.get("OANDA_API_BASE")
            or os.getenv("OANDA_BASE_URL")
            or os.getenv("OANDA_API_BASE")
            or PRACTICE_API_BASE
        )
        timeout_seconds = int(
            env_values.get("OANDA_TIMEOUT_SECONDS")
            or os.getenv("OANDA_TIMEOUT_SECONDS")
            or 20
        )
        if not account_id or not api_token:
            raise RuntimeError("Missing OANDA practice credentials")
        if "fxtrade" in api_base:
            raise RuntimeError("Live-money OANDA endpoint is not allowed in ODA_TRABOT")
        return cls(
            account_id=account_id,
            api_token=api_token,
            api_base=api_base,
            timeout_seconds=timeout_seconds,
        )


@dataclass(frozen=True)
class OandaAccountSnapshot:
    account_id: str
    currency: str
    balance: float
    nav: float
    unrealized_pl: float
    margin_used: float
    margin_available: float
    open_trade_count: int
    open_position_count: int


@dataclass(frozen=True)
class OandaPositionSnapshot:
    pair: str
    direction: str
    units: int
    average_price: float
    unrealized_pl: float


@dataclass(frozen=True)
class OandaPriceSnapshot:
    pair: str
    bid: float
    ask: float
    spread_pips: float


@dataclass(frozen=True)
class OandaTradeSnapshot:
    trade_id: str
    pair: str
    direction: str
    units: int
    entry_price: float
    unrealized_pl: float
    stop_price: float | None
    target_price: float | None


class OandaPracticeClient:
    def __init__(self, config: OandaPracticeConfig) -> None:
        self._config = config
        if "fxtrade" in self._config.api_base:
            raise RuntimeError("OandaPracticeClient refuses live-money endpoints")

    def account_summary(self) -> OandaAccountSnapshot:
        payload = self._request_json(f"/v3/accounts/{self._config.account_id}/summary")
        account = payload["account"]
        return OandaAccountSnapshot(
            account_id=str(account["id"]),
            currency=str(account["currency"]),
            balance=float(account["balance"]),
            nav=float(account["NAV"]),
            unrealized_pl=float(account["unrealizedPL"]),
            margin_used=float(account["marginUsed"]),
            margin_available=float(account["marginAvailable"]),
            open_trade_count=int(account["openTradeCount"]),
            open_position_count=int(account["openPositionCount"]),
        )

    def open_positions(self) -> tuple[OandaPositionSnapshot, ...]:
        payload = self._request_json(f"/v3/accounts/{self._config.account_id}/openPositions")
        positions: list[OandaPositionSnapshot] = []
        for position in payload.get("positions", []):
            long_units = int(float(position["long"]["units"]))
            short_units = int(float(position["short"]["units"]))
            if long_units > 0:
                positions.append(
                    OandaPositionSnapshot(
                        pair=str(position["instrument"]),
                        direction="BUY",
                        units=long_units,
                        average_price=float(position["long"]["averagePrice"]),
                        unrealized_pl=float(position["long"]["unrealizedPL"]),
                    )
                )
            if short_units < 0:
                positions.append(
                    OandaPositionSnapshot(
                        pair=str(position["instrument"]),
                        direction="SELL",
                        units=abs(short_units),
                        average_price=float(position["short"]["averagePrice"]),
                        unrealized_pl=float(position["short"]["unrealizedPL"]),
                    )
                )
        return tuple(positions)

    def open_trades(self) -> tuple[OandaTradeSnapshot, ...]:
        payload = self._request_json(f"/v3/accounts/{self._config.account_id}/openTrades")
        return tuple(
            _parse_open_trade_snapshot(trade)
            for trade in payload.get("trades", [])
        )

    def latest_prices(self, pairs: tuple[str, ...]) -> tuple[OandaPriceSnapshot, ...]:
        query = urlencode({"instruments": ",".join(pairs)})
        payload = self._request_json(f"/v3/accounts/{self._config.account_id}/pricing?{query}")
        prices: list[OandaPriceSnapshot] = []
        for price in payload.get("prices", []):
            bid = float(price["bids"][0]["price"])
            ask = float(price["asks"][0]["price"])
            prices.append(
                OandaPriceSnapshot(
                    pair=str(price["instrument"]),
                    bid=bid,
                    ask=ask,
                    spread_pips=_spread_pips(str(price["instrument"]), bid, ask),
                )
            )
        return tuple(prices)

    def candles(self, pair: str, granularity: str = "M15", count: int = 100) -> tuple[dict[str, Any], ...]:
        query = urlencode({"granularity": granularity, "count": count, "price": "MBA"})
        payload = self._request_json(f"/v3/instruments/{pair}/candles?{query}")
        return tuple(payload.get("candles", ()))

    def place_market_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json(
            f"/v3/accounts/{self._config.account_id}/orders",
            method="POST",
            payload=payload,
        )

    def replace_trade_orders(
        self,
        trade_id: str,
        pair: str,
        *,
        stop_price: float | None = None,
        target_price: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if stop_price is not None:
            payload["stopLoss"] = {"price": _format_price(pair, stop_price)}
        if target_price is not None:
            payload["takeProfit"] = {"price": _format_price(pair, target_price)}
        if not payload:
            raise ValueError("replace_trade_orders requires at least one broker price")
        return self._request_json(
            f"/v3/accounts/{self._config.account_id}/trades/{trade_id}/orders",
            method="PUT",
            payload=payload,
        )

    def replace_stop_loss(self, trade_id: str, pair: str, stop_price: float) -> dict[str, Any]:
        return self.replace_trade_orders(trade_id, pair, stop_price=stop_price)

    def close_trade(self, trade_id: str, units: int | None = None) -> dict[str, Any]:
        payload = None if units is None else {"units": str(abs(int(units)))}
        return self._request_json(
            f"/v3/accounts/{self._config.account_id}/trades/{trade_id}/close",
            method="PUT",
            payload=payload,
        )

    def _request_json(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._config.api_base}{path}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._config.api_token}",
                "Content-Type": "application/json",
                "Accept-Datetime-Format": "RFC3339",
            },
        )
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                with urlopen(request, timeout=self._config.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code in {429, 500, 502, 503, 504, 520, 522, 524} and attempt < attempts:
                    sleep(1.0)
                    continue
                raise RuntimeError(f"OANDA HTTP error {exc.code}: {body}") from exc
            except TimeoutError as exc:
                if attempt < attempts:
                    sleep(1.0)
                    continue
                raise RuntimeError("OANDA request timed out") from exc
            except URLError as exc:
                if attempt < attempts:
                    sleep(1.0)
                    continue
                raise RuntimeError(f"OANDA network error: {exc}") from exc
        raise RuntimeError("OANDA request failed after retry")


def _read_env_file(env_path: str | Path | None) -> dict[str, str]:
    if env_path is None:
        env_path = Path("/home/rfing/READ_ONLY_LEGACY/rfing_oanda_cba_restored_edge_04142026/oanda/.env")
    path = Path(env_path)
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value.strip().strip("\"'")
    return values


def _spread_pips(pair: str, bid: float, ask: float) -> float:
    pip_size = 0.01 if pair.endswith("JPY") else 0.0001
    return round((ask - bid) / pip_size, 4)


def extract_trade_ids_from_order_response(payload: dict[str, Any]) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ()
    trade_ids: list[str] = []
    candidates = [
        payload.get("orderFillTransaction"),
        payload.get("orderCreateTransaction"),
        payload.get("relatedTransaction"),
    ]
    for node in candidates:
        if not isinstance(node, dict):
            continue
        trade_ids.extend(_trade_ids_from_node(node))
    return tuple(dict.fromkeys(trade_ids))


def _trade_ids_from_node(node: dict[str, Any]) -> list[str]:
    trade_ids: list[str] = []
    trade_opened = node.get("tradeOpened") if isinstance(node.get("tradeOpened"), dict) else {}
    trade_reduced = node.get("tradeReduced") if isinstance(node.get("tradeReduced"), dict) else {}
    trades_closed = node.get("tradesClosed") if isinstance(node.get("tradesClosed"), list) else []

    for value in (
        trade_opened.get("tradeID"),
        trade_opened.get("id"),
        trade_reduced.get("tradeID"),
        trade_reduced.get("id"),
        node.get("tradeID"),
        node.get("tradeId"),
    ):
        if value is not None and str(value).strip():
            trade_ids.append(str(value).strip())

    for closed in trades_closed:
        if not isinstance(closed, dict):
            continue
        value = closed.get("tradeID") or closed.get("id")
        if value is not None and str(value).strip():
            trade_ids.append(str(value).strip())

    return trade_ids


def _parse_open_trade_snapshot(trade: dict[str, Any]) -> OandaTradeSnapshot:
    units = int(float(trade["currentUnits"]))
    direction = "BUY" if units > 0 else "SELL"
    stop_order = trade.get("stopLossOrder") if isinstance(trade.get("stopLossOrder"), dict) else {}
    target_order = trade.get("takeProfitOrder") if isinstance(trade.get("takeProfitOrder"), dict) else {}
    stop_price = _float_or_none(stop_order.get("price"))
    target_price = _float_or_none(target_order.get("price"))
    return OandaTradeSnapshot(
        trade_id=str(trade["id"]),
        pair=str(trade["instrument"]),
        direction=direction,
        units=abs(units),
        entry_price=float(trade["price"]),
        unrealized_pl=float(trade.get("unrealizedPL", 0.0)),
        stop_price=stop_price,
        target_price=target_price,
    )


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _format_price(pair: str, price: float) -> str:
    decimals = 3 if pair.endswith("JPY") else 5
    return f"{price:.{decimals}f}"
