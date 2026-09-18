from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMMODITIES = PACKAGE_ROOT / "configs" / "commodities.toml"
DEFAULT_COMPLIANCE = PACKAGE_ROOT / "configs" / "compliance.toml"
DEFAULT_DATA_DIR = PACKAGE_ROOT / "data"


@dataclass(frozen=True)
class Commodity:
    symbol: str
    name: str
    exchange: str
    exchange_name: str
    eastmoney_trade_code: str
    unit: str = "手"
    notes: str = ""


@dataclass(frozen=True)
class ComplianceConfig:
    purpose: str
    allow_network: bool
    user_agent: str
    min_interval_seconds: float
    max_requests_per_run: int
    timeout_seconds: float
    cache_ttl_hours: float
    stop_on_status: tuple[int, ...]
    referer: str
    legal_url: str
    page_url: str


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_commodities(path: Path | None = None) -> dict[str, Commodity]:
    raw = _load_toml(path or DEFAULT_COMMODITIES)
    out: dict[str, Commodity] = {}
    for symbol, item in raw.items():
        if not isinstance(item, dict):
            continue
        key = str(symbol).upper()
        out[key] = Commodity(
            symbol=key,
            name=str(item["name"]),
            exchange=str(item["exchange"]),
            exchange_name=str(item["exchange_name"]),
            eastmoney_trade_code=str(item.get("eastmoney_trade_code", key)),
            unit=str(item.get("unit", "手")),
            notes=str(item.get("notes", "")),
        )
    return out


def load_compliance(path: Path | None = None) -> ComplianceConfig:
    raw = _load_toml(path or DEFAULT_COMPLIANCE)
    return ComplianceConfig(
        purpose=str(raw.get("purpose", "personal_research")),
        allow_network=bool(raw.get("allow_network", True)),
        user_agent=str(raw["user_agent"]),
        min_interval_seconds=float(raw.get("min_interval_seconds", 1.5)),
        max_requests_per_run=int(raw.get("max_requests_per_run", 12)),
        timeout_seconds=float(raw.get("timeout_seconds", 20)),
        cache_ttl_hours=float(raw.get("cache_ttl_hours", 20)),
        stop_on_status=tuple(int(code) for code in raw.get("stop_on_status", (403, 429))),
        referer=str(raw["referer"]),
        legal_url=str(raw["legal_url"]),
        page_url=str(raw["page_url"]),
    )


def resolve_commodity(symbol: str, path: Path | None = None) -> Commodity:
    commodities = load_commodities(path)
    key = symbol.strip().upper()
    if key not in commodities:
        known = ", ".join(sorted(commodities)) or "(none)"
        raise KeyError(f"Unknown commodity {symbol!r}. Configured symbols: {known}")
    return commodities[key]
