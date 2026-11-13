"""Runtime client against a mocked transport — no network is touched."""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from easyquant_research.client import Client, LoginRequired, ResearchError


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        if isinstance(self._payload, (dict, list)):
            return json.dumps(self._payload).encode("utf-8")
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install(monkeypatch, responses):
    """Script urlopen with a queue of JSON-RPC bodies (dict) or exceptions to raise."""
    sent = []
    queue = iter(responses)

    def fake_urlopen(req, timeout=None, context=None):
        sent.append(req)
        item = next(queue)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return sent


def rpc(result):
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def http_error(code, body):
    return urllib.error.HTTPError("https://x/mcp", code, "err", {}, io.BytesIO(json.dumps(body).encode()))


def test_call_returns_structured_content(monkeypatch):
    install(monkeypatch, [rpc({"structuredContent": {"hit_count": 3}})])
    assert Client(api_key="eqk_test").call("catalog", {}) == {"hit_count": 3}


def test_call_parses_text_fallback(monkeypatch):
    install(monkeypatch, [rpc({"content": [{"type": "text", "text": '{"a": 1}'}]})])
    assert Client().call("catalog", {}) == {"a": 1}


def test_call_is_error_raises(monkeypatch):
    install(monkeypatch, [rpc({"isError": True, "content": [{"type": "text", "text": "nope"}]})])
    with pytest.raises(ResearchError) as ei:
        Client().call("catalog", {})
    assert ei.value.code == "TOOL_ERROR"


def test_local_validation_blocks_before_network(monkeypatch):
    sent = install(monkeypatch, [])  # any real call would StopIteration
    with pytest.raises(ResearchError) as ei:
        Client().call("screen", {"not_a_field": 1})
    assert ei.value.code == "INVALID_ARGUMENTS"
    assert sent == []  # never reached the transport


def test_401_raises_login_required_with_hint(monkeypatch):
    install(monkeypatch, [http_error(401, {"code": "MCP_LOGIN_REQUIRED", "message": "login"})])
    with pytest.raises(LoginRequired) as ei:
        Client().call("catalog", {})
    assert ei.value.status == 401
    assert "screen" in str(ei.value)  # hint lists trial tools


def test_http_500_raises_research_error(monkeypatch):
    install(monkeypatch, [http_error(500, {"message": "boom"})])
    with pytest.raises(ResearchError) as ei:
        Client().call("catalog", {})
    assert ei.value.status == 500


def test_network_error(monkeypatch):
    install(monkeypatch, [urllib.error.URLError("dns failure")])
    with pytest.raises(ResearchError) as ei:
        Client().call("catalog", {})
    assert ei.value.code == "NETWORK"


def test_jsonrpc_error(monkeypatch):
    install(monkeypatch, [{"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "bad params"}}])
    with pytest.raises(ResearchError) as ei:
        Client().call("catalog", {})
    assert ei.value.code == "-32602"


def test_bearer_and_endpoint(monkeypatch):
    sent = install(monkeypatch, [rpc({"structuredContent": {}})])
    Client(api_key="eqk_secret", lang="en").call("catalog", {})
    req = sent[0]
    assert req.get_header("Authorization") == "Bearer eqk_secret"
    assert req.full_url.endswith("/api/agent/v1/mcp")
    assert req.get_header("Accept-language") == "en"


def test_anonymous_has_no_auth_header(monkeypatch):
    sent = install(monkeypatch, [rpc({"structuredContent": {}})])
    Client().call("catalog", {})
    assert sent[0].get_header("Authorization") is None


def test_list_tools(monkeypatch):
    install(monkeypatch, [rpc({"tools": [{"name": "catalog"}, {"name": "screen"}]})])
    assert [t["name"] for t in Client().list_tools()] == ["catalog", "screen"]


def test_wait_job_polls_then_succeeds(monkeypatch):
    monkeypatch.setattr("easyquant_research.client.time.sleep", lambda *_: None)
    install(monkeypatch, [
        rpc({"structuredContent": {"status": "RUNNING", "retry_after_seconds": 0}}),
        rpc({"structuredContent": {"status": "SUCCEEDED", "result": {"sharpe": 1.2}}}),
    ])
    assert Client().wait_job("j1") == {"sharpe": 1.2}


def test_wait_job_failed(monkeypatch):
    monkeypatch.setattr("easyquant_research.client.time.sleep", lambda *_: None)
    install(monkeypatch, [rpc({"structuredContent": {"status": "FAILED", "error": "data missing"}})])
    with pytest.raises(ResearchError) as ei:
        Client().wait_job("j1")
    assert ei.value.code == "JOB_FAILED"


def test_bad_lang_rejected():
    with pytest.raises(ValueError):
        Client(lang="fr")