"""Offline reference queries over the bundled catalog, docs, examples and skills.

Pure functions, no network and no MCP dependency, so they are usable from the CLI, the MCP
server and tests alike. The data is exported from the EasyQuant engine (see
tools/export_indicator_catalog.py); these helpers only search and format it. Nothing here
evaluates a strategy — the engine does that, behind the runtime tools in client.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from ._resources import (data_root, load_fields, load_functions, load_indicators, load_markets,
                         load_rule_nodes, load_tools)

_DOCS = {
    "expression": "EXPRESSION.md",
    "timing": "TIMING_DSL.md",
    "markets": "MARKETS.md",
    "workflow": "WORKFLOW.md",
    "boundaries": "BOUNDARIES.md",
    "runtime": "RUNTIME_MCP.md",
}


def _matches(query: str, *parts: Any) -> bool:
    if not query:
        return True
    q = query.lower()
    return any(q in str(p).lower() for p in parts if p is not None)


# ---------------------------------------------------------------- fields / functions

def search_fields(query: str = "", market: str = "") -> list[dict[str, Any]]:
    """Field groups (with units and pitfalls) per market. market restricts to one market id."""
    markets = load_fields()["markets"]
    rows = []
    for mid, m in markets.items():
        if market and mid != market:
            continue
        for f in m["fields"]:
            if _matches(query, f.get("group"), f.get("names"), f.get("note")):
                rows.append({"market": mid, **f})
    return rows


def search_functions(query: str = "") -> list[dict[str, Any]]:
    return [f for f in load_functions()["functions"] if _matches(query, f["signature"], f["summary"])]


def expression_how() -> dict[str, Any]:
    fields = load_fields()
    return {"how": fields["how"], "global_factors": fields["global_factors"],
            "functions_how": load_functions()["how"]}


# ---------------------------------------------------------------- timing DSL

def search_indicators(query: str = "", category: str = "") -> list[dict[str, Any]]:
    rows = []
    for t in load_indicators()["types"]:
        if category and t.get("category") != category:
            continue
        if _matches(query, t["type"], t.get("name"), t.get("category"), t.get("summary")):
            rows.append({"type": t["type"], "name": t.get("name"), "category": t.get("category"),
                         "params": t.get("compact", []), "summary": t.get("summary")})
    return rows


def get_indicator(type: str) -> dict[str, Any]:
    t = next((x for x in load_indicators()["types"] if x["type"] == type.upper()), None)
    if t is None:
        raise ValueError(f"unknown indicator type {type}; use search_indicators")
    return t


def get_rule_nodes() -> dict[str, Any]:
    return load_rule_nodes()


# ---------------------------------------------------------------- markets

def list_markets() -> list[dict[str, Any]]:
    return [{"id": m["id"], "name": m["name"], "note": m["note"], "supports": m.get("supports", [])}
            for m in load_markets()["markets"]]


def get_market(market: str) -> dict[str, Any]:
    m = next((x for x in load_markets()["markets"] if x["id"] == market), None)
    if m is None:
        raise ValueError(f"unknown market {market}; known: {', '.join(x['id'] for x in list_markets())}")
    return m


def market_defaults() -> dict[str, Any]:
    d = load_markets()
    return {"defaults": d["defaults"], "costs_note": d["costs_note"]}


# ---------------------------------------------------------------- examples / docs / skills

def _example_files() -> list[Path]:
    return sorted((data_root() / "examples").glob("*.json"))


def list_examples() -> list[dict[str, Any]]:
    out = []
    for f in _example_files():
        doc = json.loads(f.read_text(encoding="utf-8"))
        out.append({"name": f.stem, "tool": doc.get("tool"), "title": doc.get("title")})
    return out


def get_example(name: str) -> dict[str, Any]:
    match = [f for f in _example_files() if f.stem == name or f.stem.startswith(name)]
    if not match:
        raise ValueError(f"no example named {name}; use list_examples")
    return json.loads(match[0].read_text(encoding="utf-8"))


def list_docs() -> list[str]:
    return sorted(_DOCS)


def get_doc(name: str) -> str:
    if name not in _DOCS:
        raise ValueError(f"name must be one of {', '.join(sorted(_DOCS))}")
    return (data_root() / "docs" / _DOCS[name]).read_text(encoding="utf-8")


def _skill_names() -> list[str]:
    return sorted(p.parent.name for p in (data_root() / "skills").glob("*/SKILL.md"))


def list_skills() -> list[str]:
    return _skill_names()


def get_skill(name: str) -> str:
    if name not in _skill_names():
        raise ValueError(f"unknown skill {name!r}; bundled: {', '.join(_skill_names())}")
    return (data_root() / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- tool contract

def list_tools() -> list[dict[str, Any]]:
    """The hosted research MCP tool contract (offline copy): names, descriptions, input schemas."""
    return load_tools()["tools"]


def tool_schema(name: str) -> dict[str, Any]:
    t = next((x for x in load_tools()["tools"] if x["name"] == name), None)
    if t is None:
        raise ValueError(f"unknown tool {name}; known: {', '.join(x['name'] for x in list_tools())}")
    return t["inputSchema"]


def validate_arguments(tool: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    """Check a tool's arguments against its bundled input schema. Returns a list of issues (empty = ok).

    This validates the *request shape* only — it does not evaluate the strategy or check data
    availability; the engine does that and returns its own errors.
    """
    schema = tool_schema(tool)
    validator = jsonschema.Draft202012Validator(schema)
    issues = []
    for err in sorted(validator.iter_errors(arguments or {}), key=lambda e: list(e.absolute_path)):
        issues.append({"path": "/" + "/".join(str(p) for p in err.absolute_path), "message": err.message})
    return issues