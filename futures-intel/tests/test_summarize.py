from __future__ import annotations

from futures_intel.config import resolve_commodity
from futures_intel.http import HttpResponse
from futures_intel.report import render_markdown
from futures_intel.sources.eastmoney import EastmoneyPositionClient
from futures_intel.summarize import summarize


class _ScriptedHttp:
    def __init__(self, payloads: dict) -> None:
        self.payloads = payloads

    def get_json(self, url: str, params: dict) -> HttpResponse:  # noqa: ARG002
        report = params["reportName"]
        if report == "RPT_FUTU_POSITIONCODE":
            payload = self.payloads["contracts"]
        elif "LPRANK=1" in params.get("filter", ""):
            payload = self.payloads["latest"]
        elif 'TYPE="2"' in params.get("filter", ""):
            payload = self.payloads["totals"]
        else:
            payload = self.payloads["members"]
        return HttpResponse(url=url, payload=payload, cached=True, status=200, fetched_at="")


def test_summary_and_markdown(synthetic_payloads) -> None:
    from futures_intel.config import load_compliance

    snapshot = EastmoneyPositionClient(_ScriptedHttp(synthetic_payloads), load_compliance()).fetch_snapshot(
        resolve_commodity("JM")
    )
    summary = summarize(snapshot, top_n=3)
    assert summary.top_long[0].member_name == "示例甲"
    assert summary.top_long[0].value == 40000
    assert summary.top_short[0].member_name == "示例乙"
    assert summary.concentration["top5_long_share"] == round((40000 + 35000 + 22000 + 18000 + 15000) / 300000, 4)
    assert any("多空都进入前五" in item for item in summary.notable)
    markdown = render_markdown(summary)
    assert "焦煤（JM）持仓摘要" in markdown
    assert "示例甲" in markdown
    assert "不构成投资建议" in markdown
