#!/usr/bin/env python3
"""Export the daily-usable timing DSL indicators from the EasyQuant engine metadata.

Single source of truth: easyquant-app/src/main/resources/dsl/indicator-metadata.json.
The filter mirrors ResearchTools.indicatorCatalog() exactly: drop intraday / L2 levels
(any non-null dataLevel), disabled types, B_ONLY visibility, and tick-driven types.

    python tools/export_indicator_catalog.py /path/to/indicator-metadata.json

Writes catalog/indicators.json. Re-run after the engine adds or changes indicators.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (REPO_ROOT.parent / "EasyQuant" / "backend" / "easyquant-backend"
                  / "easyquant-app" / "src" / "main" / "resources" / "dsl" / "indicator-metadata.json")


def daily_usable(t: dict) -> bool:
    if t.get("dataLevel") is not None:
        return False
    if t.get("enabled", True) is False:
        return False
    if t.get("consumerVisibility") == "B_ONLY":
        return False
    if t.get("requiresTickDrive", False):
        return False
    return True


def export(source: Path) -> dict:
    root = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    for t in root.get("types", []):
        if not daily_usable(t):
            continue
        params = []
        for p in t.get("params", []):
            row = {"key": p.get("key")}
            if "default" in p and p["default"] is not None:
                row["default"] = p["default"]
            if p.get("kind"):
                row["kind"] = p["kind"]
            if p.get("description"):
                row["description"] = p["description"]
            params.append(row)
        tutorial = t.get("tutorial") or {}
        rows.append({
            "type": t.get("type"),
            "name": t.get("labelZh"),
            "category": t.get("category"),
            "params": params,
            "compact": [p["key"] + ("=" + str(p["default"]) if "default" in p else "") for p in params],
            "summary": tutorial.get("summary"),
            "pitfalls": tutorial.get("pitfalls") or [],
        })
    return {
        "source": "dsl/indicator-metadata.json (EasyQuant engine)",
        "filter": "daily-usable: no dataLevel, enabled, not B_ONLY, not requiresTickDrive",
        "how": "indicators 是「名字 → {type, 参数...}」；规则里用 {\"ind\": \"名字\"} 引用。type 与参数键以本目录为准，不要臆造。",
        "count": len(rows),
        "types": rows,
    }


def main(argv: list[str]) -> int:
    source = Path(argv[1]) if len(argv) > 1 else DEFAULT_SOURCE
    if not source.is_file():
        print(f"indicator metadata not found: {source}\n"
              f"usage: python tools/export_indicator_catalog.py /path/to/indicator-metadata.json", file=sys.stderr)
        return 2
    out = export(source)
    target = REPO_ROOT / "catalog" / "indicators.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target} ({out['count']} daily-usable indicators)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))