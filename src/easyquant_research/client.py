"""Client for the hosted EasyQuant research MCP endpoint (POST /api/agent/v1/mcp).

Standard library only (certifi is an optional CA fallback). The endpoint speaks JSON-RPC 2.0
over a stateless request/response subset of Streamable HTTP: one POST per tool call, no SSE
stream and no session id. Slow tools return a job_id you poll with get_job.

Configure with arguments or environment variables:

    EASYQUANT_BASE_URL   default https://trade.goeasyquant.com
    EASYQUANT_API_KEY    eqk_... (created in the runtime's account page). Optional: without it
                         the endpoint serves a limited anonymous trial; logging in (OAuth or an
                         API key) unlocks every tool and a higher quota.

The key can run historical research only. It cannot place orders, touch fund accounts, create
or enable trading strategies, or manage keys; that boundary is enforced by the runtime.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from ._resources import default_lang, load_tools
from .reference import validate_arguments

DEFAULT_BASE_URL = "https://trade.goeasyquant.com"
MCP_PATH = "/api/agent/v1/mcp"
PROTOCOL_VERSION = "2025-06-18"


def _ssl_context() -> ssl.SSLContext:
    """System trust store, or certifi's bundle when the system store is empty.

    Python from the python.org macOS installer ships without CA certificates, so every HTTPS
    call fails with CERTIFICATE_VERIFY_FAILED until "Install Certificates.command" is run. A
    system store that loaded any certificate is kept as is; SSL_CERT_FILE / SSL_CERT_DIR win.
    """
    ctx = ssl.create_default_context()
    if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
        return ctx
    if ctx.cert_store_stats().get("x509_ca", 0) == 0:
        try:
            import certifi
            ctx.load_verify_locations(cafile=certifi.where())
        except ImportError:
            pass
    return ctx


class ResearchError(Exception):
    """A non-success response from the runtime (HTTP error, JSON-RPC error, or tool isError)."""

    def __init__(self, message: str, status: int | None = None, code: str | None = None,
                 body: Any = None):
        self.status = status
        self.code = code
        self.body = body
        super().__init__(message)


class LoginRequired(ResearchError):
    """The endpoint asked for authentication (anonymous trial exhausted or tool requires login)."""


class Client:
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 timeout: float = 120.0, lang: str | None = None):
        self.base_url = (base_url or os.environ.get("EASYQUANT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or os.environ.get("EASYQUANT_API_KEY") or None
        self.timeout = timeout
        if lang is not None and lang not in ("en", "zh"):
            raise ValueError("lang must be 'en' or 'zh'")
        self.lang = lang or default_lang()
        self._id = 0

    # ------------------------------------------------------------------ calls

    def initialize(self) -> dict[str, Any]:
        return self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "easyquant-research", "title": "EasyQuant Research connector"},
        })

    def list_tools(self) -> list[dict[str, Any]]:
        """Tools the runtime actually exposes right now (trial mode hides login-only tools)."""
        return self._rpc("tools/list").get("tools", [])

    def call(self, name: str, arguments: dict[str, Any] | None = None,
             validate_locally: bool = True) -> dict[str, Any]:
        """Call a research tool and return its structured result.

        Validates the argument shape locally first (same schema the runtime advertises) so
        obvious mistakes never cost a round trip or quota. Raises ResearchError on a tool error.
        """
        arguments = arguments or {}
        if validate_locally:
            issues = validate_arguments(name, arguments)
            if issues:
                raise ResearchError("invalid arguments for " + name + ": "
                                    + "; ".join(f"{i['path']}: {i['message']}" for i in issues), code="INVALID_ARGUMENTS")
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise ResearchError(_text(result) or f"tool {name} failed", code="TOOL_ERROR", body=result)
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        text = _text(result)
        try:
            return json.loads(text) if text else {}
        except json.JSONDecodeError:
            return {"text": text}

    def wait_job(self, job_id: str, timeout: float = 900.0, interval: float = 5.0) -> dict[str, Any]:
        """Poll get_job until the job finishes. Returns the SUCCEEDED result document."""
        deadline = time.monotonic() + timeout
        while True:
            job = self.call("get_job", {"job_id": job_id})
            status = str(job.get("status", "")).upper()
            if status in ("SUCCEEDED", "DONE"):
                return job.get("result", job)
            if status == "FAILED":
                raise ResearchError(f"job {job_id} failed: {job.get('error')}", code="JOB_FAILED", body=job)
            if time.monotonic() > deadline:
                raise TimeoutError(f"job {job_id} still {status or 'running'} after {timeout}s")
            wait = job.get("retry_after_seconds")
            time.sleep(float(wait) if isinstance(wait, (int, float)) and wait > 0 else interval)

    # ------------------------------------------------------------------ http

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "en" if self.lang == "en" else "zh-CN",
            "User-Agent": "easyquant-research-python",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.base_url + MCP_PATH, data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=_ssl_context()) as resp:
                body = _decode(resp.read())
        except urllib.error.HTTPError as e:
            body = _decode(e.read())
            code = body.get("code") if isinstance(body, dict) else None
            message = (body.get("message") if isinstance(body, dict) else None) or f"HTTP {e.code}"
            if e.code == 401:
                raise LoginRequired(
                    f"{message} (hint: set EASYQUANT_API_KEY to an eqk_ key from the runtime's account "
                    f"page, or log in via OAuth; anonymous trial covers only "
                    f"{', '.join(load_tools()['trialTools'])})",
                    status=401, code=code or "MCP_LOGIN_REQUIRED", body=body) from None
            raise ResearchError(message, status=e.code, code=code, body=body) from None
        except urllib.error.URLError as e:
            raise ResearchError(f"cannot reach runtime: {e.reason}", code="NETWORK") from None
        if not isinstance(body, dict):
            raise ResearchError(f"unexpected response: {body!r}", code="BAD_RESPONSE")
        if "error" in body:
            err = body["error"] or {}
            raise ResearchError(err.get("message", "JSON-RPC error"), code=str(err.get("code")), body=body)
        return body.get("result") or {}


def _text(result: dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list) and content and isinstance(content[0], dict):
        return str(content[0].get("text", ""))
    return ""


def _decode(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw.decode("utf-8", errors="replace")