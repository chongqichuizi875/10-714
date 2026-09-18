from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Iterable


NOT_RANKED = 9999


def parse_trade_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("empty trade date")
    return date.fromisoformat(text[:10])


def clean_rank(value: Any) -> int | None:
    if value in (None, ""):
        return None
    rank = int(value)
    if rank >= NOT_RANKED:
        return None
    return rank


def clean_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def clean_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def clean_member_name(raw: str | None, fallback: str | None = None) -> str:
    name = (raw or fallback or "").strip()
    for suffix in ("（代客）", "(代客)", "（自营）", "(自营)"):
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


@dataclass(frozen=True)
class MemberPosition:
    trade_date: date
    exchange: str
    variety_code: str
    variety_name: str
    contract: str
    member_name: str
    member_name_raw: str
    volume: int | None
    volume_change: int | None
    volume_rank: int | None
    long_position: int | None
    long_change: int | None
    long_rank: int | None
    short_position: int | None
    short_change: int | None
    short_rank: int | None
    net_long: int | None
    net_long_change: int | None
    net_short: int | None
    net_short_change: int | None
    settle_price: float | None
    source: str
    source_page: str

    @property
    def net_position(self) -> int | None:
        if self.long_position is None or self.short_position is None:
            if self.net_long is not None:
                return self.net_long
            if self.net_short is not None:
                return -self.net_short
            return None
        return self.long_position - self.short_position


@dataclass(frozen=True)
class MarketTotals:
    today_volume: int | None = None
    today_long: int | None = None
    today_short: int | None = None
    today_net_long: int | None = None
    prev_volume: int | None = None
    prev_long: int | None = None
    prev_short: int | None = None
    volume_change: int | None = None
    long_change: int | None = None
    short_change: int | None = None


@dataclass(frozen=True)
class ContractInfo:
    trade_code: str
    contract: str
    name: str
    exchange_code: str
    is_main: bool


@dataclass
class DailySnapshot:
    trade_date: date
    commodity_symbol: str
    commodity_name: str
    exchange: str
    exchange_name: str
    contract: str
    is_main_contract: bool
    settle_price: float | None
    members: list[MemberPosition] = field(default_factory=list)
    totals: MarketTotals = field(default_factory=MarketTotals)
    source: str = "eastmoney-datacenter"
    source_page: str = ""
    fetched_at: str = ""
    disclaimer: str = ""

    def ranked(self, attr: str, *, reverse: bool = False) -> list[MemberPosition]:
        rows = [row for row in self.members if getattr(row, attr) is not None]
        return sorted(rows, key=lambda row: getattr(row, attr), reverse=reverse)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trade_date"] = self.trade_date.isoformat()
        payload["members"] = [
            {**asdict(row), "trade_date": row.trade_date.isoformat()}
            for row in self.members
        ]
        return payload


def ranked_by(
    rows: Iterable[MemberPosition],
    rank_attr: str,
    *,
    limit: int | None = None,
) -> list[MemberPosition]:
    ordered = [
        row
        for row in sorted(
            (item for item in rows if getattr(item, rank_attr) is not None),
            key=lambda item: getattr(item, rank_attr),
        )
    ]
    return ordered[:limit] if limit is not None else ordered
