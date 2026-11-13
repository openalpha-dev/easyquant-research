"""Command line.

    easyquant-research fields [--market M] [--search TEXT]     data fields with units (offline)
    easyquant-research functions [--search TEXT]               expression functions (offline)
    easyquant-research indicators [--search T] [--type T]      timing DSL indicators (offline)
    easyquant-research markets [MARKET]                        markets + capability rules (offline)
    easyquant-research rules                                   timing DSL rule-tree reference (offline)
    easyquant-research examples [NAME]                         list or print example requests (offline)
    easyquant-research docs NAME                               expression|timing|markets|workflow|boundaries|runtime
    easyquant-research skill [NAME] [--install DIR]            print or install the Agent Skills
    easyquant-research tools [--live]                          tool contract (offline) or runtime tools/list
    easyquant-research validate TOOL (--args JSON | --file F)  check argument shape offline

    easyquant-research catalog                                 live catalog (fields, quota, data date)
    easyquant-research screen [--market M] [--condition C] ... one day's matching list
    easyquant-research factor (--expression E | --factor F)    factor checkup
    easyquant-research portfolio (--args JSON | --file F)      portfolio backtest
    easyquant-research timing (--args JSON | --file F)         single-symbol timing backtest
    easyquant-research call TOOL [--args JSON | --file F | --set k=v] [--wait]   generic runtime call
    easyquant-research job JOB_ID [--wait]                     poll an async job
    easyquant-research capabilities                            AlphaSpec research capabilities + quota
    easyquant-research submit FILE                             submit an AlphaSpec artifact (research draft)
    easyquant-research evaluate ARTIFACT_ID                    queue an evaluation
    easyquant-research evaluation ARTIFACT_ID [--wait]         read evaluation status/result
    easyquant-research evidence ARTIFACT_ID --run RUN_ID       frozen backtest evidence

Runtime commands read EASYQUANT_BASE_URL and EASYQUANT_API_KEY (or --base-url / --api-key).
Without a key the endpoint serves a limited anonymous trial. Research only — no orders.
Exit codes: 0 ok · 1 tool error / rejected · 2 usage · 3 runtime / network error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from . import reference as ref
from ._resources import default_lang
from .client import Client, LoginRequired, ResearchError


def _out(args: argparse.Namespace, obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _read_json_arg(args: argparse.Namespace) -> dict[str, Any]:
    """Build a tool-argument object from --args (inline JSON), --file, or --set k=v pairs."""
    if getattr(args, "args", None):
        return json.loads(args.args)
    if getattr(args, "file", None):
        return json.loads(Path(args.file).read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for pair in getattr(args, "set", None) or []:
        if "=" not in pair:
            raise ValueError(f"--set expects k=v, got {pair!r}")
        k, v = pair.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def _client(args: argparse.Namespace) -> Client:
    return Client(base_url=args.base_url, api_key=args.api_key, lang=getattr(args, "lang", None))


def _print_rows(rows: list[dict[str, Any]], cols: list[str]) -> None:
    for r in rows:
        print("  ".join(str(r.get(c, "")) for c in cols))


# ---------------------------------------------------------------- offline commands

def _cmd_fields(args: argparse.Namespace) -> int:
    rows = ref.search_fields(args.search, args.market)
    if args.json:
        _out(args, rows)
        return 0
    for r in rows:
        print(f"[{r['market']}] {r['group']}: {r['names']}")
        print(f"    {r['note']}")
    print(f"\n{len(rows)} field groups. Live units/quota: easyquant-research catalog", file=sys.stderr)
    return 0


def _cmd_functions(args: argparse.Namespace) -> int:
    rows = ref.search_functions(args.search)
    if args.json:
        _out(args, rows)
        return 0
    for r in rows:
        print(f"{r['signature']:70} {r['summary']}")
    return 0


def _cmd_indicators(args: argparse.Namespace) -> int:
    if args.type:
        _out(args, ref.get_indicator(args.type))
        return 0
    rows = ref.search_indicators(args.search, args.category)
    if args.json:
        _out(args, rows)
        return 0
    for r in rows:
        params = ", ".join(r.get("params", []))
        print(f"{r['type']:24} {r.get('category') or '':12} {params}")
        if r.get("summary"):
            print(f"    {r['summary']}")
    print(f"\n{len(rows)} indicators. Details: easyquant-research indicators --type NAME", file=sys.stderr)
    return 0


def _cmd_markets(args: argparse.Namespace) -> int:
    if args.market:
        _out(args, ref.get_market(args.market))
        return 0
    rows = ref.list_markets()
    if args.json:
        _out(args, rows)
        return 0
    for m in rows:
        print(f"{m['id']:12} {m['name']:8} {', '.join(m['supports'])}")
        print(f"    {m['note']}")
    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    _out(args, ref.get_rule_nodes())
    return 0


def _cmd_examples(args: argparse.Namespace) -> int:
    if not args.name:
        for e in ref.list_examples():
            print(f"{e['name']:32} {e['tool']:20} {e['title']}")
        return 0
    print(json.dumps(ref.get_example(args.name), ensure_ascii=False, indent=2))
    return 0


def _cmd_docs(args: argparse.Namespace) -> int:
    print(ref.get_doc(args.name), end="")
    return 0


def _cmd_skill(args: argparse.Namespace) -> int:
    names = ref.list_skills()
    if args.name and args.name not in names:
        print(f"unknown skill {args.name!r}; bundled: {', '.join(names)}", file=sys.stderr)
        return 2
    if not args.install:
        print(ref.get_skill(args.name or "easyquant-research"), end="")
        return 0
    for name in [args.name] if args.name else names:
        target = Path(args.install).expanduser() / name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(ref.get_skill(name), encoding="utf-8")
        print(f"installed {target}")
    return 0


def _cmd_tools(args: argparse.Namespace) -> int:
    if args.live:
        rows = _client(args).list_tools()
        _out(args, rows)
        return 0
    rows = ref.list_tools()
    if args.json:
        _out(args, rows)
        return 0
    for t in rows:
        lock = "login" if t.get("requiresLogin") else "trial"
        print(f"{t['name']:24} [{lock:5}] {t['title']}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    arguments = _read_json_arg(args)
    issues = ref.validate_arguments(args.tool, arguments)
    if args.json:
        _out(args, {"ok": not issues, "issues": issues})
    elif issues:
        print(f"{args.tool}: {len(issues)} issue(s)")
        for i in issues:
            print(f"  {i['path']}: {i['message']}")
    else:
        print(f"{args.tool}: ok")
    return 1 if issues else 0


# ---------------------------------------------------------------- runtime commands

def _run_tool(args: argparse.Namespace, name: str, arguments: dict[str, Any]) -> int:
    c = _client(args)
    result = c.call(name, arguments)
    if getattr(args, "wait", False) and isinstance(result, dict) and result.get("job_id"):
        if not args.json:
            print(f"job {result['job_id']} queued; polling ...", file=sys.stderr)
        result = c.wait_job(result["job_id"], timeout=args.timeout)
    _out(args, result)
    return 0


def _cmd_catalog(args: argparse.Namespace) -> int:
    return _run_tool(args, "catalog", {})


def _cmd_screen(args: argparse.Namespace) -> int:
    a = {k: v for k, v in {
        "market": args.market, "condition": args.condition, "rank_by": args.rank_by,
        "rank_order": args.rank_order, "top_n": args.top_n, "date": args.date, "limit": args.limit,
    }.items() if v not in (None, "")}
    return _run_tool(args, "screen", a)


def _cmd_factor(args: argparse.Namespace) -> int:
    a = {k: v for k, v in {"expression": args.expression, "factor": args.factor,
                           "window_years": args.window_years}.items() if v not in (None, "")}
    return _run_tool(args, "factor_report", a)


def _cmd_named(args: argparse.Namespace, name: str) -> int:
    return _run_tool(args, name, _read_json_arg(args))


def _cmd_call(args: argparse.Namespace) -> int:
    return _run_tool(args, args.tool, _read_json_arg(args))


def _cmd_job(args: argparse.Namespace) -> int:
    c = _client(args)
    if args.wait:
        _out(args, c.wait_job(args.job_id, timeout=args.timeout))
        return 0
    _out(args, c.call("get_job", {"job_id": args.job_id}))
    return 0


def _cmd_submit(args: argparse.Namespace) -> int:
    document = json.loads(Path(args.file).read_text(encoding="utf-8"))
    return _run_tool(args, "submit_artifact", {"document": document})


def _cmd_evaluation(args: argparse.Namespace) -> int:
    c = _client(args)
    result = c.call("get_evaluation", {"artifact_id": args.artifact_id})
    if args.wait:
        import time
        deadline = time.monotonic() + args.timeout
        while str(result.get("status", "")).upper() in ("QUEUED", "RUNNING"):
            if time.monotonic() > deadline:
                raise TimeoutError(f"evaluation {args.artifact_id} still running after {args.timeout}s")
            wait = result.get("retry_after_seconds")
            time.sleep(float(wait) if isinstance(wait, (int, float)) and wait > 0 else 5)
            result = c.call("get_evaluation", {"artifact_id": args.artifact_id})
    _out(args, result)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="easyquant-research",
                                     description="EasyQuant historical research: offline reference + hosted MCP bridge.")
    parser.add_argument("--version", action="version", version=f"easyquant-research {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    offline = argparse.ArgumentParser(add_help=False)
    offline.add_argument("--json", action="store_true", help="machine-readable output")

    f = sub.add_parser("fields", parents=[offline], help="data fields with units (offline)")
    f.add_argument("--market", help="cn_stock / cn_etf / us_equity / hk_stock / cn_future")
    f.add_argument("--search", help="substring match on group, names, note")
    f.set_defaults(func=_cmd_fields)

    fn = sub.add_parser("functions", parents=[offline], help="expression functions (offline)")
    fn.add_argument("--search")
    fn.set_defaults(func=_cmd_functions)

    ind = sub.add_parser("indicators", parents=[offline], help="timing DSL indicators (offline)")
    ind.add_argument("--search")
    ind.add_argument("--category")
    ind.add_argument("--type", help="full entry for one indicator type")
    ind.set_defaults(func=_cmd_indicators)

    mk = sub.add_parser("markets", parents=[offline], help="markets + capability rules (offline)")
    mk.add_argument("market", nargs="?")
    mk.set_defaults(func=_cmd_markets)

    rl = sub.add_parser("rules", parents=[offline], help="timing DSL rule-tree reference (offline)")
    rl.set_defaults(func=_cmd_rules)

    ex = sub.add_parser("examples", help="list or print example requests (offline)")
    ex.add_argument("name", nargs="?")
    ex.set_defaults(func=_cmd_examples)

    dc = sub.add_parser("docs", help="print a reference document (offline)")
    dc.add_argument("name", choices=ref.list_docs())
    dc.set_defaults(func=_cmd_docs)

    sk = sub.add_parser("skill", help="print or install the Agent Skills")
    sk.add_argument("name", nargs="?")
    sk.add_argument("--install", metavar="DIR", help="skills directory, e.g. ~/.claude/skills")
    sk.set_defaults(func=_cmd_skill)

    tl = sub.add_parser("tools", parents=[offline], help="tool contract (offline) or runtime tools/list")
    tl.add_argument("--live", action="store_true", help="list tools the runtime exposes right now")
    tl.add_argument("--base-url"); tl.add_argument("--api-key"); tl.add_argument("--lang", choices=["en", "zh"])
    tl.set_defaults(func=_cmd_tools)

    va = sub.add_parser("validate", parents=[offline], help="check a tool's argument shape (offline)")
    va.add_argument("tool")
    va.add_argument("--args", help="inline JSON arguments")
    va.add_argument("--file", help="JSON file of arguments")
    va.set_defaults(func=_cmd_validate)

    remote = argparse.ArgumentParser(add_help=False)
    remote.add_argument("--base-url", help="runtime base URL (default: $EASYQUANT_BASE_URL)")
    remote.add_argument("--api-key", help="API key (default: $EASYQUANT_API_KEY)")
    remote.add_argument("--json", action="store_true", help="machine-readable output")
    remote.add_argument("--lang", choices=["en", "zh"], default=None)
    remote.add_argument("--timeout", type=float, default=900, help="seconds to wait when polling")

    def add_json_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--args", help="inline JSON arguments object")
        p.add_argument("--file", help="JSON file holding the arguments object")
        p.add_argument("--set", action="append", metavar="K=V", help="set one argument (value parsed as JSON if possible)")

    cp = sub.add_parser("catalog", parents=[remote], help="live catalog")
    cp.set_defaults(func=_cmd_catalog)

    sc = sub.add_parser("screen", parents=[remote], help="one day's matching list")
    sc.add_argument("--market"); sc.add_argument("--condition"); sc.add_argument("--rank-by", dest="rank_by")
    sc.add_argument("--rank-order", dest="rank_order", choices=["desc", "asc"])
    sc.add_argument("--top-n", dest="top_n", type=int); sc.add_argument("--date"); sc.add_argument("--limit", type=int)
    sc.add_argument("--wait", action="store_true")
    sc.set_defaults(func=_cmd_screen)

    fc = sub.add_parser("factor", parents=[remote], help="factor checkup")
    fc.add_argument("--expression"); fc.add_argument("--factor")
    fc.add_argument("--window-years", dest="window_years", type=int, choices=[1, 3])
    fc.add_argument("--wait", action="store_true")
    fc.set_defaults(func=_cmd_factor)

    pf = sub.add_parser("portfolio", parents=[remote], help="portfolio backtest")
    add_json_args(pf); pf.add_argument("--wait", action="store_true")
    pf.set_defaults(func=lambda a: _cmd_named(a, "backtest_portfolio"))

    tm = sub.add_parser("timing", parents=[remote], help="single-symbol timing backtest")
    add_json_args(tm); tm.add_argument("--wait", action="store_true")
    tm.set_defaults(func=lambda a: _cmd_named(a, "backtest_timing"))

    rb = sub.add_parser("robustness", parents=[remote], help="robustness check (login required)")
    add_json_args(rb); rb.add_argument("--wait", action="store_true")
    rb.set_defaults(func=lambda a: _cmd_named(a, "robustness"))

    ca = sub.add_parser("call", parents=[remote], help="generic runtime tool call")
    ca.add_argument("tool"); add_json_args(ca); ca.add_argument("--wait", action="store_true")
    ca.set_defaults(func=_cmd_call)

    jb = sub.add_parser("job", parents=[remote], help="poll an async job")
    jb.add_argument("job_id"); jb.add_argument("--wait", action="store_true")
    jb.set_defaults(func=_cmd_job)

    cap = sub.add_parser("capabilities", parents=[remote], help="AlphaSpec research capabilities + quota")
    cap.set_defaults(func=lambda a: _cmd_named(a, "research_capabilities"))

    sb = sub.add_parser("submit", parents=[remote], help="submit an AlphaSpec artifact (research draft)")
    sb.add_argument("file")
    sb.set_defaults(func=_cmd_submit)

    ev = sub.add_parser("evaluate", parents=[remote], help="queue an evaluation")
    ev.add_argument("artifact_id", type=int)
    ev.set_defaults(func=lambda a: _run_tool(a, "evaluate_artifact", {"artifact_id": a.artifact_id}))

    evr = sub.add_parser("evaluation", parents=[remote], help="read evaluation status/result")
    evr.add_argument("artifact_id", type=int); evr.add_argument("--wait", action="store_true")
    evr.set_defaults(func=_cmd_evaluation)

    ed = sub.add_parser("evidence", parents=[remote], help="frozen backtest evidence")
    ed.add_argument("artifact_id", type=int); ed.add_argument("--run", type=int, required=True, dest="run_id")
    ed.set_defaults(func=lambda a: _run_tool(a, "get_research_evidence", {"artifact_id": a.artifact_id, "run_id": a.run_id}))

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except LoginRequired as exc:
        print(f"login required: {exc}", file=sys.stderr)
        return 1
    except ResearchError as exc:
        print(f"tool error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, TimeoutError) as exc:
        print(f"runtime error: {exc}", file=sys.stderr)
        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
            print(_CERT_HINT, file=sys.stderr)
        return 3


_CERT_HINT = (
    "hint: this Python has no CA certificates. On macOS with the python.org installer run\n"
    "      \"/Applications/Python 3.x/Install Certificates.command\", or:\n"
    "      pip install certifi && export SSL_CERT_FILE=$(python3 -m certifi)"
)


if __name__ == "__main__":
    sys.exit(main())