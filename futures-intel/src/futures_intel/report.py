from __future__ import annotations

from futures_intel.summarize import Highlight, PositionSummary


def render_markdown(summary: PositionSummary) -> str:
    main = "是" if summary.is_main_contract else "否"
    settle = _num(summary.settle_price, digits=1)
    totals = summary.totals
    conc = summary.concentration
    lines = [
        f"# {summary.commodity_name}（{summary.commodity_symbol}）持仓摘要",
        "",
        f"- 交易日：{summary.trade_date}",
        f"- 交易所：{summary.exchange_name}（{summary.exchange}）",
        f"- 合约：{summary.contract}（主力：{main}）",
        f"- 结算价：{settle}",
        f"- 数据入口：{summary.source_page}",
        f"- 适配来源：`{summary.source}`",
        "",
        "## 全市场合计",
        "",
        "| 项目 | 数量（手） | 较上日 |",
        "| --- | ---: | ---: |",
        f"| 成交量 | {_num(totals.get('volume'))} | {_signed(totals.get('volume_change'))} |",
        f"| 多头持仓 | {_num(totals.get('long'))} | {_signed(totals.get('long_change'))} |",
        f"| 空头持仓 | {_num(totals.get('short'))} | {_signed(totals.get('short_change'))} |",
        f"| 净多 | {_num(totals.get('net_long'))} | — |",
        "",
        "## 持仓集中度",
        "",
        "集中度 = 排名靠前会员持仓之和 / 全市场合计。数字越大，说明前排席位占的份额越高。",
        "",
        "| 口径 | 占比 |",
        "| --- | ---: |",
        f"| 多头前 5 | {_pct(conc.get('top5_long_share'))} |",
        f"| 多头前 20 | {_pct(conc.get('top20_long_share'))} |",
        f"| 空头前 5 | {_pct(conc.get('top5_short_share'))} |",
        f"| 空头前 20 | {_pct(conc.get('top20_short_share'))} |",
        "",
        "## 多头前五",
        "",
        _table(summary.top_long, "多单"),
        "",
        "## 空头前五",
        "",
        _table(summary.top_short, "空单"),
        "",
        "## 净多 / 净空前五",
        "",
        "净多 = 多单 − 空单。期货公司席位披露的是经纪业务合计，不是公司自营方向。",
        "",
        "### 净多",
        "",
        _table(summary.top_net_long, "净多"),
        "",
        "### 净空",
        "",
        _table(summary.top_net_short, "净空"),
        "",
        "## 观察",
        "",
    ]
    if summary.notable:
        lines.extend(f"- {item}" for item in summary.notable)
    else:
        lines.append("- 暂无额外观察。")
    lines.extend(
        [
            "",
            "## 使用限制",
            "",
            summary.disclaimer,
            "",
        ]
    )
    return "\n".join(lines)


def _table(rows: list[Highlight], value_label: str) -> str:
    if not rows:
        return "（无数据）"
    lines = [
        f"| 名次 | 会员 | {value_label}（手） | 增减 |",
        "| ---: | --- | ---: | ---: |",
    ]
    for index, row in enumerate(rows, start=1):
        rank = row.rank if row.rank is not None else index
        lines.append(
            f"| {rank} | {row.member_name} | {_num(row.value)} | {_signed(row.change)} |"
        )
    return "\n".join(lines)


def _num(value: float | int | None, *, digits: int | None = None) -> str:
    if value is None:
        return "—"
    if digits is not None:
        return f"{value:,.{digits}f}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}"


def _signed(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:+,}"


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"
