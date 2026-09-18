from __future__ import annotations

from futures_intel.config import resolve_commodity
from futures_intel.http import HttpResponse
from futures_intel.sources.eastmoney import EastmoneyPositionClient


class _ScriptedHttp:
    def __init__(self, payloads: dict) -> None:
        self.payloads = payloads
        self.calls: list[dict] = []

    def get_json(self, url: str, params: dict) -> HttpResponse:  # noqa: ARG002
        self.calls.append(params)
        report = params["reportName"]
        if report == "RPT_FUTU_POSITIONCODE":
            payload = self.payloads["contracts"]
        elif "LPRANK=1" in params.get("filter", ""):
            payload = self.payloads["latest"]
        elif 'TYPE="2"' in params.get("filter", ""):
            payload = self.payloads["totals"]
        else:
            payload = self.payloads["members"]
        return HttpResponse(url=url, payload=payload, cached=True, status=200, fetched_at="2026-09-18T00:00:00+00:00")


def test_fetch_snapshot_from_synthetic_payloads(synthetic_payloads) -> None:
    http = _ScriptedHttp(synthetic_payloads)
    client = EastmoneyPositionClient(http, __import__("futures_intel.config", fromlist=["load_compliance"]).load_compliance())
    snapshot = client.fetch_snapshot(resolve_commodity("JM"))

    assert snapshot.contract == "JM2701"
    assert snapshot.is_main_contract is True
    assert snapshot.exchange == "DCE"
    assert snapshot.trade_date.isoformat() == "2026-09-17"
    assert snapshot.settle_price == 1600.0
    assert snapshot.totals.today_long == 300000
    assert snapshot.totals.long_change == 1000
    names = [row.member_name for row in snapshot.members]
    assert names[0] == "示例甲"
    missing_volume = next(row for row in snapshot.members if row.member_name == "示例丁")
    assert missing_volume.volume_rank is None
    unranked_long = next(row for row in snapshot.members if row.member_name == "示例己")
    assert unranked_long.long_rank is None
    assert all("代客" not in row.member_name for row in snapshot.members)
    assert len(http.calls) == 4
