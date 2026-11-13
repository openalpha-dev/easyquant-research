---
name: easyquant-research
description: 用 EasyQuant 研究引擎做历史量化研究：A 股、场内 ETF、美股、港股的条件选股与组合回测，这些市场加期货（主力连续，可做空）的单标的择时回测，以及 A 股因子体检；点时口径，只做历史研究、不下单。Use when asked to screen stocks/ETFs, backtest a selection or timing idea, check a factor's predictive power (IC/ICIR/decay/neutralization), or submit an AlphaSpec research artifact for the EasyQuant engine.
---

# EasyQuant 研究

EasyQuant 研究引擎本身就是一个托管 MCP 服务器。本包提供两类工具：**离线参考**（查字段、单位、函数、指标、市场规则、示例，不联网、不扣额度）和**运行时桥接**（把请求转发到托管引擎，真正算选股/回测/体检）。引擎与数据在托管侧，本包不含本地回测引擎，也不伪造结果。

写表达式或择时规则前，**先用离线工具查清楚，不要猜字段名、单位或指标参数**；拿不准再调运行时 `catalog`（含实时数据日期、你的额度、已解锁的全局因子）。

## 安装（一次）

```bash
pip install "easyquant-research[mcp]"     # 离线参考 + CLI + MCP 服务器
easyquant-research --version
```

运行时命令读环境变量（也可用 `--base-url` / `--api-key` 覆盖）：

```bash
export EASYQUANT_BASE_URL="https://trade.goeasyquant.com"   # 可省略，默认即此
export EASYQUANT_API_KEY="eqk_..."                          # 可省略：省略则走匿名体验
export EASYQUANT_LANG="zh"                                  # 运行时消息语言 zh|en
```

API Key 在运行时个人中心生成，**只在 `/api/agent/v1/**` 生效**。绝不要把真实 key 写进会提交的文件或仓库。未登录时按 IP 开放 `catalog`、`screen`、`backtest_timing`、`backtest_portfolio`、`factor_report`、`get_job` 六个工具，计次工具合计每天有限次数；用完或调其它工具要求登录。

没有 shell、但连上了 `easyquant-research-mcp` 时，用 MCP 工具代替 CLI：下面的离线命令对应同名离线工具，运行时命令对应同名运行时工具。

## 工作流

1. **选市场。** `market` 传 `cn_stock`（默认）/ `cn_etf` / `us_equity` / `hk_stock` / `cn_future`。只有 A 股有估值、财务和全局因子；其它市场价量为主。期货在择时回测里写品种代码（如 `RB`），可做空。市场能力规则用离线 `get_market` / `easyquant-research markets <market>` 查。
2. **从示例起步。** `list_examples` / `easyquant-research examples` 列出内置示例；`get_example` / `easyquant-research examples <name>` 打印一个 `{tool, title, arguments}`，可直接喂给对应运行时工具。
3. **写条件或规则前查参考**（离线，不扣额度）：
   - 字段与单位：`search_fields(query, market)` / `easyquant-research fields --market <m> --search <词>`。中英文都能搜（`估值`、`roe`、`成交额`）。
   - 表达式函数：`search_functions(query)` / `easyquant-research functions --search <词>`。
   - 择时指标：`search_indicators(query, category)` 找候选，`get_indicator(type)` 看参数键、默认值、含义与**陷阱**；用前必读陷阱。
   - 择时规则节点：`get_rule_nodes()` / `easyquant-research rules`。
4. **校验请求形状**（离线，只查参数结构，不评估策略）：`validate_arguments(tool, arguments)` / `easyquant-research validate <tool> --file <f>`。把每个 issue 修掉再调运行时工具。
5. **调运行时工具**算结果。组合回测、因子体检可能返回 `job_id`：按返回的 `retry_after_seconds` 用 `get_job` 轮询，`SUCCEEDED` 时 `result` 才是完整文档，`FAILED` 时 error 说明原因。CLI 加 `--wait` 自动轮询。
6. **AlphaSpec 规格**（需登录）：先 `research_capabilities` 看能力与额度，再 `submit_artifact` → `evaluate_artifact` → `get_evaluation`（轮询）→ `get_research_evidence`。**第一阶段只支持 A 股日线**；不支持的市场/周期组合直接拒绝，不要缩短窗口或改写范围来凑。

回答用户时**用你与用户交流的语言**：CLI 加 `--lang en|zh`，MCP 运行时工具传 `lang`。判定依据是工具返回的数字、`code` 和 `metric` 键，这些不随语言变化。

## 表达式（选股 / 排序 / 因子）

表达式对每只标的、每个交易日算一个值。用作**选股条件**时结果非 0 即入选；用作**排序因子**时按数值从大到小排。字段名小写，函数名大写。

- 「且」用 `*`，「或」用 `MAX(a, b)`，分支用 `IF(cond, a, b)`。
- **不支持横截面 `RANK(x)`**：要「全市场排前 N」，把排序表达式写进 `rank_by` 并给 `top_n`，由引擎按全市场排。
- 单位陷阱（用前用 `search_fields` 核）：`total_mv` / `circ_mv` 是**万元**（100 亿 = `1e6`）；`dv_ttm`、`turnover_rate`、`roe_yearly` 等百分比字段直接写数值（3% 写 `3`）；亏损公司 `pe_ttm` 为空，低估值条件要加 `pe_ttm > 0`；绝对价格阈值用 `raw_close` 而非复权 `close`。
- 全局因子 `gf_<代码>` / `gfpct_<代码>`（当天全市场百分位 0~1）只 A 股可用，**可用列表是实时的**，以 `catalog` 返回为准，不要凭记忆写代码。
- 完整字段、函数与陷阱见 `easyquant-expression` 技能与 `get_doc("expression")`。

示例：

| 想法 | 写法 |
| --- | --- |
| ROE 大于 15% 且站上 60 日线 | `(roe_yearly > 15) * (close > MA(close, 60))` |
| 市盈率 15 倍以下、股息率 3% 以上 | `(pe_ttm > 0) * (pe_ttm < 15) * (dv_ttm > 3)` |
| 近 20 日涨幅（作排序因子） | `close / REF(close, 20) - 1` |

## 择时 DSL（单标的回测）

`backtest_timing` 收 `code` + `indicators`（`{别名: {type, 参数…}}`）+ 规则树 `entry` / `exit`（期货可加 `short_entry` / `short_exit`）。**日线收盘出信号、次日开盘成交**。

- 逻辑节点 `AND` / `OR` 的 `left` / `right` 是**规则**；`NOT` 的子节点放 `rule`。
- 比较节点 `GT GTE LT LTE EQ NEQ CROSS_UP CROSS_DOWN` 的 `left` / `right` 是**操作数**。
- 操作数是 `{"ind": 别名}`、`{"const": n}`、`PRICE` 或算术 `{"op": …, "left": …, "right": …}`。**绝不用裸数字**：`"right": 30` 非法，写 `{"const": 30}`。
- 指标类型与参数键以 `get_indicator` 为准，不要猜。规则节点全集见 `get_rule_nodes`。
- 美股 / 港股要传 `market`；期货 `code` 写品种根（如 `RB`），主力连续、换月已前复权。

完整语义见 `get_doc("timing")`，示例 `get_example("timing-ema-cross")`。

## 运行时工具

| 工具 | 用途 | 体验可用 |
| --- | --- | --- |
| `catalog` | 字段、函数、指标、市场规则、数据日期、额度、已解锁全局因子 | ✓ |
| `screen` | 某一天条件选股完整名单（含命中值、行业/市值分布、可直接用的回测参数） | ✓ |
| `backtest_portfolio` | 组合回测：按条件/排序选、定期调仓（前一日数据、次日开盘成交、先卖后买）；可能返回 `job_id` | ✓ |
| `backtest_timing` | 单标的择时回测（含止损与买入持有对照） | ✓ |
| `factor_report` | A 股因子体检：Rank IC/ICIR、衰减、分年、中性化 IC、Barra 风格相关、分组收益、评级；给 `expression` 或风格因子代码 | ✓ |
| `robustness` | 组合策略稳健性：数值常数 ±20% 扰动 + 调仓频率变化重跑，看收益是否剧烈摆动（过拟合）；参数同 `backtest_portfolio` | 需登录 |
| `get_job` | 轮询异步任务 | ✓ |
| `research_capabilities` | AlphaSpec 能力、固定评估窗口与额度 | 需登录 |
| `submit_artifact` | 原样提交 AlphaSpec 文档（契约/能力/归属校验），**只建研究草稿、不建交易策略**，返回 `artifact_id` | 需登录 |
| `evaluate_artifact` | 在平台固定窗口入队评估（扣评估额度），不接受自定义起止 | 需登录 |
| `get_evaluation` | 评估状态/结果；`DONE` 只代表算完，`passed=false` 也是有效结果 | 需登录 |
| `get_research_evidence` | 冻结的出处、指标、净值曲线与历史成交（历史研究证据，非模拟/实盘证据） | 需登录 |

完整契约（名称、描述、输入 schema、是否需登录）离线用 `list_research_tools` 查，实时用 `easyquant-research tools --live`。

## 边界（必须遵守）

- **只做历史研究。** 没有任何工具能下单、碰资金账户、创建或启用交易策略、管理 API Key。用户要这些时说明本包做不到，不要近似。
- **创建策略与模拟运行在托管平台。** 本包到研究草稿为止；用户要创建策略并模拟运行（模拟盘）时，引导其登录 EasyQuant 平台 <https://trade.goeasyquant.com/welcome>（英文 <https://trade.goeasyquant.com/en/welcome>），策略创建与模拟/实盘执行都在平台侧。
- **只引用工具返回的数字**，原样转述 caveats（数据日期、口径、样本区间、持仓只数变化等）。绝不编造引擎没返回的业绩。
- **不对个股给买卖建议。** `screen` 是计算出的名单，不是推荐。
- 选股、回测、体检每人每天有次数额度，同一组参数 12 小时内重复调用不扣次。**不要为凑通过结果反复提交**——那正是稳健性检验和评估门禁要纠正的搜索运气。
- AlphaSpec 的 `producer.searchTrials` 要如实计入本次搜索评估过的**每一个**候选（含丢弃的），少报会掩盖搜索运气。
- 数值交易成本（佣金、印花税、滑点、每手、交收）由运行时实时返回，**不要写死或凭记忆报**；离线参考只给能力类规则（T+1、涨跌停成交、点时财务、含退市股等）。

## 参考

`get_doc("expression")` 表达式 · `get_doc("timing")` 择时 DSL · `get_doc("markets")` 市场规则 · `get_doc("workflow")` 研究流程 · `get_doc("boundaries")` 边界 · `get_doc("runtime")` 运行时 MCP 接口与客户端配置。