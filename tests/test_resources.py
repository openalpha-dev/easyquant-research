"""Bundled-data loading and language selection (offline)."""
from __future__ import annotations

import pytest

from easyquant_research import _resources as res


def test_data_root_has_all_sections():
    root = res.data_root()
    for sub in ("catalog", "examples", "docs", "skills"):
        assert (root / sub).is_dir(), sub


def test_loaders_return_expected_shape():
    assert "cn_stock" in res.load_fields()["markets"]
    assert res.load_functions()["functions"]
    assert res.load_rule_nodes()["rule_nodes"]
    assert len(res.load_markets()["markets"]) == 5
    indicators = res.load_indicators()
    assert indicators["count"] == len(indicators["types"])


def test_tool_contract_counts():
    tools = res.load_tools()
    assert len(tools["tools"]) == 12
    assert len(tools["trialTools"]) == 6
    names = {t["name"] for t in tools["tools"]}
    assert {"catalog", "screen", "backtest_timing", "backtest_portfolio", "factor_report", "get_job"} <= names
    # every tool carries an input schema
    for t in tools["tools"]:
        assert t["inputSchema"]["type"] == "object"


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_default_lang_env(monkeypatch, lang):
    monkeypatch.setenv("EASYQUANT_LANG", lang)
    assert res.default_lang() == lang


def test_default_lang_locale(monkeypatch):
    monkeypatch.delenv("EASYQUANT_LANG", raising=False)
    monkeypatch.setenv("LC_ALL", "zh_CN.UTF-8")
    monkeypatch.delenv("LANG", raising=False)
    assert res.default_lang() == "zh"
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    assert res.default_lang() == "en"