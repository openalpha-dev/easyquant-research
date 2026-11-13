---
name: easyquant-expression
description: 把选股和择时想法写成 EasyQuant 因子表达式：各市场字段、单位、函数与常见陷阱。Use when translating a user's selection or timing idea into an EasyQuant expression for screening, ranking or factor research.
---

# EasyQuant 因子表达式

表达式对每只股票（或 ETF、期货品种）、每个交易日算出一个值。用作**选股条件**时，结果非 0 即入选；用作**排序因子**时，按数值从大到小排。条件之间用 `*` 表示「且」，用 `MAX(a, b)` 表示「或」。

字段名小写，函数名大写。**字段全集和最新函数以工具返回为准，不要凭记忆写**：离线用 `search_fields(query, market)` / `search_functions(query)`（或 CLI `easyquant-research fields` / `functions`），拿不准实时单位、额度与已解锁全局因子再调运行时 `catalog`。本文只列最常用的部分。

## 常用字段（A 股 `cn_stock`）

| 类别 | 字段 | 单位与说明 |
| --- | --- | --- |
| 价量 | `open` `high` `low` `close` `volume` | 已前复权；`volume` 单位为手 |
| 价量 | `amount` | 成交额，单位为元 |
| 价量 | `raw_close` 等 `raw_*` | 不复权原值，用于「股价低于 10 元」这类条件 |
| 估值 | `pe_ttm` `pb` `ps_ttm` | 倍；亏损公司的 `pe_ttm` 为空 |
| 股息 | `dv_ttm` | 近 12 个月股息率，单位 %（3 表示 3%） |
| 市值 | `total_mv` `circ_mv` | 单位**万元**（100 亿元 = `1e6`） |
| 换手 | `turnover_rate` | 单位 % |
| 盈利 | `roe_yearly` `roa_yearly` | 年化 ROE / ROA，单位 % |
| 增长 | `netprofit_yoy` `or_yoy` | 净利润、营收同比，单位 % |
| 质量 | `grossprofit_margin` `debt_to_assets` | 毛利率、资产负债率，单位 % |
| 报表 | `incttm_*` `bs_*` `cfttm_*` | 利润表 TTM、资产负债表期末值、现金流量表 TTM，单位元 |
| 过滤 | `nonfin` | 非金融公司为 1，银行、保险、证券为空；乘上它可剔除金融股 |
| 基准 | `bench_close` | 沪深 300 收盘价，所有股票同一条序列 |
| 全局因子 | `gf_<代码>` `gfpct_<代码>` | Barra 风格与本土因子：`gf_` 原值，`gfpct_` 当天全市场百分位（0~1）。例如 `gfpct_value > 0.8` 为价值因子前 20%。**可用列表是实时的**，见 `catalog` 的 `expression.global_factors` |

★ 本土因子（龙虎榜、涨停、资金流、形态命中等）只存当天前 200 名或命中的股票，没进榜就是空值。它们适合当条件（如 `gf_lhb_net_buy_5d > 0`），不适合在全市场排序。

## 常用函数

`MA(x, n)` `EMA(x, n)` `STD(x, n)` `SUM(x, n)` `REF(x, n)` `DELTA(x, n)` `HHV(x, n)` `LLV(x, n)` `RSI(close, n)` `ATR(high, low, close, n)` `CROSS(a, b)` `IF(cond, a, b)` `ABS` `LOG` `MAX(a, b)` `MIN(a, b)`

- 不支持横截面 `RANK(x)`：要「全市场排前 N」，把排序表达式写进 `rank_by` 并给 `top_n`，由回测引擎按全市场排。
- `TS_RANK(x, n)`：当天的值在自己近 n 天里的百分位。
- `ZSCORE(x, n)`：自己近 n 天的时序标准分，不是横截面标准化。

完整函数表用 `search_functions()` 查，语义见 `get_doc("expression")`。

## 示例

| 想法 | 表达式 |
| --- | --- |
| ROE 大于 15% 且站上 60 日线 | `(roe_yearly > 15) * (close > MA(close, 60))` |
| 市盈率 15 倍以下、股息率 3% 以上 | `(pe_ttm > 0) * (pe_ttm < 15) * (dv_ttm > 3)` |
| 市值 50 亿到 300 亿之间 | `(circ_mv > 5e5) * (circ_mv < 3e6)` |
| 近 20 日涨幅 | `close / REF(close, 20) - 1` |
| 20 日线上穿 60 日线 | `CROSS(MA(close, 20), MA(close, 60))` |
| 剔除金融股的经营现金流质量 | `cfttm_n_cashflow_act / incttm_n_income_attr_p * nonfin` |

## 其他市场（`market` 参数）

只有 A 股有估值、财务和全局因子。其他市场能用的字段（用 `search_fields(market=...)` 核）：

| 市场 | `market` | 可用字段 | 说明 |
| --- | --- | --- | --- |
| 场内 ETF | `cn_etf` | 价量、`amount`、`fund_share`（份额，万份）、`scale`（规模，元）、`bench_*` | 不含货币 ETF；规模 2 亿以上写 `scale > 2e8` |
| 美股 | `us_equity` | 价量、`amount`（美元） | 自动只在当时日均成交额 ≥ 1000 万美元、股价 ≥ 5 美元的股票里选，不含 ETF |
| 港股 | `hk_stock` | 价量、`amount`（港元） | 自动只在当时日均成交额 ≥ 1000 万港元、股价 ≥ 1 港元的股票里选 |
| 期货品种 | `cn_future` | 价量、`amount`（元） | 品种主力连续，换月已前复权；自动只在日均成交额 ≥ 10 亿元的品种里排；`short_n` 做空排名末 N 个 |

价量指 `open` `high` `low` `close` `volume` `ret1` 与 `raw_*`。用了某市场没有的字段会当场报错。

| 想法 | 写法 |
| --- | --- |
| ETF 日均成交额 1 亿以上、近 20 日涨幅前 10 | `market=cn_etf`，条件 `MA(amount, 20) > 1e8`，`rank_by` `close / REF(close, 20) - 1`，`top_n` 10 |
| ETF 份额近 20 日增长 | `fund_share / REF(fund_share, 20) - 1` |
| 美股 12-1 动量 | `market=us_equity`，`rank_by` `REF(close, 21) / REF(close, 252) - 1` |
| 期货 60 日动量前 5 多、末 5 空 | `market=cn_future`，`rank_by` `close / REF(close, 60) - 1`，`top_n` 5，`short_n` 5 |

## 常见陷阱

- **`roe` 是报告期累计值**：一季报只含一个季度，`roe > 15` 在一季报后几乎没有股票满足。按年比较用 `roe_yearly`。
- **市值单位是万元**：「市值大于 100 亿」要写 `total_mv > 1e6`，不是 `1e10`。
- **百分比字段直接写数值**：股息率 3% 写 `dv_ttm > 3`，不是 `0.03`。
- **亏损公司的市盈率为空**：低估值条件要加 `pe_ttm > 0`，否则亏损公司的处理方式取决于空值，结果难以解释。
- **绝对价格阈值**：用 `close` 写「股价低于 10 元」得到的是复权价，要用 `raw_close`。
- **成交稀少的标的价格失真**：ETF 不加成交额门槛时，成交极少的 ETF 开盘价常被小单打到涨停附近，回测失真；加 `MA(amount, 20) > 5e7`。
- **期货大合约**：股指、黄金、原油一手名义上百万，回测账户 100 万时分到的金额可能不够一手，持仓会比 `top_n` 少。
- **只写条件、不指定排序时**：所有符合条件的股票等权入选，持仓只数可能随时间大幅变化，结果里要看持仓只数区间。

## 配合使用

写好表达式后，用 `validate_arguments("screen", {...})` 或 `validate_arguments("backtest_portfolio", {...})` 离线校验请求形状，再调运行时工具。选股名单用 `screen`，组合历史表现用 `backtest_portfolio`，因子预测力用 `factor_report`（给 `expression`）。整体流程见 `easyquant-research` 技能。