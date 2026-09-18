# 合规边界

这个目录里的程序只做一件事：按很低的频率，读取东方财富「成交持仓龙虎榜」页面自己在用的公开 JSON，把焦煤这类品种的会员持仓排名存到你自己的电脑上，并生成一份本地摘要。

它不是爬整站的爬虫，也不是可以对外发布数据的产品。

## 为什么可以读这个接口

[东方财富商品期货龙虎榜](https://data.eastmoney.com/futures/sh/data.html) 打开后，浏览器会向 `https://datacenter-web.eastmoney.com/api/data/v1/get` 要 JSON。本工具只复用这三个公开报表：

| 报表 | 用途 |
| --- | --- |
| `RPT_FUTU_POSITIONCODE` | 品种和合约列表，用来找到焦煤主力合约 |
| `RPT_FUTU_DAILYPOSITION`（`TYPE=0`） | 会员成交 / 多头 / 空头排名 |
| `RPT_FUTU_DAILYPOSITION`（`TYPE=2`） | 本日合计、上日合计、总量增减 |

[qhweb.eastmoney.com/robots.txt](https://qhweb.eastmoney.com/robots.txt) 对全部机器人写的是 `Allow: /`。`data.eastmoney.com` 没有提供 `robots.txt`。本工具不抓 HTML，不进需要登录的页面。

## 明确不做的事

- 不登录，不绕过验证码，不伪造浏览器指纹，不轮换代理。
- 不抓「持仓结构 / 建仓过程 / 持仓均价 / 盈亏分析」。这些页面会要求登录，属于 Choice 增值内容。
- 不解析或改写东方财富网页源代码，只按页面已经暴露的查询参数取 JSON。
- 收到 `401 / 403 / 429 / 451` 立刻停，不再重试。
- 不把原始接口结果提交到 Git。`data/raw`、`data/processed`、`data/reports` 默认忽略。

## 频率和身份

默认配置见 `configs/compliance.toml`：

- 两次请求至少间隔 1.5 秒
- 单次运行最多 12 个真实网络请求
- 同一 URL 20 小时内走本地缓存
- User-Agent 写明 `personal-research; rate-limited; no-redistribution`，不假装成人用的浏览器

焦煤日频持仓一般 4 次请求就够：合约列表、最近交易日、会员明细、合计。

## 法律声明里和本工具相关的句子

[东方财富法律声明](https://about.eastmoney.com/home/legal) 写得很清楚，这里按原文意思转述，不代替你自己阅读全文：

1. 网站内容和数据只供参考，不构成投资依据。
2. 不得干扰网站正常运行，也不得制造不合理或不成比例的高负载。
3. 网站材料受著作权法保护。未经事先书面许可，不得复制、修改、转载、传播、经销或散发。
4. 未经交易所事先书面同意，不得复制或传播网站上的行情信息。

因此本仓库的默认立场是：

- 用途限于个人本地研究
- 原始数据和生成的摘要都留在本机
- 若要商用、对外展示、写进研报公开发布，请改走交易所授权渠道或东方财富 Choice / 掘金等正式许可接口
- 会员持仓排名的权威来源是交易所披露。焦煤对应[大连商品交易所每日持仓排名](http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/rtj/rcjccpm/index.html)。交易所官网若开启防护，本工具不会尝试绕过

## 数据含义上的合规提醒

交易所公布的是期货公司**经纪业务（代客）**成交和持仓，不是公司自己的方向性筹码。摘要里如果某个席位多空都很大，程序会单独标出来，避免把经纪通道误读成单边主力。
