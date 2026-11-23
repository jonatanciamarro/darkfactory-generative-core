"""Shift-Left TDD Suite: Native Google Flow Model Context Protocol (MCP) Server.

Verifies:
1. Standard MCP JSON-RPC 2.0 initialization handshake.
2. Tools registry and JSON Schema conformance (tools/list).
3. Tool execution for:
   - flow_audit_inventory
   - flow_get_pending_scenes
   - flow_generate_scene
   - flow_sync_clips
4. JSON-RPC error handling (-32601 Method Not Found, invalid arguments, etc.).
5. Stdio message loop processing.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.mcp.google_flow_server import (
    GoogleFlowMCPServer,
    handle_jsonrpc_request,
    get_mcp_tools_definitions,
)


class TestMCPProtocolHandshake:
    """Verifies MCP JSON-RPC 2.0 handshake and capability negotiation."""

    def test_initialize_handshake(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        resp = handle_jsonrpc_request(req)
        assert resp is not None
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert "result" in resp
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert result["serverInfo"]["name"] == "darkfactory-google-flow"
        assert "tools" in result["capabilities"]

    def test_initialized_notification_returns_none(self):
        req = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        resp = handle_jsonrpc_request(req)
        assert resp is None  # Notifications do not return a response in JSON-RPC

    def test_ping_request(self):
        req = {"jsonrpc": "2.0", "id": 99, "method": "ping"}
        resp = handle_jsonrpc_request(req)
        assert resp is not None
        assert resp["id"] == 99
        assert resp["result"] == {}


class TestMCPToolsList:
    """Verifies the tools definition catalog conforms to MCP specification."""

    def test_tools_definitions_catalog(self):
        tools = get_mcp_tools_definitions()
        assert isinstance(tools, list)
        tool_names = [t["name"] for t in tools]

        assert "flow_audit_inventory" in tool_names
        assert "flow_get_pending_scenes" in tool_names
        assert "flow_generate_scene" in tool_names
        assert "flow_sync_clips" in tool_names
        assert "flow_sync_studio" in tool_names

        for t in tools:
            assert "description" in t
            assert "inputSchema" in t
            schema = t["inputSchema"]
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_tools_list_jsonrpc(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        resp = handle_jsonrpc_request(req)
        assert resp is not None
        assert resp["id"] == 2
        assert "tools" in resp["result"]
        assert len(resp["result"]["tools"]) >= 4


class TestMCPToolsExecution:
    """Verifies tool calling dispatch and responses."""

    def test_call_flow_audit_inventory(self, tmp_path):
        broll_dir = tmp_path / "broll"
        broll_dir.mkdir()
        dummy_clip = broll_dir / "scene_2.mp4"
        dummy_clip.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"A" * 60000)

        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "flow_audit_inventory",
                "arguments": {
                    "search_dirs": [str(broll_dir)],
                    "total_scenes": 40,
                },
            },
        }

        resp = handle_jsonrpc_request(req)
        assert resp is not None
        assert resp["id"] == 3
        result = resp["result"]
        assert "content" in result
        text_content = result["content"][0]["text"]
        assert "AUDITORIA DE COBERTURA" in text_content or "coverage_percentage" in text_content

    def test_call_flow_get_pending_scenes(self, tmp_path):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "flow_get_pending_scenes",
                "arguments": {"total_scenes": 3},
            },
        }

        resp = handle_jsonrpc_request(req)
        assert resp is not None
        assert resp["id"] == 4
        result = resp["result"]
        text_content = result["content"][0]["text"]
        data = json.loads(text_content)
        assert "missing_shot_a_ids" in data
        assert "missing_shot_b_ids" in data

    def test_call_flow_sync_clips(self, tmp_path):
        src_dir = tmp_path / "loose_downloads"
        src_dir.mkdir()
        target_dir = tmp_path / "broll"
        target_dir.mkdir()

        clip = src_dir / "Flow_Clip_scene 9.mp4"
        clip.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"K" * 60000)

        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "flow_sync_clips",
                "arguments": {
                    "source_dir": str(src_dir),
                    "target_dir": str(target_dir),
                },
            },
        }

        resp = handle_jsonrpc_request(req)
        assert resp is not None
        result = resp["result"]
        text_content = result["content"][0]["text"]
        assert "scene_9.mp4" in text_content
        assert (target_dir / "scene_9.mp4").exists()

    def test_call_flow_generate_scene_dry_run(self, tmp_path):
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "flow_generate_scene",
                "arguments": {
                    "scene_id": 1,
                    "shot_type": "shot_a",
                    "prompt": "Test cinematic prompt",
                    "dry_run": True,
                    "output_dir": str(tmp_path),
                },
            },
        }

        resp = handle_jsonrpc_request(req)
        assert resp is not None
        result = resp["result"]
        assert "content" in result
        text_content = result["content"][0]["text"]
        data = json.loads(text_content)
        assert data["success"] is True
        assert data["scene_id"] == 1

    def test_tool_flow_sync_studio_execution(self):
        """Verifica a execução da ferramenta flow_sync_studio via JSON-RPC."""
        from src.google_flow_bot import GoogleFlowSyncSummary

        fake_summary = GoogleFlowSyncSummary(
            project_url="https://flow.google.com/project/test-123",
            total_tiles_found=5,
            downloaded_clips=[{"index": 0, "file_path": "data/broll/flow_sync_01.mp4"}],
            failed_clips=[],
            success_rate=100.0,
        )

        with patch("src.google_flow_bot.GoogleFlowBot.execute_playwright_sync", return_value=fake_summary):
            req = {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "flow_sync_studio",
                    "arguments": {"max_clips": 5, "prefer_upscale": True},
                },
            }
            resp = handle_jsonrpc_request(req)
            assert resp is not None
            result = resp["result"]
            assert "content" in result
            data = json.loads(result["content"][0]["text"])
            assert data["success"] is True
            assert data["total_tiles_found"] == 5
            assert data["downloaded_count"] == 1
            assert data["success_rate"] == 100.0


class TestMCPErrorHandling:
    """Verifies JSON-RPC 2.0 error specifications."""

    def test_method_not_found(self):
        req = {"jsonrpc": "2.0", "id": 10, "method": "unsupported_method"}
        resp = handle_jsonrpc_request(req)
        assert resp is not None
        assert "error" in resp
        assert resp["error"]["code"] == -32601
        assert "Method not found" in resp["error"]["message"]

    def test_unknown_tool_name(self):
        req = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "ghost_tool", "arguments": {}},
        }
        resp = handle_jsonrpc_request(req)
        assert resp is not None
        result = resp["result"]
        assert result.get("isError") is True
        assert "Unknown tool" in result["content"][0]["text"]

    def test_stdio_loop_io_stream(self):
        """Verifica o loop de leitura e escrita stdio da classe GoogleFlowMCPServer."""
        import io
        server = GoogleFlowMCPServer()

        input_data = (
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n"
        )
        fake_stdin = io.StringIO(input_data)
        fake_stdout = io.StringIO()

        with patch("sys.stdin", fake_stdin), patch("sys.stdout", fake_stdout):
            server.run_stdio_loop()

        output_lines = [line.strip() for line in fake_stdout.getvalue().splitlines() if line.strip()]
        assert len(output_lines) == 2

        resp_1 = json.loads(output_lines[0])
        resp_2 = json.loads(output_lines[1])
        assert resp_1["id"] == 1
        assert resp_1["result"]["serverInfo"]["name"] == "darkfactory-google-flow"
        assert resp_2["id"] == 2
        assert resp_2["result"] == {}

