# 因子表达式

表达式对每只标的、每个交易日算出一个值。用作**选股条件**时结果非 0 即入选；用作**排序因子**时按数值排序。条件之间「且」用 `*`，「或」用 `MAX(a, b)`，条件分支用 `IF(条件, 值1, 值2)`。字段名小写、函数名大写。

字段全集、单位与最新函数以运行时 `catalog` 返回为准；离线可用 `search_fields` / `search_functions` 查询本包 `catalog/fields.json`、`catalog/functions.json`（由引擎导出）。**不要臆造字段名或函数名。**

## 常用字段（A 股）

| 类别 | 字段 | 单位与说明 |
| --- | --- | --- |
| 价量 | `open` `high` `low` `close` `volume` | 已前复权；`volume` 单位手 |
| 价量 | `amount` | 成交额，元 |
| 价量 | `raw_close` 等 `raw_*` | 不复权原值，「股价低于 10 元」用 `raw_close` |
| 估值 | `pe` `pe_ttm` `pb` `ps` `ps_ttm` | 倍；亏损公司 `pe_ttm` 为空，低估值条件加 `pe_ttm > 0` |
| 股息 | `dv_ratio` `dv_ttm` | 股息率 %，3 表示 3% |
| 市值股本 | `total_mv` `circ_mv` | **万元**，100 亿元写 `1e6` |
| 市值股本 | `total_share` `float_share` `free_share` | 万股 |
| 交易 | `turnover_rate` `turnover_rate_f` `volume_ratio` | 换手率 %，量比倍数 |
| 财务指标 | `roe_yearly` `roa_yearly` `roic_yearly` `grossprofit_margin` `netprofit_margin` `debt_to_assets` `current_ratio` `quick_ratio` `netprofit_yoy` `or_yoy` `tr_yoy` `q_roe` `q_netprofit_yoy` `q_sales_yoy` `eps` `bps` `cfps` | 比率类为 %；按年比较用 `roe_yearly` |
| 利润表 | `inc_<科目>` / `incq_<科目>` / `incttm_<科目>` | 年初累计 / 单季 / 近四季合计，元；科目沿用 Tushare income 字段名 |
| 资产负债表 | `bs_<科目>` | 期末值，元 |
| 现金流量表 | `cf_<科目>` / `cfq_<科目>` / `cfttm_<科目>` | 同利润表口径 |
| 过滤 | `nonfin` | 非金融为 1，银行/保险/证券为空；乘上它剔除金融股 |
| 指数 | `bench_close` `sh_close`（及 `_open/_high/_low/_vol/_amount`） | 沪深 300 / 上证指数，所有股票同一条序列 |
| 派生 | `ret1` | 当日涨跌幅（比例） |
| 全局因子 | `gf_<代码小写>` `gfpct_<代码小写>` | Barra 风格与本土因子：`gf_` 原值，`gfpct_` 当天全市场百分位 0~1 |

★ 本土因子（龙虎榜、涨停、资金流、形态命中等）只存当天前 200 或命中的股票，没进榜是空值，适合当条件（如 `gf_lhb_net_buy_5d > 0`），不适合在全市场排序。可用因子清单与套餐锁定见运行时 `catalog` 的 `expression.global_factors`。

## 常用函数

`MA(x,n)` / `SMA` / `EMA(x,n)`、`STD(x,n)` / `SUM(x,n)` / `MEAN(x,n)`、`REF(x,n)` / `DELAY(x,n)`、`DELTA(x,n)`、`HHV(x,n)` / `LLV(x,n)`、`TS_RANK(x,n)`、`ZSCORE(x,n)`、`RSI(x,n)` / `ATR(high,low,close,n)` / `ADX(...)` / `CCI(...)` / `OBV(close,volume)`、`CORR(x,y,n)` / `COV(x,y,n)`、`DECAY_LINEAR(x,n)` / `MAX_DRAWDOWN(x,n)`、`CROSS(a,b)`、`EVERY(cond,n)`、`IF(cond,a,b)`、`ABS` / `LOG` / `SQRT` / `MAX(a,b)` / `MIN(a,b)`。

- 不支持横截面 `RANK(x)`：要「全市场排前 N」，把排序表达式写进 `rank_by` 并给 `top_n`，由引擎按全市场排。
- `TS_RANK(x,n)` 是当天值在自己近 n 天里的百分位；`ZSCORE(x,n)` 是自己近 n 天的时序标准分，都不是横截面标准化。
- 不支持字符串、下标、属性访问。空值用 `np.nan`。

## 示例

| 想法 | 写法 |
| --- | --- |
| ROE 大于 15% 且站上 60 日线 | `(roe_yearly > 15) * (close > MA(close, 60))` |
| 市盈率 15 倍以下、股息率 3% 以上 | `(pe_ttm > 0) * (pe_ttm < 15) * (dv_ttm > 3)` |
| 流通市值 50 亿到 300 亿 | `(circ_mv > 5e5) * (circ_mv < 3e6)` |
| 近 20 日涨幅最大的 30 只 | `rank_by` `close / REF(close, 20) - 1`，`top_n` 30 |
| 20 日线上穿 60 日线 | `CROSS(MA(close, 20), MA(close, 60))` |

## 其他市场（`market` 参数）

只有 A 股有估值、财务和全局因子。其他市场只能用价量字段（`open high low close volume amount ret1 raw_*`）：

| 市场 | `market` | 额外字段 | 点时流动性门槛 |
| --- | --- | --- | --- |
| 场内 ETF | `cn_etf` | `fund_share`（万份）、`scale`（元）、`bench_*` | 不含货币 ETF；规模用 `scale` |
| 美股 | `us_equity` | `amount`（美元） | 20 日均成交额 ≥ 1000 万美元、股价 ≥ 5 美元，不含 ETF |
| 港股 | `hk_stock` | `amount`（港元） | 20 日均成交额 ≥ 1000 万港元、股价 ≥ 1 港元 |
| 期货品种 | `cn_future` | `amount`（元） | 20 日均成交额 ≥ 10 亿元；`short_n` 做空末 N 个 |

用了某市场没有的字段会当场报错。

## 常见陷阱

- `roe` 是报告期累计值，一季报只含一个季度；按年比较用 `roe_yearly`。
- 市值单位是万元：「市值大于 100 亿」写 `total_mv > 1e6`，不是 `1e10`。
- 百分比字段直接写数值：股息率 3% 写 `dv_ttm > 3`，不是 `0.03`。
- 亏损公司市盈率为空：低估值条件加 `pe_ttm > 0`。
- 绝对价格阈值用 `raw_close`，`close` 是复权价。
- ETF 不加成交额门槛时，成交极少的 ETF 开盘价常被小单打到涨停附近，回测失真；加 `MA(amount, 20) > 5e7`。
- 期货大合约一手名义上百万，账户资金不够一手时持仓会比 `top_n` 少。
- 只写条件不指定排序时，符合条件的全部等权入选，持仓只数可能随时间大幅变化，要看结果里的持仓只数区间。