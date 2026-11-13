"""Locate the bundled reference data (catalog, examples, docs, skills).

Installed wheels carry them under easyquant_research/_data; a source checkout reads them from
the repository root, so there is exactly one copy to edit.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

_PKG_DATA = Path(__file__).resolve().parent / "_data"
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _root() -> Path:
    if (_PKG_DATA / "catalog").is_dir():
        return _PKG_DATA
    if (_REPO_ROOT / "catalog").is_dir():
        return _REPO_ROOT
    raise FileNotFoundError("easyquant-research data files not found; reinstall the package")


def data_root() -> Path:
    """Directory holding catalog/, examples/, docs/ and skills/ (installed copy or checkout)."""
    return _root()


@lru_cache(maxsize=None)
def load_json(rel: str) -> Any:
    return json.loads((_root() / rel).read_text(encoding="utf-8"))


def load_fields() -> dict[str, Any]:
    return load_json("catalog/fields.json")


def load_functions() -> dict[str, Any]:
    return load_json("catalog/functions.json")


def load_indicators() -> dict[str, Any]:
    return load_json("catalog/indicators.json")


def load_rule_nodes() -> dict[str, Any]:
    return load_json("catalog/rule-nodes.json")


def load_markets() -> dict[str, Any]:
    return load_json("catalog/markets.json")


def load_tools() -> dict[str, Any]:
    """The hosted research MCP tool contract (names, descriptions, input schemas)."""
    return load_json("catalog/tools.json")


def default_lang() -> str:
    """Language for runtime messages: $EASYQUANT_LANG, else zh on a Chinese locale, else en."""
    lang = os.environ.get("EASYQUANT_LANG") or ""
    if lang in ("zh", "en"):
        return lang
    loc = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    return "zh" if loc.lower().startswith("zh") else "en"