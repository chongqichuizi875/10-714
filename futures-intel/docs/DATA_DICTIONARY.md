# 数据字典

单位未注明时都是「手」。排名 `9999` 在东方财富接口里表示「未进入该榜」，本工具会把它存成空值。

## 合约

| 字段 | 含义 |
| --- | --- |
| `TRADE_CODE` / `variety_code` | 品种代码，焦煤是 `JM` |
| `SECURITY_CODE` / `contract` | 合约代码，例如 `JM2701` |
| `IS_MAINCODE` | `1` 表示东方财富认定的主力合约 |
| `SECUCODE` | 带交易所后缀，例如 `JM2701.DCE` |
| `TRADE_DATE` | 持仓排名对应的交易日 |

## 会员持仓

| 字段 | 东方财富原字段 | 含义 |
| --- | --- | --- |
| `member_name` | `ORG_NAME_ABBR_NEW` | 去掉「代客」后的会员简称 |
| `member_name_raw` | `MEMBER_NAME_ABBR` | 原始席位名，常带「（代客）」 |
| `volume` / `volume_change` / `volume_rank` | `VOLUME` / `VOLUME_CHANGE` / `VOLUMERANK` | 成交量及排名 |
| `long_position` / `long_change` / `long_rank` | `LONG_POSITION` / `LP_CHANGE` / `LPRANK` | 多头持仓 |
| `short_position` / `short_change` / `short_rank` | `SHORT_POSITION` / `SP_CHANGE` / `SPRANK` | 空头持仓 |
| `net_long` / `net_long_change` | `NET_LONG_POSITION` / `NLP_CHANGE` | 净多 |
| `net_short` / `net_short_change` | `NET_SHORT_POSITION` / `NSP_CHANGE` | 净空 |
| `settle_price` | `SETTLE_PRICE` | 当日结算价 |

`TYPE=0` 是会员明细。`TYPE=2` 是三行合计：本日合计、上日合计、总量增减。

## 摘要指标

| 指标 | 计算方法 |
| --- | --- |
| `top5_long_share` | 多头排名前 5 的持仓之和 / 本日多头合计 |
| `top20_long_share` | 多头排名前 20 的持仓之和 / 本日多头合计 |
| `top5_short_share` / `top20_short_share` | 空头侧同样计算 |

前 20 集中度会接近 100%，因为交易所日常只公布大约前 20 名会员。它更适合看「榜内结构」，不能当成全市场真实持有人分布。
