"""CLI offline commands and exit codes (no network)."""
from __future__ import annotations

import json

import pytest

from easyquant_research.cli import main


@pytest.mark.parametrize("argv", [
    ["fields", "--market", "cn_stock", "--json"],
    ["functions", "--search", "CROSS"],
    ["indicators", "--type", "SMA"],
    ["markets"],
    ["markets", "cn_future"],
    ["rules"],
    ["examples"],
    ["examples", "timing-ema-cross"],
    ["docs", "expression"],
    ["skill"],
    ["skill", "easyquant-expression"],
    ["tools"],
])
def test_offline_commands_ok(argv, capsys):
    assert main(argv) == 0
    assert capsys.readouterr().out.strip()


def test_fields_json_is_parseable(capsys):
    assert main(["fields", "--market", "cn_stock", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows and all(r["market"] == "cn_stock" for r in rows)


def test_validate_ok_and_issue(capsys):
    assert main(["validate", "screen", "--args", '{"condition": "roe_yearly > 15"}']) == 0
    capsys.readouterr()
    assert main(["validate", "screen", "--args", '{"bogus": 1}']) == 1
    assert "issue" in capsys.readouterr().out


def test_validate_from_file(tmp_path, capsys):
    f = tmp_path / "req.json"
    f.write_text('{"condition": "close > MA(close, 20)"}', encoding="utf-8")
    assert main(["validate", "screen", "--file", str(f)]) == 0


def test_skill_install(tmp_path, capsys):
    assert main(["skill", "--install", str(tmp_path)]) == 0
    for name in ("easyquant-research", "easyquant-expression"):
        assert (tmp_path / name / "SKILL.md").is_file()


def test_unknown_skill_usage_error(capsys):
    assert main(["skill", "nope"]) == 2


def test_version_exits_zero():
    with pytest.raises(SystemExit) as ei:
        main(["--version"])
    assert ei.value.code == 0


def test_no_command_is_usage_error():
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2