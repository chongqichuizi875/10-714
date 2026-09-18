from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from futures_intel.config import Commodity, ComplianceConfig
from futures_intel.http import HttpResponse, PoliteClient
from futures_intel.models import (
    ContractInfo,
    DailySnapshot,
    MarketTotals,
    MemberPosition,
    clean_float,
    clean_int,
    clean_member_name,
    clean_rank,
    parse_trade_date,
)


DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

# Codes observed on the public 成交持仓龙虎榜 page.
MARKET_MAP = {
    "069001005": ("SHFE", "上海期货交易所"),
    "069001007": ("DCE", "大连商品交易所"),
    "069001008": ("CZCE", "郑州商品交易所"),
    "069001009": ("CFFEX", "中国金融期货交易所"),
    "069001016": ("INE", "上海国际能源交易中心"),
    "069001021": ("GFEX", "广州期货交易所"),
}

DISCLAIMER = (
    "本工具只读取东方财富期货龙虎榜页面自己调用的公开 JSON，供个人本地研究。"
    "会员持仓排名以交易所披露为准；东方财富 Choice 数据仅供参考，不构成投资建议。"
    "未经权利人书面许可，不得复制、传播或商用转售这些数据。"
)


class EastmoneyError(RuntimeError):
    pass


class EastmoneyPositionClient:
    def __init__(self, http: PoliteClient, compliance: ComplianceConfig) -> None:
        self.http = http
        self.compliance = compliance

    def list_contracts(self, commodity: Commodity) -> list[ContractInfo]:
        payload = self._get(
            {
                "reportName": "RPT_FUTU_POSITIONCODE",
                "columns": "TRADE_MARKET_CODE,TRADE_CODE,TRADE_TYPE,SECURITY_CODE,IS_MAINCODE",
                "filter": f'(TRADE_CODE="{commodity.eastmoney_trade_code}")',
                "pageNumber": "1",
                "pageSize": "20",
                "source": "WEB",
                "client": "WEB",
            }
        )
        rows = []
        for item in _rows(payload):
            rows.append(
                ContractInfo(
                    trade_code=str(item.get("TRADE_CODE") or commodity.eastmoney_trade_code),
                    contract=str(item["SECURITY_CODE"]),
                    name=str(item.get("TRADE_TYPE") or commodity.name),
                    exchange_code=str(item.get("TRADE_MARKET_CODE") or ""),
                    is_main=str(item.get("IS_MAINCODE")) == "1",
                )
            )
        if not rows:
            raise EastmoneyError(f"No Eastmoney contracts found for {commodity.symbol}")
        return rows

    def resolve_contract(self, commodity: Commodity, contract: str | None = None) -> ContractInfo:
        contracts = self.list_contracts(commodity)
        if contract:
            wanted = contract.strip().upper()
            for item in contracts:
                if item.contract.upper() == wanted:
                    return item
            known = ", ".join(item.contract for item in contracts)
            raise EastmoneyError(f"Contract {contract} not in Eastmoney list: {known}")
        for item in contracts:
            if item.is_main:
                return item
        return contracts[0]

    def latest_trade_date(self, contract: str) -> str:
        payload = self._get(
            {
                "reportName": "RPT_FUTU_DAILYPOSITION",
                "columns": "TRADE_DATE,SECURITY_CODE",
                "filter": f'(SECURITY_CODE="{contract}")(TYPE="0")(LPRANK=1)',
                "sortTypes": "-1",
                "sortColumns": "TRADE_DATE",
                "pageNumber": "1",
                "pageSize": "1",
                "source": "WEB",
                "client": "WEB",
            }
        )
        rows = _rows(payload)
        if not rows:
            raise EastmoneyError(f"No daily position dates for {contract}")
        return parse_trade_date(rows[0]["TRADE_DATE"]).isoformat()

    def fetch_snapshot(
        self,
        commodity: Commodity,
        *,
        trade_date: str | None = None,
        contract: str | None = None,
    ) -> DailySnapshot:
        info = self.resolve_contract(commodity, contract)
        day = trade_date or self.latest_trade_date(info.contract)
        members_payload = self._get(_position_params(info.contract, day, type_code="0"))
        totals_payload = self._get(_position_params(info.contract, day, type_code="2"))

        member_rows = [_member_from_row(item, commodity, self.compliance) for item in _rows(members_payload)]
        if not member_rows:
            raise EastmoneyError(f"Empty member ranking for {info.contract} on {day}")

        exchange, exchange_name = _exchange_of(member_rows[0], info, commodity)
        settle = next((row.settle_price for row in member_rows if row.settle_price is not None), None)
        return DailySnapshot(
            trade_date=parse_trade_date(day),
            commodity_symbol=commodity.symbol,
            commodity_name=commodity.name,
            exchange=exchange,
            exchange_name=exchange_name,
            contract=info.contract,
            is_main_contract=info.is_main,
            settle_price=settle,
            members=member_rows,
            totals=_totals_from_rows(_rows(totals_payload)),
            source="eastmoney-datacenter",
            source_page=self.compliance.page_url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            disclaimer=DISCLAIMER,
        )

    def _get(self, params: dict[str, str]) -> dict[str, Any]:
        response: HttpResponse = self.http.get_json(DATACENTER_URL, params)
        payload = response.payload
        if not isinstance(payload, dict):
            raise EastmoneyError("Eastmoney response is not a JSON object")
        if payload.get("success") is False:
            raise EastmoneyError(payload.get("message") or "Eastmoney returned success=false")
        return payload


def _position_params(contract: str, trade_date: str, *, type_code: str) -> dict[str, str]:
    return {
        "reportName": "RPT_FUTU_DAILYPOSITION",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{contract}")(TRADE_DATE=\'{trade_date}\')(TYPE="{type_code}")',
        "sortTypes": "1",
        "sortColumns": "LPRANK",
        "pageNumber": "1",
        "pageSize": "50",
        "source": "WEB",
        "client": "WEB",
    }


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result") or {}
    data = result.get("data") or []
    return [item for item in data if isinstance(item, dict)]


def _member_from_row(
    item: dict[str, Any],
    commodity: Commodity,
    compliance: ComplianceConfig,
) -> MemberPosition:
    secucode = str(item.get("SECUCODE") or "")
    exchange = ""
    if "." in secucode:
        exchange = secucode.split(".")[-1]
    market_code = str(item.get("TRADE_MARKET_CODE") or "")
    if not exchange and market_code in MARKET_MAP:
        exchange = MARKET_MAP[market_code][0]
    raw_name = str(item.get("MEMBER_NAME_ABBR") or "")
    return MemberPosition(
        trade_date=parse_trade_date(item.get("TRADE_DATE")),
        exchange=exchange or commodity.exchange,
        variety_code=str(item.get("TRADE_CODE") or commodity.symbol),
        variety_name=commodity.name,
        contract=str(item.get("SECURITY_CODE") or ""),
        member_name=clean_member_name(item.get("ORG_NAME_ABBR_NEW"), raw_name),
        member_name_raw=raw_name,
        volume=clean_int(item.get("VOLUME")),
        volume_change=clean_int(item.get("VOLUME_CHANGE")),
        volume_rank=clean_rank(item.get("VOLUMERANK") if item.get("VOLUMERANK") is not None else item.get("VOLUME_RANK")),
        long_position=clean_int(item.get("LONG_POSITION")),
        long_change=clean_int(item.get("LP_CHANGE")),
        long_rank=clean_rank(item.get("LPRANK") if item.get("LPRANK") is not None else item.get("LP_RANK")),
        short_position=clean_int(item.get("SHORT_POSITION")),
        short_change=clean_int(item.get("SP_CHANGE")),
        short_rank=clean_rank(item.get("SPRANK") if item.get("SPRANK") is not None else item.get("SP_RANK")),
        net_long=clean_int(item.get("NET_LONG_POSITION")),
        net_long_change=clean_int(item.get("NLP_CHANGE")),
        net_short=clean_int(item.get("NET_SHORT_POSITION")),
        net_short_change=clean_int(item.get("NSP_CHANGE")),
        settle_price=clean_float(item.get("SETTLE_PRICE")),
        source="eastmoney-datacenter",
        source_page=compliance.page_url,
    )


def _totals_from_rows(rows: list[dict[str, Any]]) -> MarketTotals:
    by_name = {str(item.get("MEMBER_NAME_ABBR") or ""): item for item in rows}
    today = by_name.get("本日合计", {})
    prev = by_name.get("上日合计", {})
    delta = by_name.get("总量增减", {})
    return MarketTotals(
        today_volume=clean_int(today.get("VOLUME")),
        today_long=clean_int(today.get("LONG_POSITION")),
        today_short=clean_int(today.get("SHORT_POSITION")),
        today_net_long=clean_int(today.get("NET_LONG_POSITION")),
        prev_volume=clean_int(prev.get("VOLUME")),
        prev_long=clean_int(prev.get("LONG_POSITION")),
        prev_short=clean_int(prev.get("SHORT_POSITION")),
        volume_change=clean_int(delta.get("VOLUME") if delta.get("VOLUME") is not None else today.get("VOLUME_CHANGE")),
        long_change=clean_int(delta.get("LONG_POSITION") if delta.get("LONG_POSITION") is not None else today.get("LP_CHANGE")),
        short_change=clean_int(delta.get("SHORT_POSITION") if delta.get("SHORT_POSITION") is not None else today.get("SP_CHANGE")),
    )


def _exchange_of(
    sample: MemberPosition,
    info: ContractInfo,
    commodity: Commodity,
) -> tuple[str, str]:
    if info.exchange_code in MARKET_MAP:
        return MARKET_MAP[info.exchange_code]
    if sample.exchange:
        return sample.exchange, commodity.exchange_name
    return commodity.exchange, commodity.exchange_name
