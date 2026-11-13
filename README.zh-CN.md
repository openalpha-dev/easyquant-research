# EasyQuant Research

**EasyQuant 量化研究引擎的开源 MCP 连接器与 Agent Skills——面向 AI 智能体的量化交易研究：条件选股、组合与择时回测、因子 / alpha 研究，覆盖 A 股、场内 ETF、美股、港股与期货。点时口径，Python，只做历史研究。**

[English](README.md) ·
[表达式](docs/EXPRESSION.md) ·
[择时 DSL](docs/TIMING_DSL.md) ·
[市场规则](docs/MARKETS.md) ·
[运行时 MCP](docs/RUNTIME_MCP.md) ·
[引擎：EasyQuant 易量策略](https://www.goeasyquant.com)

`easyquant-research` 是 EasyQuant 研究引擎的开源客户端。引擎与数据在托管侧，本包只开源 agent
诚实使用它们所需的那一层：

- **离线参考目录**——带单位的字段、表达式函数、带参数与陷阱的择时指标、市场交易规则、示例与文档，
  全部从引擎导出；
- **MCP 桥接**——一个 stdio MCP 服务器和 Python/CLI 客户端，把请求经 HTTPS 转发到托管研究 MCP；
- **可安装的 Agent Skills**——教 agent 先查再写、校验请求形状、轮询异步任务、只引用引擎返回的数字。

**本包不含本地回测引擎，也不伪造结果。** 离线工具只做查询和参数形状校验（不扣额度）；运行时工具
调用引擎，由引擎真正计算。

```bash
pip install "easyquant-research[mcp]"
easyquant-research fields --market cn_stock --search 估值     # 离线，不扣额度
easyquant-research screen --condition "(roe_yearly > 15) * (close > MA(close, 60))"
```

## 为什么开源一个客户端

AI 让「写策略」变便宜了，却没让「相信策略」变便宜。一个 agent 一下午能产出上百条候选想法，
但它自己说不清哪几条经得起前视偏差、多重检验和真实交易规则的考验。验证需要一个有点时数据、
按市场自身规则撮合的真实引擎，也需要 agent 在使用它时不臆造字段、单位或业绩数字。

本包就是让这件事成立的那道边界。参考目录从跑回测的同一个引擎导出，所以 agent 写的字段就是引擎读的
字段。技能强制这套纪律：先查再猜、花一次调用前先校验形状、原样转述 caveats、绝不引用引擎没返回的
数字。引擎本身——数据、成本、撮合、门禁——留在托管侧，才能保持正确与点时。

它与开放策略文档契约 **AlphaSpec** 配套：AlphaSpec 定义一条策略*是什么*（一份可检查的 JSON 规则树），
`easyquant-research` 是 agent 在 EasyQuant 上*研究*它的方式——选股、回测、因子体检，再用
`submit_artifact` 把一份 AlphaSpec 文档作为研究草稿提交。同一个引擎、同一套词汇，没有私有捷径。

## 覆盖范围

| 市场 | `market` | 选股 | 组合回测 | 择时回测 | 因子体检 |
|---|---|---|---|---|---|
| A 股 | `cn_stock`（默认） | ✓ | ✓ | ✓ | ✓ |
| 场内 ETF | `cn_etf` | ✓ | ✓ | ✓ | — |
| 美股 | `us_equity` | ✓ | ✓ | ✓ | — |
| 港股 | `hk_stock` | ✓ | ✓ | ✓ | — |
| 期货（主力连续） | `cn_future` | ✓ | ✓（多空） | ✓（多空） | — |

可用作**选股器**、**组合回测**、单标的**择时回测**或**因子投资 / alpha 研究**工具。择时 DSL 内置
130+ 个日线可用**技术指标**（SMA、EMA、MACD、RSI、ATR 等），带参数与陷阱说明；表达式语言覆盖估值、
基本面、动量、价值、质量、波动率与流动性因子。

只有 A 股有估值、财务和全局因子，其它市场价量为主。期货写品种根（如 `RB`），换月已前复权，可做空。
市场规则是按市场作用域保留、而非一刀切移除：中国的 T+1、涨跌停成交、每手在存在的地方照样生效。
数值成本（佣金、印花税、滑点、每手）由引擎实时返回，不在本包写死。见 [docs/MARKETS.md](docs/MARKETS.md)。

## 快速上手

### 命令行

```bash
pip install easyquant-research

# 离线参考——不联网、不扣额度
easyquant-research fields --market cn_stock --search roe
easyquant-research functions --search CROSS
easyquant-research indicators --type MACD          # 参数、默认值、陷阱
easyquant-research rules                           # 择时 DSL 规则树参考
easyquant-research examples                        # 可起步的请求
easyquant-research validate screen --file req.json # 校验参数形状

# 运行时——读 EASYQUANT_BASE_URL / EASYQUANT_API_KEY（无 key 走匿名体验）
export EASYQUANT_API_KEY=eqk_...                   # 在引擎个人中心生成
easyquant-research catalog                         # 实时字段、数据日期、额度、全局因子
easyquant-research screen --condition "(pe_ttm > 0) * (pe_ttm < 15) * (dv_ttm > 3)"
easyquant-research portfolio --file examples/portfolio-momentum.json --wait
easyquant-research timing --file examples/timing-ema-cross.json --wait
easyquant-research factor --expression "incttm_n_income_attr_p / total_mv" --wait
```

### Python

```python
from easyquant_research import Client, reference as ref

ref.search_fields("估值", "cn_stock")        # 离线，不扣额度
ref.validate_arguments("screen", {"condition": "roe_yearly > 15"})

c = Client()                                 # 读 EASYQUANT_BASE_URL / EASYQUANT_API_KEY
hits = c.call("screen", {"condition": "(roe_yearly > 15) * (close > MA(close, 60))"})
res = c.call("backtest_portfolio", {"rank_by": "close / REF(close, 60) - 1", "top_n": 30})
if res.get("job_id"):
    res = c.wait_job(res["job_id"])          # 按 retry_after_seconds 轮询 get_job
```

### Agent Skill（能跑命令的 agent）

```bash
easyquant-research skill --install ~/.claude/skills   # 或你的 agent 的技能目录
```

装两个技能。`easyquant-research` 教 agent 完整研究流程：选市场、从示例起步、查字段/指标而非臆造、
校验请求形状、调运行时、轮询任务、提交 AlphaSpec 草稿、只报返回的数字并带上 caveats。
`easyquant-expression` 教它把选股或择时想法写成正确的表达式——字段、单位、函数，以及那些会静默
算错的陷阱（市值单位万元、百分比直接写数值、亏损公司市盈率为空、复权价与原价）。

### MCP（没有 shell 的 agent）

```json
{
  "mcpServers": {
    "easyquant-research": {
      "command": "easyquant-research-mcp",
      "env": { "EASYQUANT_API_KEY": "eqk_..." }
    }
  }
}
```

客户端经 stdio 与本地 `easyquant-research-mcp` 进程说 MCP；该进程用与 CLI 相同的客户端经 HTTPS 调
托管引擎，所以 key 只会去到引擎。支持 streamable-http + OAuth 的客户端可直连引擎
`https://trade.goeasyquant.com/api/agent/v1/mcp`。见 [docs/RUNTIME_MCP.md](docs/RUNTIME_MCP.md)。

工具：`search_fields`、`search_functions`、`search_indicators`、`get_indicator`、`get_rule_nodes`、
`list_markets`、`get_market`、`list_examples`、`get_example`、`get_doc`、`list_skills`、`get_skill`、
`list_research_tools`、`validate_arguments`（离线），以及 `catalog`、`screen`、`backtest_portfolio`、
`backtest_timing`、`factor_report`、`robustness`、`get_job`、`research_capabilities`、
`submit_artifact`、`evaluate_artifact`、`get_evaluation`、`get_research_evidence`（运行时）。
**没有任何下单工具。**

## 只做历史研究

这里每个工具都是历史研究。没有工具能下单、碰资金账户、创建或启用交易策略、管理 API Key。
API Key 只在 `/api/agent/v1/**` 生效；agent 与个人走同一道门，而这道门不通向执行。
`submit_artifact` 只建研究草稿，绝不建交易策略。技能要求 agent 只引用返回的数字、原样转述 caveats、
不对个股给买卖建议。

要**创建策略并模拟运行（模拟盘）**，请登录托管的 EasyQuant 平台——策略创建与模拟/实盘执行在平台侧，
不在本包范围内：[https://trade.goeasyquant.com/welcome](https://trade.goeasyquant.com/welcome)
（英文 [https://trade.goeasyquant.com/en/welcome](https://trade.goeasyquant.com/en/welcome)）。
平台提供可视化策略画布、AI 投研、历史回测与模拟交易；草稿先预览，保存与执行由你确认。

## 关于 EasyQuant

[EasyQuant 易量策略](https://www.goeasyquant.com) 是一个量化策略交付平台：研究、回测、模拟与实盘
跑在同一个引擎上，所以你在回测里看到的数字，与真正到市场的委托是同一套口径算出来的。本包开放的是
它的**研究**面——与它自家 AI 研究助手所用的同一套公开 API，不多一分。
[个人版](https://trade.goeasyquant.com) 让任何用户免费创建 API Key；匿名体验无需 key 即可覆盖六个
只读研究工具。

## 仓库结构

```
catalog/             从引擎导出的离线参考（字段、函数、指标、规则节点、市场、工具契约）
examples/            示例请求，每个 {tool, title, arguments}，已对 schema 校验
docs/                表达式、择时 DSL、市场、流程、边界、运行时 MCP
src/easyquant_research/   参考查询、运行时客户端、CLI、MCP 服务器
skills/              Agent Skills（easyquant-research、easyquant-expression）
tools/               export_indicator_catalog.py——从引擎重新生成指标目录
tests/               离线 + mock 传输测试（不联网）
```

wheel 把 `catalog/`、`examples/`、`docs/`、`skills/` 的副本打进 `easyquant_research/_data`，
所以装好的技能无需 checkout 就能经 CLI 取到一切。指标目录可复现：
`python tools/export_indicator_catalog.py` 读引擎的单一真源指标元数据，重写 `catalog/indicators.json`。

## 关键词

量化交易 · 量化研究 · 量化投资 · 量化金融 · 算法交易 · 程序化交易 · 系统化交易 · 回测 · 历史回测 ·
选股 · 股票筛选 · 条件选股 · 因子投资 · 因子研究 · alpha 因子 · 技术指标 · 技术分析 · 交易策略 ·
策略 DSL · 声明式策略 · 规则策略 · 择时 · 组合回测 · 调仓 · 动量 · 价值 · 质量 · 波动率 · 流动性 ·
市场中性 · Barra 风格因子 · Rank IC · ICIR · 夏普比率 · 最大回撤 · 点时数据 · 前视偏差 ·
幸存者偏差 · 过拟合 · A 股 · 中国股市 · ETF · 期货 · 美股 · 港股 · MCP · Model Context Protocol ·
AI agent · 智能体 · 大模型 · LLM · Claude · Cursor · Python · 开源 · 金融科技 · AlphaSpec ·
EasyQuant · 模拟交易。

## 许可证

Apache-2.0