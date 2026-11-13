"""Offline reference queries and request-shape validation (no network)."""
from __future__ import annotations

import pytest

from easyquant_research import reference as ref


def test_search_fields_market_and_query():
    rows = ref.search_fields("", "cn_stock")
    assert rows and all(r["market"] == "cn_stock" for r in rows)
    hit = ref.search_fields("roe", "cn_stock")
    assert any("roe" in str(r["names"]).lower() for r in hit)
    # a market with no valuation fields must not return A-share-only groups
    us = ref.search_fields("pe_ttm", "us_equity")
    assert us == []


def test_search_functions():
    assert any("CROSS" in f["signature"] for f in ref.search_functions("CROSS"))
    assert ref.search_functions("")  # empty query returns all


def test_indicators_and_get():
    assert ref.search_indicators("MACD")
    sma = ref.get_indicator("SMA")
    assert sma["type"] == "SMA" and sma["params"]
    assert ref.get_indicator("sma")["type"] == "SMA"  # case-insensitive
    with pytest.raises(ValueError):
        ref.get_indicator("NOT_AN_INDICATOR")


def test_rule_nodes():
    nodes = ref.get_rule_nodes()
    assert "rule_nodes" in nodes and "operands" in nodes


def test_markets():
    ids = {m["id"] for m in ref.list_markets()}
    assert ids == {"cn_stock", "cn_etf", "us_equity", "hk_stock", "cn_future"}
    assert ref.get_market("cn_future")["id"] == "cn_future"
    with pytest.raises(ValueError):
        ref.get_market("crypto")


def test_examples_all_validate():
    examples = ref.list_examples()
    assert len(examples) >= 7
    for e in examples:
        doc = ref.get_example(e["name"])
        assert doc["tool"] and isinstance(doc["arguments"], dict)
        issues = ref.validate_arguments(doc["tool"], doc["arguments"])
        assert issues == [], f"{e['name']}: {issues}"


def test_get_example_prefix_and_unknown():
    assert ref.get_example("timing-ema")["tool"] == "backtest_timing"
    with pytest.raises(ValueError):
        ref.get_example("does-not-exist")


def test_docs():
    assert set(ref.list_docs()) == {"expression", "timing", "markets", "workflow", "boundaries", "runtime"}
    for name in ref.list_docs():
        assert ref.get_doc(name).strip()
    with pytest.raises(ValueError):
        ref.get_doc("nope")


def test_skills():
    assert set(ref.list_skills()) == {"easyquant-research", "easyquant-expression"}
    for name in ref.list_skills():
        text = ref.get_skill(name)
        assert text.startswith("---")
        assert f"name: {name}" in text
    with pytest.raises(ValueError):
        ref.get_skill("nope")


def test_tool_contract_and_schema():
    assert len(ref.list_tools()) == 12
    assert ref.tool_schema("get_job")["required"] == ["job_id"]
    with pytest.raises(ValueError):
        ref.tool_schema("place_order")


def test_validate_arguments_ok_and_issues():
    assert ref.validate_arguments("screen", {"condition": "roe_yearly > 15"}) == []
    issues = ref.validate_arguments("screen", {"not_a_field": 1})
    assert issues and any(i["path"] for i in issues)
    # missing required argument
    missing = ref.validate_arguments("get_job", {})
    assert any("job_id" in i["message"] for i in missing)


def test_no_order_tool_anywhere():
    names = {t["name"] for t in ref.list_tools()}
    assert not any("order" in n or "trade" in n or "live" in n for n in names)