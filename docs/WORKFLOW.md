# 研究工作流

所有工具只做历史研究。先把想法写成正确的表达式或 DSL，再花运行时调用；算得慢的返回 `job_id`，按 `retry_after_seconds` 用 `get_job` 轮询。

## 0. 写之前先查（离线，不扣额度）

- 选股/排序表达式：`search_fields`、`search_functions`，或 `get_doc expression`。
- 择时规则：`search_indicators`、`get_indicator`、`get_rule_nodes`，或 `get_doc timing`。
- 市场与成交口径：`list_markets`、`get_market`，或 `get_doc markets`。
- 起步样例：`list_examples`、`get_example`。
- 参数形状自检：`validate_arguments TOOL {...}`（只校验请求形状，不评估策略）。

拿不准实时数据日期、额度、已解锁全局因子时，再调运行时 `catalog`。

## 1. 条件选股 `screen`

给 `condition`（可选 `rank_by` / `top_n` / `date`），返回某一天的命中总数、完整名单、每只的条件取值、行业与市值分布，以及可直接交给 `backtest_portfolio` 的参数。这是按条件计算的筛选结果，**不是推荐**。

## 2. 组合回测 `backtest_portfolio`

把选股条件与排序写成表达式，定期调仓回测。全市场首次算一个新表达式约 1~2 分钟，常返回 `job_id`。结果含收益、回撤、成本、持仓与 caveats。

## 3. 因子体检 `factor_report`

评估一个因子在 A 股全市场的预测力：Rank IC / ICIR、持有期衰减、分年度、剔除市值与行业后的 IC、与 Barra 风格相关性、分组收益、一句话结论与等级。因子可以是表达式，也可以是风格代码（`SIZE` / `VALUE` / `QUALITY` / `MOMENTUM` / `VOLATILITY` / `LIQUIDITY`）。首次约 1~3 分钟。

## 4. 稳健性检验 `robustness`（需登录）

参数同 `backtest_portfolio`。把条件里的数字常量上下浮动 20%、换调仓频率分别重跑，看收益是否随小改动大幅变化（过拟合），再看逐年超额是否稳定。约 3~6 分钟。服务端按开关开放，`tools/list` 里没有就不要调。

## 5. 择时回测 `backtest_timing`

单标的 DSL 规则树（见 `docs/TIMING_DSL.md`），可加止盈止损，给出买入持有对比。期货可多空。

## 6. AlphaSpec 规格（需登录）

把 declarative 策略规格作为研究草稿评估，**不创建交易策略**：

1. `research_capabilities`：提交前必读，当前能力、平台指定评估窗口与额度。一期仅 A 股日线，不支持的组合必须拒绝，不能缩短区间或改写范围。
2. `submit_artifact`：原样提交 artifact，返回 `artifact_id`。
3. `evaluate_artifact`：按平台指定区间入队（用评估配额）。
4. `get_evaluation`：`QUEUED/RUNNING` 按 `retry_after_seconds` 轮询；`DONE` 返回 `gate_result` 与 `run_ids`。`DONE` 只代表算完，`passed=false` 也是有效结果，不自动调参。
5. `get_research_evidence`：读该草稿关联回测的冻结 provenance、指标、净值与历史成交。缺失快照如实说明，不按当前配置补造。

AlphaSpec 契约本身见开源的 `alphaspec` 包（`pip install alphaspec`）。

## 下一步：托管平台策略创建与模拟运行

本包到研究草稿与回测证据为止。要把策略真正创建出来并模拟运行（模拟盘），请登录 EasyQuant 平台：<https://trade.goeasyquant.com/welcome>（英文 <https://trade.goeasyquant.com/en/welcome>）。平台提供可视化策略画布、AI 投研、历史回测与模拟交易；草稿先预览，保存与执行由你确认。下单与模拟/实盘运行不在本包范围内。

## 额度与去重

选股、回测、体检每人每天有次数额度（见 `catalog` 的 `daily_quota`）；同一组参数 12 小时内重复调用不扣次。**不要为凑一个通过的结果反复提交**——那正是评估要纠正的搜索运气。

## 回答纪律

只能引用工具返回的数字，原样转述 caveats；区分实际结果与推测；不对任何个股给买卖建议、评级或好坏判断。