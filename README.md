# EasyQuant Research

**Open-source MCP connector and Agent Skills for quantitative trading research on the EasyQuant engine — stock screening, portfolio & timing backtesting, and factor / alpha research across China A-shares, ETFs, US/HK equities and futures. Point-in-time, Python, research only.**

[中文说明](README.zh-CN.md) ·
[Expression](docs/EXPRESSION.md) ·
[Timing DSL](docs/TIMING_DSL.md) ·
[Markets](docs/MARKETS.md) ·
[Runtime MCP](docs/RUNTIME_MCP.md) ·
[Engine: EasyQuant](https://www.goeasyquant.com)

`easyquant-research` is the open client side of the EasyQuant research engine. The engine and its
data stay hosted; this package ships what an agent needs to use them honestly:

- an **offline reference catalog** — fields with units, expression functions, timing-DSL indicators
  with parameters and pitfalls, market trading rules, examples and docs, exported from the engine;
- an **MCP bridge** — a stdio MCP server and a Python/CLI client that forward requests to the hosted
  research MCP over HTTPS;
- **installable Agent Skills** that teach an agent to look things up before guessing, validate the
  request shape, poll async jobs, and quote only the numbers the engine returned.

There is **no local backtest engine here and no fabricated results**. Offline tools look things up
and check argument shape (quota-free); runtime tools call the engine, which does the computing.

```bash
pip install "easyquant-research[mcp]"
easyquant-research fields --market cn_stock --search 估值     # offline, no quota
easyquant-research screen --condition "(roe_yearly > 15) * (close > MA(close, 60))"
```

## Why a client, and why open

AI made writing strategies cheap; it did not make trusting them cheap. An agent can produce a
hundred candidate ideas in an afternoon, but it cannot tell on its own which survive look-ahead
bias, multiple testing and real trading rules. That verification needs a real engine with
point-in-time data and the market's own trading rules — and it needs the agent to use that engine
without inventing fields, units or performance figures.

This package is the boundary that makes that possible. The reference catalog is exported from the
same engine that runs the backtest, so the field an agent writes is the field the engine reads. The
skills enforce the discipline: look up before guessing, validate the shape before spending a call,
relay caveats, never quote a number the engine did not return. The engine itself — data, costs,
matching, gate — stays hosted, where it can be kept correct and point-in-time.

It pairs with **[AlphaSpec](https://www.goeasyquant.com)**, the open strategy-document contract:
AlphaSpec defines what a strategy *is* (a checkable JSON rule tree); `easyquant-research` is how an
agent *researches* one on EasyQuant — screen, backtest, factor-check, then `submit_artifact` an
AlphaSpec document as a research draft. Same engine, same vocabulary, no private shortcut.

## What it covers

| Market | `market` | Screen | Portfolio backtest | Timing backtest | Factor checkup |
|---|---|---|---|---|---|
| China A-shares | `cn_stock` (default) | ✓ | ✓ | ✓ | ✓ |
| On-exchange ETFs | `cn_etf` | ✓ | ✓ | ✓ | — |
| US equities | `us_equity` | ✓ | ✓ | ✓ | — |
| HK equities | `hk_stock` | ✓ | ✓ | ✓ | — |
| Futures (main continuous) | `cn_future` | ✓ | ✓ (long/short) | ✓ (long/short) | — |

Use it as a **stock screener**, a **portfolio backtester**, a single-symbol **timing backtester**, or
a **factor-investing / alpha-research** tool. The timing DSL ships 130+ daily-usable **technical
indicators** (SMA, EMA, MACD, RSI, ATR, …) with written parameters and pitfalls; the expression
language covers valuation, fundamentals, momentum, value, quality, volatility and liquidity factors.

Only A-shares carry valuation, financials and global factors; the other markets are price-volume
based. Futures use a variety root (e.g. `RB`), back-adjusted at rolls, and can be shorted. Market
rules are scoped, not removed: China's T+1, price-limit fills and lot sizes apply where they exist.
Numeric costs (commission, tax, slippage, lot size) are returned live by the engine, not hard-coded
here. See [docs/MARKETS.md](docs/MARKETS.md).

## Getting started

### Command line

```bash
pip install easyquant-research

# Offline reference — no network, no quota
easyquant-research fields --market cn_stock --search roe
easyquant-research functions --search CROSS
easyquant-research indicators --type MACD          # parameters, defaults, pitfalls
easyquant-research rules                           # timing-DSL rule-tree reference
easyquant-research examples                        # requests to start from
easyquant-research validate screen --file req.json # check argument shape

# Runtime — reads EASYQUANT_BASE_URL / EASYQUANT_API_KEY (anonymous trial without a key)
export EASYQUANT_API_KEY=eqk_...                   # created in the engine's account page
easyquant-research catalog                         # live fields, data date, quota, global factors
easyquant-research screen --condition "(pe_ttm > 0) * (pe_ttm < 15) * (dv_ttm > 3)"
easyquant-research portfolio --file examples/portfolio-momentum.json --wait
easyquant-research timing --file examples/timing-ema-cross.json --wait
easyquant-research factor --expression "incttm_n_income_attr_p / total_mv" --wait
```

### Python

```python
from easyquant_research import Client, reference as ref

ref.search_fields("估值", "cn_stock")        # offline, quota-free
ref.validate_arguments("screen", {"condition": "roe_yearly > 15"})

c = Client()                                 # reads EASYQUANT_BASE_URL / EASYQUANT_API_KEY
hits = c.call("screen", {"condition": "(roe_yearly > 15) * (close > MA(close, 60))"})
res = c.call("backtest_portfolio", {"rank_by": "close / REF(close, 60) - 1", "top_n": 30})
if res.get("job_id"):
    res = c.wait_job(res["job_id"])          # polls get_job by retry_after_seconds
```

### Agent Skill (agents that can run commands)

```bash
easyquant-research skill --install ~/.claude/skills   # or your agent's skills directory
```

This installs two skills. `easyquant-research` teaches the agent the whole research workflow:
pick a market, start from an example, look fields/indicators up instead of guessing, validate the
request shape, call the runtime, poll jobs, submit AlphaSpec drafts, and report only returned
numbers with their caveats. `easyquant-expression` teaches it to turn a selection or timing idea
into a correct expression — fields, units, functions and the pitfalls that silently produce wrong
results (market cap in 万元, percentages as plain numbers, loss-making PE empty, adjusted vs raw
price).

### MCP (agents without a shell)

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

The client speaks MCP to a local `easyquant-research-mcp` process over stdio; that process calls the
hosted engine over HTTPS with the same client as the CLI, so the key only ever goes to the engine.
Clients that support streamable-http + OAuth can connect to the engine directly at
`https://trade.goeasyquant.com/api/agent/v1/mcp`. See [docs/RUNTIME_MCP.md](docs/RUNTIME_MCP.md).

Tools: `search_fields`, `search_functions`, `search_indicators`, `get_indicator`, `get_rule_nodes`,
`list_markets`, `get_market`, `list_examples`, `get_example`, `get_doc`, `list_skills`, `get_skill`,
`list_research_tools`, `validate_arguments` (offline) and `catalog`, `screen`, `backtest_portfolio`,
`backtest_timing`, `factor_report`, `robustness`, `get_job`, `research_capabilities`,
`submit_artifact`, `evaluate_artifact`, `get_evaluation`, `get_research_evidence` (runtime).
**There is no order tool.**

## Research only

Every tool here is historical research. No tool can place orders, touch fund accounts, create or
enable trading strategies, or manage API keys. An API key works only under `/api/agent/v1/**`; the
agent passes through exactly the same door as a person, and that door does not lead to execution.
`submit_artifact` creates a research draft, never a trading strategy. The skills require the agent
to quote only returned numbers, relay caveats, and give no buy/sell advice on individual names.

To **create a strategy and run it in paper trading (simulation)**, log in to the hosted EasyQuant
platform — strategy creation and paper/live execution live there, outside this package:
[https://trade.goeasyquant.com/welcome](https://trade.goeasyquant.com/welcome)
(English: [https://trade.goeasyquant.com/en/welcome](https://trade.goeasyquant.com/en/welcome)).
The platform offers a visual strategy canvas, AI-assisted research, backtesting and paper trading;
drafts are previewed first and you approve saves and runs.

## About EasyQuant

[EasyQuant](https://www.goeasyquant.com) is a quantitative strategy delivery platform: research,
backtesting, paper trading and live execution on one engine, so the number you saw in a backtest is
computed the same way as the order that reaches the market. This package opens its **research**
surface — the same public API its own AI research assistant uses, and nothing more. The
[personal edition](https://trade.goeasyquant.com) lets any user create an API key for free; an
anonymous trial covers the six read-only research tools without a key.

## Repository layout

```
catalog/             offline reference exported from the engine (fields, functions, indicators,
                     rule nodes, markets, tool contract)
examples/            example requests, each {tool, title, arguments}, validated against the schemas
docs/                expression, timing DSL, markets, workflow, boundaries, runtime MCP
src/easyquant_research/   reference queries, runtime client, CLI, MCP server
skills/              Agent Skills (easyquant-research, easyquant-expression)
tools/               export_indicator_catalog.py — regenerate the indicator catalog from the engine
tests/               offline + mocked-transport tests (no network)
```

The wheel carries a copy of `catalog/`, `examples/`, `docs/` and `skills/` under
`easyquant_research/_data`, so an installed skill reaches everything through the CLI without a
checkout. The indicator catalog is reproducible: `python tools/export_indicator_catalog.py` reads
the engine's single-source indicator metadata and rewrites `catalog/indicators.json`.

## Keywords

Quantitative trading · quantitative research · quantitative finance · algorithmic trading ·
systematic trading · backtesting · stock screener · stock screening · stock selection ·
factor investing · factor research · alpha factors · alpha research · technical analysis ·
technical indicators · trading strategy · strategy DSL · declarative strategy · rule-based strategy ·
timing strategy · portfolio backtest · rebalancing · momentum · value · quality · volatility ·
liquidity · market neutral · Barra style factors · Rank IC · ICIR · Sharpe ratio · drawdown ·
point-in-time data · look-ahead bias · survivorship bias · overfitting · deflated Sharpe ·
China A-shares · ETF · futures · US equities · HK stocks · MCP · Model Context Protocol ·
AI agent · LLM · Claude · Cursor · Codex · Agent Skills · Python · open source · fintech ·
AlphaSpec · EasyQuant · paper trading.

## License

Apache-2.0