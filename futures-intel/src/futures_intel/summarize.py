from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from futures_intel.models import DailySnapshot, MemberPosition, ranked_by


@dataclass
class Highlight:
    member_name: str
    value: int | None
    change: int | None
    rank: int | None


@dataclass
class PositionSummary:
    trade_date: str
    commodity_symbol: str
    commodity_name: str
    exchange: str
    exchange_name: str
    contract: str
    is_main_contract: bool
    settle_price: float | None
    totals: dict[str, int | None]
    concentration: dict[str, float | None]
    top_long: list[Highlight]
    top_short: list[Highlight]
    top_net_long: list[Highlight]
    top_net_short: list[Highlight]
    notable: list[str] = field(default_factory=list)
    source: str = ""
    source_page: str = ""
    disclaimer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_date": self.trade_date,
            "commodity_symbol": self.commodity_symbol,
            "commodity_name": self.commodity_name,
            "exchange": self.exchange,
            "exchange_name": self.exchange_name,
            "contract": self.contract,
            "is_main_contract": self.is_main_contract,
            "settle_price": self.settle_price,
            "totals": self.totals,
            "concentration": self.concentration,
            "top_long": [item.__dict__ for item in self.top_long],
            "top_short": [item.__dict__ for item in self.top_short],
            "top_net_long": [item.__dict__ for item in self.top_net_long],
            "top_net_short": [item.__dict__ for item in self.top_net_short],
            "notable": self.notable,
            "source": self.source,
            "source_page": self.source_page,
            "disclaimer": self.disclaimer,
        }


def summarize(snapshot: DailySnapshot, *, top_n: int = 5) -> PositionSummary:
    longs = ranked_by(snapshot.members, "long_rank", limit=20)
    shorts = ranked_by(snapshot.members, "short_rank", limit=20)
    # net ranking uses the numeric net value when the official rank is missing
    net_long_sorted = sorted(
        [row for row in snapshot.members if (row.net_long or 0) > 0 or (row.net_position or 0) > 0],
        key=lambda row: row.net_long if row.net_long is not None else (row.net_position or 0),
        reverse=True,
    )
    net_short_sorted = sorted(
        [row for row in snapshot.members if (row.net_short or 0) > 0 or (row.net_position or 0) < 0],
        key=lambda row: row.net_short if row.net_short is not None else abs(row.net_position or 0),
        reverse=True,
    )

    totals = snapshot.totals
    concentration = {
        "top5_long_share": _share(longs[:5], "long_position", totals.today_long),
        "top20_long_share": _share(longs[:20], "long_position", totals.today_long),
        "top5_short_share": _share(shorts[:5], "short_position", totals.today_short),
        "top20_short_share": _share(shorts[:20], "short_position", totals.today_short),
    }

    return PositionSummary(
        trade_date=snapshot.trade_date.isoformat(),
        commodity_symbol=snapshot.commodity_symbol,
        commodity_name=snapshot.commodity_name,
        exchange=snapshot.exchange,
        exchange_name=snapshot.exchange_name,
        contract=snapshot.contract,
        is_main_contract=snapshot.is_main_contract,
        settle_price=snapshot.settle_price,
        totals={
            "volume": totals.today_volume,
            "volume_change": totals.volume_change,
            "long": totals.today_long,
            "long_change": totals.long_change,
            "short": totals.today_short,
            "short_change": totals.short_change,
            "net_long": totals.today_net_long,
        },
        concentration=concentration,
        top_long=[_highlight(row, "long_position", "long_change", "long_rank") for row in longs[:top_n]],
        top_short=[_highlight(row, "short_position", "short_change", "short_rank") for row in shorts[:top_n]],
        top_net_long=[
            _highlight(row, "net_long", "net_long_change", None) for row in net_long_sorted[:top_n]
        ],
        top_net_short=[
            _highlight(row, "net_short", "net_short_change", None) for row in net_short_sorted[:top_n]
        ],
        notable=_notable(snapshot, longs, shorts),
        source=snapshot.source,
        source_page=snapshot.source_page,
        disclaimer=snapshot.disclaimer,
    )


def _highlight(
    row: MemberPosition,
    value_attr: str,
    change_attr: str,
    rank_attr: str | None,
) -> Highlight:
    value = getattr(row, value_attr)
    if value is None and value_attr == "net_long":
        value = row.net_position if (row.net_position or 0) > 0 else None
    if value is None and value_attr == "net_short":
        if row.net_short is not None:
            value = row.net_short
        elif (row.net_position or 0) < 0:
            value = abs(row.net_position or 0)
    return Highlight(
        member_name=row.member_name,
        value=value,
        change=getattr(row, change_attr),
        rank=getattr(row, rank_attr) if rank_attr else None,
    )


def _share(rows: list[MemberPosition], attr: str, total: int | None) -> float | None:
    if not total:
        return None
    partial = sum(getattr(row, attr) or 0 for row in rows)
    return round(partial / total, 4)


def _notable(
    snapshot: DailySnapshot,
    longs: list[MemberPosition],
    shorts: list[MemberPosition],
) -> list[str]:
    notes: list[str] = []
    if snapshot.totals.long_change is not None:
        direction = "增加" if snapshot.totals.long_change >= 0 else "减少"
        notes.append(
            f"全市场多头持仓较上日{direction} {abs(snapshot.totals.long_change):,} 手。"
        )
    if snapshot.totals.short_change is not None:
        direction = "增加" if snapshot.totals.short_change >= 0 else "减少"
        notes.append(
            f"全市场空头持仓较上日{direction} {abs(snapshot.totals.short_change):,} 手。"
        )

    long_up = max(snapshot.members, key=lambda row: row.long_change or 0, default=None)
    long_down = min(snapshot.members, key=lambda row: row.long_change or 0, default=None)
    if long_up and (long_up.long_change or 0) > 0:
        notes.append(f"多头增仓最多：{long_up.member_name} +{long_up.long_change:,} 手。")
    if long_down and (long_down.long_change or 0) < 0:
        notes.append(f"多头减仓最多：{long_down.member_name} {long_down.long_change:,} 手。")

    short_up = max(snapshot.members, key=lambda row: row.short_change or 0, default=None)
    if short_up and (short_up.short_change or 0) > 0:
        notes.append(f"空头增仓最多：{short_up.member_name} +{short_up.short_change:,} 手。")

    two_sided = [
        row
        for row in snapshot.members
        if row.long_rank is not None
        and row.short_rank is not None
        and row.long_rank <= 5
        and row.short_rank <= 5
    ]
    if two_sided:
        names = "、".join(row.member_name for row in two_sided)
        notes.append(f"多空都进入前五的席位：{names}。这类席位通常是经纪业务较大的会员，不宜直接当成单边方向。")

    if longs and shorts:
        notes.append(
            f"多头第一名是{longs[0].member_name}，空头第一名是{shorts[0].member_name}。"
        )
    return notes
