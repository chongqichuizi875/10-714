# futures-intel

个人研究用的期货持仓收集器。第一期只做一件事：在合规边界内，读取东方财富公开的会员持仓排名，先用**焦煤（JM）**跑通收集 → 本地存档 → 摘要。

当前 Cloud Agent 挂在 [chongqichuizi875/10-714](https://github.com/chongqichuizi875/10-714) 上，不能另外新建 GitHub 仓库，所以这套代码以可独立拆走的目录形式放在 `futures-intel/`。之后要单独建仓，把这个目录拷出去即可。

## 它收集什么

- 焦煤主力合约和可交易合约
- 指定交易日的会员成交量、多头、空头、净持仓排名
- 本日 / 上日合计
- 一份本地 Markdown / JSON 摘要：前五名、集中度、当天比较显眼的增减

权威数据源仍是[大连商品交易所每日持仓排名](http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/rtj/rcjccpm/index.html)。东方财富只是网页转载入口。页面地址：[成交持仓龙虎榜](https://data.eastmoney.com/futures/sh/data.html)。

## 合规怎么做

短版规则：

1. 只打页面自己在用的公开 JSON，不抓 HTML，不登录，不碰 Choice 付费栏目。
2. 标明研究用途的 User-Agent，默认 1.5 秒一条、单次最多 12 次真实请求，并做 20 小时缓存。
3. 遇到 403 / 429 立刻停，不伪装、不换代理。
4. 原始结果默认不进 Git。
5. 输出里写明：席位是经纪业务代客数据，不是投资建议。

完整说明见 [docs/COMPLIANCE.md](docs/COMPLIANCE.md)。字段含义见 [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)。

## 使用

需要 Python 3.11+。运行时代码只用标准库。

```bash
cd futures-intel
python3 -m pip install -e ".[dev]"
python3 -m futures_intel demo
```

常用参数：

```bash
# 指定交易日和合约
python3 -m futures_intel demo --date 2026-09-17 --contract JM2701

# 只走本地缓存，不再联网
python3 -m futures_intel demo --offline --date 2026-09-17 --contract JM2701

# 以后加品种时，先改 configs/commodities.toml
python3 -m futures_intel fetch --symbol JM
```

本地结果写在 `data/`：

| 目录 | 内容 |
| --- | --- |
| `data/processed/` | 规范化后的 JSON / CSV |
| `data/reports/` | 摘要 Markdown / JSON |
| `data/.http-cache/` | 接口缓存，避免重复打官网 |

## 测试

```bash
cd futures-intel
python3 -m pytest
```

测试用的是虚构会员和整数，不包含真实东方财富回包。

## 以后可以往这个目录里继续堆的信息

`configs/commodities.toml` 按品种追加即可。比较自然的下一档是焦炭 `J`、铁矿 `I`，以及把大商所官方下载做成对照源。官方源如果有防护，对照应改为人工下载，而不是绕过防护。
