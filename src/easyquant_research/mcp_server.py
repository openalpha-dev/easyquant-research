"""MCP server (stdio) for the EasyQuant research engine.

    pip install "easyquant-research[mcp]"
    easyquant-research-mcp                # started by the MCP client, not by hand

Two kinds of tools:
  * Offline reference (search_fields, search_indicators, get_rule_nodes, get_doc, ...): read the
    bundled catalog exported from the engine. No network, no quota — use them to write a correct
    expression or DSL before spending a runtime call.
  * Runtime bridge (catalog, screen, backtest_portfolio, backtest_timing, factor_report, ...):
    forward to the hosted research MCP at EASYQUANT_BASE_URL (default https://trade.goeasyquant.com)
    using EASYQUANT_API_KEY. Without a key the endpoint serves a limited anonymous trial.

Every runtime tool is historical research only. No tool here can place orders, touch fund
accounts, create or enable trading strategies, or manage API keys.
"""
from __future__ import annotations

from typing import Any

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer  # type: ignore[no-redef]
    from mcp.server.fastmcp.exceptions import ToolError  # type: ignore[no-redef]

from mcp.types import ToolAnnotations

from . import __version__
from . import reference as ref
from ._resources import default_lang
from .client import Client, ResearchError

INSTRUCTIONS = """EasyQuant 研究引擎：A 股、场内 ETF、美股、港股的条件选股与组合回测，以及这些市场加期货（主力连续，可做空）的择时回测，点时口径，只做历史研究、不下单。
写表达式或择时规则前，先用离线工具 search_fields / search_functions / search_indicators / get_rule_nodes 查字段、单位、函数与节点，不要猜；拿不准再调运行时 catalog（含实时数据日期、额度与已解锁全局因子）。
market 传 cn_stock / cn_etf / us_equity / hk_stock / cn_future 切换市场；期货在择时回测里写品种代码（如 RB）。
组合回测、因子体检可能返回 job_id，按 retry_after_seconds 用 get_job 轮询。
AlphaSpec 规格先调 research_capabilities，再 submit_artifact → evaluate_artifact → get_evaluation → get_research_evidence。
选股、回测、体检每人每天有次数额度，同一组参数 12 小时内重复调用不扣次；不要为凑通过结果反复提交。
回答只能引用工具返回的数字并原样转述 caveats，不对个股给买卖建议。"""

server = MCPServer("easyquant-research", instructions=INSTRUCTIONS, version=__version__)

# MCP hints: research-only (never destructive, no order tool); offline=closed catalog, runtime=open engine.
_OFFLINE = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
_RESEARCH = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
_DRAFT = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True)


def _lang(lang: str) -> str:
    if lang and lang not in ("en", "zh"):
        raise ToolError("lang must be en or zh")
    return lang or default_lang()


def _client(lang: str = "") -> Client:
    try:
        return Client(lang=_lang(lang))
    except ValueError as exc:
        raise ToolError(str(exc)) from None


def _clean(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


def _bridge(name: str, arguments: dict[str, Any], lang: str = "") -> dict[str, Any]:
    try:
        return _client(lang).call(name, arguments)
    except ResearchError as exc:
        raise ToolError(str(exc)) from None
    except OSError as exc:
        raise ToolError(f"cannot reach runtime: {exc}") from None


def _offline(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise ToolError(str(exc)) from None


# ---------------------------------------------------------------- offline reference

@server.tool(annotations=_OFFLINE)
def search_fields(query: str = "", market: str = "") -> list[dict[str, Any]]:
    """Offline: data fields with units and pitfalls, per market. query matches group/names/note
    (English or Chinese, e.g. "估值", "roe", "成交额"); market restricts to cn_stock / cn_etf /
    us_equity / hk_stock / cn_future. Write expressions from these fields, never invent names."""
    return _offline(ref.search_fields, query, market)


@server.tool(annotations=_OFFLINE)
def search_functions(query: str = "") -> list[dict[str, Any]]:
    """Offline: expression functions (MA, REF, STD, RSI, CROSS, IF, ...). query matches the
    signature or summary. Field names are lowercase, function names uppercase."""
    return _offline(ref.search_functions, query)


@server.tool(annotations=_OFFLINE)
def search_indicators(query: str = "", category: str = "") -> list[dict[str, Any]]:
    """Offline: timing DSL indicator types usable on daily bars (SMA, EMA, MACD, RSI, ATR, ...).
    query matches type/name/category/summary; category filters one category. Call get_indicator
    for parameters, defaults and pitfalls before using a type."""
    return _offline(ref.search_indicators, query, category)


@server.tool(annotations=_OFFLINE)
def get_indicator(type: str) -> dict[str, Any]:
    """Offline: full entry for one timing DSL indicator type — parameter keys, defaults, kinds,
    descriptions, summary and pitfalls. type is e.g. SMA, MACD, ATR."""
    return _offline(ref.get_indicator, type)


@server.tool(annotations=_OFFLINE)
def get_rule_nodes() -> dict[str, Any]:
    """Offline: the timing DSL rule-tree reference — logic/comparison/cross nodes, operand forms
    ({"ind":...}, {"const":n}, PRICE, arithmetic), and a worked example. Constants are {"const":n},
    never bare numbers."""
    return _offline(ref.get_rule_nodes)


@server.tool(annotations=_OFFLINE)
def list_markets() -> list[dict[str, Any]]:
    """Offline: markets the engine researches (id, name, note, supported tools)."""
    return _offline(ref.list_markets)


@server.tool(annotations=_OFFLINE)
def get_market(market: str) -> dict[str, Any]:
    """Offline: one market's capability trading rules (long-only, limit-up/down fills, point-in-time
    financials, delisted names included), universe and examples. Numeric costs (commission, tax,
    slippage, lot size) are returned live by the runtime catalog/results, not fixed here."""
    return _offline(ref.get_market, market)


@server.tool(annotations=_OFFLINE)
def list_examples() -> list[dict[str, Any]]:
    """Offline: bundled example requests (name, target tool, title) to start from."""
    return _offline(ref.list_examples)


@server.tool(annotations=_OFFLINE)
def get_example(name: str) -> dict[str, Any]:
    """Offline: one example request by name (a prefix is enough). It holds {tool, title, arguments}
    you can pass straight to the matching runtime tool."""
    return _offline(ref.get_example, name)


@server.tool(annotations=_OFFLINE)
def get_doc(name: str) -> str:
    """Offline: a reference document — expression, timing, markets, workflow, boundaries, runtime."""
    return _offline(ref.get_doc, name)


@server.tool(annotations=_OFFLINE)
def list_skills() -> list[str]:
    """Offline: names of the installable Agent Skills bundled in this package."""
    return _offline(ref.list_skills)


@server.tool(annotations=_OFFLINE)
def get_skill(name: str) -> str:
    """Offline: the full SKILL.md of one bundled Agent Skill (easyquant-research / easyquant-expression)."""
    return _offline(ref.get_skill, name)


@server.tool(annotations=_OFFLINE)
def list_research_tools() -> list[dict[str, Any]]:
    """Offline: the hosted research MCP tool contract (names, descriptions, input schemas, whether
    each requires login). Use it to see exact parameters before calling a runtime tool."""
    return _offline(ref.list_tools)


@server.tool(annotations=_OFFLINE)
def validate_arguments(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Offline: check a runtime tool's arguments against its input schema (request shape only — not
    a strategy evaluation). Returns {ok, issues}. Fix every issue before calling the tool."""
    issues = _offline(ref.validate_arguments, tool, arguments)
    return {"ok": not issues, "issues": issues}


# ---------------------------------------------------------------- runtime bridge

@server.tool(annotations=_RESEARCH)
def catalog(lang: str = "") -> dict[str, Any]:
    """Runtime: the engine's live catalog — fields with units, functions, timing indicators, market
    trading rules, current data date, your daily quota and unlocked global factors. Call it before
    writing an expression or rule when the offline reference is not enough. lang is en | zh."""
    return _bridge("catalog", {}, lang)


@server.tool(annotations=_RESEARCH)
def screen(market: str = "", condition: str = "", rank_by: str = "", rank_order: str = "",
           top_n: int = 0, date: str = "", limit: int = 0, lang: str = "") -> dict[str, Any]:
    """Runtime: screen one day's full list of symbols matching a condition (default latest trading
    day). Returns hit count, the list, each name's condition values, industry/market-cap distribution
    and ready-to-use backtest_portfolio arguments. A computed screen, not a recommendation. lang en|zh."""
    args = _clean(market=market or None, condition=condition or None, rank_by=rank_by or None,
                  rank_order=rank_order or None, top_n=top_n or None, date=date or None, limit=limit or None)
    return _bridge("screen", args, lang)


@server.tool(annotations=_RESEARCH)
def backtest_portfolio(market: str = "", condition: str = "", rank_by: str = "", rank_order: str = "",
                       top_n: int = 0, rebalance: str = "", weighting: str = "", max_position_pct: float = 0,
                       start: str = "", end: str = "", exits: dict | None = None, short_n: int = 0,
                       capital_budget_pct: float = 0, lang: str = "") -> dict[str, Any]:
    """Runtime: portfolio backtest — select by condition/rank, rebalance periodically (previous-day
    data, next-open fills, sell before buy). May return a job_id; poll get_job. Only quote the returned
    numbers and relay caveats; no buy/sell advice on individual names. lang en|zh."""
    args = _clean(market=market or None, condition=condition or None, rank_by=rank_by or None,
                  rank_order=rank_order or None, top_n=top_n or None, rebalance=rebalance or None,
                  weighting=weighting or None, max_position_pct=max_position_pct or None,
                  start=start or None, end=end or None, exits=exits, short_n=short_n or None,
                  capital_budget_pct=capital_budget_pct or None)
    return _bridge("backtest_portfolio", args, lang)


@server.tool(annotations=_RESEARCH)
def backtest_timing(code: str, indicators: dict, market: str = "", entry: dict | None = None,
                    exit: dict | None = None, short_entry: dict | None = None, short_exit: dict | None = None,
                    capital_budget_pct: float = 0, start: str = "", end: str = "",
                    exits: dict | None = None, lang: str = "") -> dict[str, Any]:
    """Runtime: single-symbol daily timing backtest from a DSL rule tree (indicators + entry/exit),
    with optional stops and a buy-and-hold comparison. Futures (code like RB) may use short_entry /
    short_exit. US/HK need market. Only quote returned numbers. lang en|zh."""
    args = _clean(code=code, indicators=indicators, market=market or None, entry=entry, exit=exit,
                  short_entry=short_entry, short_exit=short_exit,
                  capital_budget_pct=capital_budget_pct or None, start=start or None, end=end or None, exits=exits)
    return _bridge("backtest_timing", args, lang)


@server.tool(annotations=_RESEARCH)
def factor_report(expression: str = "", factor: str = "", window_years: int = 0,
                  lang: str = "") -> dict[str, Any]:
    """Runtime: factor checkup on the A-share universe — Rank IC/ICIR, decay, yearly, neutralized IC,
    Barra style correlation, group returns, verdict and grade. Give expression OR a style factor code
    (SIZE/VALUE/QUALITY/MOMENTUM/VOLATILITY/LIQUIDITY). May return a job_id. lang en|zh."""
    args = _clean(expression=expression or None, factor=factor or None, window_years=window_years or None)
    return _bridge("factor_report", args, lang)


@server.tool(annotations=_RESEARCH)
def robustness(market: str = "", condition: str = "", rank_by: str = "", rank_order: str = "",
               top_n: int = 0, rebalance: str = "", weighting: str = "", max_position_pct: float = 0,
               start: str = "", end: str = "", exits: dict | None = None, short_n: int = 0,
               capital_budget_pct: float = 0, lang: str = "") -> dict[str, Any]:
    """Runtime: robustness check of a portfolio strategy — perturb numeric constants ±20% and vary
    rebalance frequency, re-run, and see whether returns swing (overfitting) and yearly excess is stable.
    Same arguments as backtest_portfolio. Login required; may be absent if the server disables it. lang en|zh."""
    args = _clean(market=market or None, condition=condition or None, rank_by=rank_by or None,
                  rank_order=rank_order or None, top_n=top_n or None, rebalance=rebalance or None,
                  weighting=weighting or None, max_position_pct=max_position_pct or None,
                  start=start or None, end=end or None, exits=exits, short_n=short_n or None,
                  capital_budget_pct=capital_budget_pct or None)
    return _bridge("robustness", args, lang)


@server.tool(annotations=_RESEARCH)
def get_job(job_id: str, lang: str = "") -> dict[str, Any]:
    """Runtime: poll an async job. QUEUED/RUNNING → wait retry_after_seconds and call again;
    SUCCEEDED → result is the full document; FAILED → error says why. lang en|zh."""
    return _bridge("get_job", {"job_id": job_id}, lang)


@server.tool(annotations=_RESEARCH)
def research_capabilities(lang: str = "") -> dict[str, Any]:
    """Runtime: read before submitting an AlphaSpec artifact — current capabilities, the platform's
    fixed evaluation windows and your quota. Phase 1 is A-share daily only; reject unsupported
    combinations rather than shortening the window or rewriting the scope. lang en|zh."""
    return _bridge("research_capabilities", {}, lang)


@server.tool(annotations=_DRAFT)
def submit_artifact(document: dict, lang: str = "") -> dict[str, Any]:
    """Runtime: submit an AlphaSpec artifact as-is (contract validation, capability and ownership
    checks). Creates a research draft only — never a trading strategy. Returns artifact_id. lang en|zh."""
    return _bridge("submit_artifact", {"document": document}, lang)


@server.tool(annotations=_DRAFT)
def evaluate_artifact(artifact_id: int, lang: str = "") -> dict[str, Any]:
    """Runtime: queue an evaluation on the platform's fixed windows (uses your evaluation quota).
    Poll get_evaluation afterwards. Does not accept custom start/end or raise quota. lang en|zh."""
    return _bridge("evaluate_artifact", {"artifact_id": artifact_id}, lang)


@server.tool(annotations=_RESEARCH)
def get_evaluation(artifact_id: int, lang: str = "") -> dict[str, Any]:
    """Runtime: evaluation status/result. QUEUED/RUNNING → poll by retry_after_seconds; DONE → gate_result
    and run_ids. DONE only means the computation finished; passed=false is a valid result. lang en|zh."""
    return _bridge("get_evaluation", {"artifact_id": artifact_id}, lang)


@server.tool(annotations=_RESEARCH)
def get_research_evidence(artifact_id: int, run_id: int, lang: str = "") -> dict[str, Any]:
    """Runtime: the frozen provenance, metrics, equity curve and historical fills of the backtest a
    draft evaluation ran. This is historical research evidence, not paper/live trading evidence;
    report missing snapshots honestly, never fabricate from current config. lang en|zh."""
    return _bridge("get_research_evidence", {"artifact_id": artifact_id, "run_id": run_id}, lang)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()