import json
import os
import subprocess
import sys

from server.mcp import handle, TOOLS


def test_initialize_declares_only_read_tools():
    result = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert result["result"]["protocolVersion"] == "2025-06-18"
    assert result["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert all(tool["annotations"]["readOnlyHint"] for tool in TOOLS)


def test_unknown_method_and_invalid_tool_have_protocol_errors():
    assert handle({"jsonrpc": "2.0", "id": 2, "method": "delete_everything"})["error"]["code"] == -32601
    assert handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "approve_post"}})["error"]["code"] == -32602


def test_notifications_emit_no_response():
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tool_arguments_cannot_inject_path_or_override_token():
    for args in ({"post_id": "../me"}, {"post_id": "forest", "token": "override"}):
        response = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_post", "arguments": args}})
        assert response["error"]["code"] == -32602


def test_missing_token_is_visible_tool_error(monkeypatch):
    monkeypatch.delenv("TONGPING_TOKEN", raising=False)
    result = handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_post", "arguments": {"post_id": "forest"}}})
    assert result["result"]["isError"] is True


def test_stdio_is_newline_json_without_debug_stdout():
    messages = ["{", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})]
    result = subprocess.run([sys.executable, "-m", "server.mcp"], input="\n".join(messages) + "\n", text=True, capture_output=True, timeout=10)
    assert result.returncode == 0
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(responses) == 3
    assert responses[0]["error"]["code"] == -32700
    assert len(responses[2]["result"]["tools"]) == 4
