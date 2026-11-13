# 择时 DSL（单标的买卖规则）

`backtest_timing` 用 EasyQuant DSL 描述单个标的的入场、出场规则。日线回测：**收盘出信号、次日开盘成交**，满足入场即全仓买入，满足出场或止盈止损即全部卖出，同时给出同区间买入持有对比。

指标类型与参数以运行时 `catalog` 的 `timing_rules.indicators` 为准；离线用 `search_indicators` / `get_indicator` 查本包 `catalog/indicators.json`（由引擎 `dsl/indicator-metadata.json` 过滤日内/L2/停用/B_ONLY 后导出，共 132 个日线可用指标）。**不要臆造指标类型或参数键。**

## 结构

```json
{
  "code": "600519.SH",
  "indicators": {
    "fast": { "type": "SMA", "period": 20 },
    "slow": { "type": "SMA", "period": 60 }
  },
  "entry": { "type": "CROSS_UP", "left": { "ind": "fast" }, "right": { "ind": "slow" } },
  "exit":  { "type": "CROSS_DOWN", "left": { "ind": "fast" }, "right": { "ind": "slow" } }
}
```

- `indicators`：名字 → `{type, 参数...}`。规则里用 `{"ind": "名字"}` 引用。
- 常量写 `{"const": 30}`，**不能直接写裸数字**。
- 价格先用 `{"type": "PRICE", "field": "CLOSE"}` 定义成指标（`field` 可取 `OPEN/HIGH/LOW/CLOSE`），再 `{"ind": ...}` 引用。
- 四则运算写 `{"op": "SUB", "left": ..., "right": ...}`（`ADD/SUB/MUL/DIV`），`left/right` 仍是操作数。

## 规则节点

| 类别 | 节点 | 字段 |
| --- | --- | --- |
| 逻辑 | `AND` / `OR` | `left`、`right`（二元；三个条件要嵌套两层） |
| 逻辑 | `NOT` | `rule` |
| 比较 | `GT` / `LT` / `GTE` / `LTE` / `EQ` / `NEQ` | `left`、`right` |
| 穿越 | `CROSS_UP` / `CROSS_DOWN` | `left`、`right` |

## 期货多空

期货品种（`code` 写 `RB`、`IF`、`AU` 等，按主力连续）可加 `short_entry` / `short_exit` 做空，与 `entry` / `exit` 同时写即多空双向；同一时间只持有一个方向。`capital_budget_pct` 设资金预算 %（默认 100，最多 300 即 3 倍杠杆）。

## 止盈止损（可选 `exits`）

`stopLossPct`（止损 %）、`takeProfitPct`（止盈 %）、`trailingStopPct`（移动止损 %：从持仓最高点回撤多少平仓）、`trailingArmProfitPct`（浮盈达到多少 % 后启用移动止损）。

## 市场与代码

- A 股 / ETF：`code` 带交易所后缀（`600519.SH`、`510300.SH`），按代码自动识别，不传 `market`。
- 美股 / 港股：必须传 `market`（`us_equity` / `hk_stock`），`code` 写 `AAPL`、`00700.HK`。
- 期货：`code` 写品种代码，按主力连续。

完整字段语义见 `catalog/rule-nodes.json` 与 `docs/MARKETS.md` 的成交口径。