"""MCP server wiring. Skipped when the optional `mcp` extra is not installed."""
from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from easyquant_research import mcp_server as srv  # noqa: E402

OFFLINE = [
    "search_fields", "search_functions", "search_indicators", "get_indicator", "get_rule_nodes",
    "list_markets", "get_market", "list_examples", "get_example", "get_doc", "list_skills",
    "get_skill", "list_research_tools", "validate_arguments",
]
RUNTIME = [
    "catalog", "screen", "backtest_portfolio", "backtest_timing", "factor_report", "robustness",
    "get_job", "research_capabilities", "submit_artifact", "evaluate_artifact", "get_evaluation",
    "get_research_evidence",
]


def test_server_and_main_exist():
    assert srv.server is not None
    assert callable(srv.main)


@pytest.mark.parametrize("name", OFFLINE + RUNTIME)
def test_tool_function_defined(name):
    assert callable(getattr(srv, name))


def test_no_order_tool():
    assert not any("order" in n or "live" in n for n in OFFLINE + RUNTIME)


def test_offline_tool_runs_without_network():
    # an offline tool must work with no runtime configured
    assert srv.search_fields("roe", "cn_stock")
    assert srv.get_indicator("SMA")["type"] == "SMA"
    assert srv.validate_arguments("screen", {"condition": "roe_yearly > 15"})["ok"] is True