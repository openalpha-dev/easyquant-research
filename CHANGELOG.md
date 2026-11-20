# Changelog

## 0.1.1 — 2026-11-20

- MCP server: declare tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`,
  `openWorldHint`) on all 26 tools. Offline reference is closed-world read-only; runtime research is
  open-world read-only; `submit_artifact` / `evaluate_artifact` are additive (non-destructive,
  non-idempotent). No tool is destructive and there is no order tool. Meets the MCP annotation spec
  and directory requirements (e.g. OpenAI's all-four-hints rule).
- README: add the M8ven trust badge (English + 中文).

## 0.1.0 — 2026-11-13

First open-source release of the EasyQuant research client. The engine and data stay hosted; this
package ships the offline reference, the MCP bridge and the installable Agent Skills. Research only —
no order placement, no fund-account access, no strategy creation/enablement, no API-key management.

- Offline reference catalog exported from the engine: `catalog/fields.json` (per-market fields with
  units and pitfalls), `catalog/functions.json` (expression functions), `catalog/indicators.json`
  (132 daily-usable timing-DSL indicator types with parameters, defaults and pitfalls),
  `catalog/rule-nodes.json` (timing rule tree), `catalog/markets.json` (capability trading rules;
  numeric costs marked live), `catalog/tools.json` (the hosted MCP tool contract).
- `tools/export_indicator_catalog.py` regenerates the indicator catalog from the engine's
  single-source indicator metadata, applying the daily-usable filter (skip non-null `dataLevel`,
  `enabled == false`, `consumerVisibility == B_ONLY`, `requiresTickDrive == true`).
- Pure offline reference queries (`reference.py`): `search_fields`, `search_functions`,
  `search_indicators`, `get_indicator`, `get_rule_nodes`, `list_markets`, `get_market`,
  `list_examples`, `get_example`, `list_docs`, `get_doc`, `list_skills`, `get_skill`, `list_tools`,
  `tool_schema`, `validate_arguments` (request-shape check against the bundled JSON Schema).
- Runtime client (`client.py`, standard library + certifi): JSON-RPC 2.0 over the stateless
  request/response subset of Streamable HTTP at `POST {base}/api/agent/v1/mcp`. Bearer API key or
  anonymous trial; `LoginRequired` on 401 with a trial-tool hint; `ResearchError` carries status,
  code and body; `wait_job` polls `get_job` by `retry_after_seconds`. Local schema validation before
  each call; prefers `structuredContent`.
- CLI `easyquant-research`: offline (`fields`, `functions`, `indicators`, `markets`, `rules`,
  `examples`, `docs`, `skill`, `tools`, `validate`) and runtime (`catalog`, `screen`, `factor`,
  `portfolio`, `timing`, `robustness`, `call`, `job`, `capabilities`, `submit`, `evaluate`,
  `evaluation`, `evidence`). `--wait` polls jobs; exit codes 0 ok / 1 tool error / 2 usage / 3 network.
- MCP server `easyquant-research-mcp` (extra `easyquant-research[mcp]`, stdio): 14 offline reference
  tools + 12 runtime bridge tools. No order tool.
- Agent Skills `easyquant-research` (research workflow) and `easyquant-expression` (fields, units,
  functions, pitfalls); `easyquant-research skill --install DIR` installs them, no checkout needed.
- Six reference docs (`docs/`): expression, timing DSL, markets, workflow, boundaries, runtime MCP.
- Seven example requests (`examples/`), each `{tool, title, arguments}`, all validated against the
  tool schemas: screen value, portfolio momentum, portfolio ETF, timing EMA cross, timing futures
  long/short, factor report, AlphaSpec artifact.
- AlphaSpec bridge: `research_capabilities` → `submit_artifact` (research draft only) →
  `evaluate_artifact` → `get_evaluation` → `get_research_evidence`. Phase 1 is A-share daily only.
- HTTPS works out of the box on Pythons with an empty trust store (python.org macOS installer): the
  client falls back to certifi's bundle; `SSL_CERT_FILE` / `SSL_CERT_DIR` still take precedence.
- Bilingual README (English + 中文), Apache-2.0, CI on Python 3.10 / 3.12.