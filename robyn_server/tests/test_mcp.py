"""Tests for MCP Protocol endpoints.

Tests the JSON-RPC 2.0 based MCP (Model Context Protocol) implementation.
"""

import pytest

from robyn_server.mcp import (
    JsonRpcErrorCode,
    JsonRpcRequest,
    McpCapabilities,
    McpInitializeParams,
    McpInitializeResult,
    McpServerInfo,
    McpTool,
    McpToolCallContentItem,
    McpToolCallParams,
    McpToolCallResult,
    McpToolInputSchema,
    McpToolsListResult,
    create_error_response,
    create_success_response,
    mcp_handler,
)


# ============================================================================
# Schema Tests
# ============================================================================


class TestJsonRpcSchemas:
    """Tests for JSON-RPC 2.0 schema models."""

    def test_json_rpc_request_minimal(self):
        """Test minimal JSON-RPC request."""
        request = JsonRpcRequest(method="ping")
        assert request.jsonrpc == "2.0"
        assert request.method == "ping"
        assert request.id is None
        assert request.params is None

    def test_json_rpc_request_full(self):
        """Test full JSON-RPC request with all fields."""
        request = JsonRpcRequest(
            jsonrpc="2.0",
            id="123",
            method="tools/call",
            params={"name": "test", "arguments": {}},
        )
        assert request.jsonrpc == "2.0"
        assert request.id == "123"
        assert request.method == "tools/call"
        assert request.params == {"name": "test", "arguments": {}}

    def test_json_rpc_request_integer_id(self):
        """Test JSON-RPC request with integer ID."""
        request = JsonRpcRequest(id=42, method="test")
        assert request.id == 42

    def test_json_rpc_response_success(self):
        """Test successful JSON-RPC response."""
        response = create_success_response("1", {"status": "ok"})
        assert response.jsonrpc == "2.0"
        assert response.id == "1"
        assert response.result == {"status": "ok"}
        assert response.error is None

    def test_json_rpc_response_error(self):
        """Test error JSON-RPC response."""
        response = create_error_response("1", -32600, "Invalid Request")
        assert response.jsonrpc == "2.0"
        assert response.id == "1"
        assert response.result is None
        assert response.error is not None
        assert response.error.code == -32600
        assert response.error.message == "Invalid Request"

    def test_json_rpc_response_model_dump_success(self):
        """Test model_dump excludes error for success response."""
        response = create_success_response("1", {"data": "test"})
        dumped = response.model_dump()
        assert "result" in dumped
        assert "error" not in dumped
        assert dumped["result"] == {"data": "test"}

    def test_json_rpc_response_model_dump_error(self):
        """Test model_dump excludes result for error response."""
        response = create_error_response("1", -32600, "Invalid")
        dumped = response.model_dump()
        assert "error" in dumped
        assert dumped.get("result") is None or "result" not in dumped


class TestMcpSchemas:
    """Tests for MCP-specific schema models."""

    def test_mcp_initialize_params(self):
        """Test MCP initialize parameters parsing."""
        params = McpInitializeParams.model_validate(
            {
                "clientInfo": {"name": "test_client", "version": "1.0.0"},
                "protocolVersion": "2024-11-05",
                "capabilities": {},
            }
        )
        assert params.client_info.name == "test_client"
        assert params.client_info.version == "1.0.0"
        assert params.protocol_version == "2024-11-05"

    def test_mcp_initialize_result(self):
        """Test MCP initialize result."""
        result = McpInitializeResult(
            protocol_version="2024-11-05",
            server_info=McpServerInfo(name="test", version="0.1.0"),
            capabilities=McpCapabilities(tools={}),
        )
        dumped = result.model_dump(by_alias=True)
        assert dumped["protocolVersion"] == "2024-11-05"
        assert dumped["serverInfo"]["name"] == "test"
        assert "tools" in dumped["capabilities"]

    def test_mcp_tool(self):
        """Test MCP tool definition."""
        tool = McpTool(
            name="test_tool",
            description="A test tool",
            input_schema=McpToolInputSchema(
                type="object",
                properties={"arg1": {"type": "string"}},
                required=["arg1"],
            ),
        )
        dumped = tool.model_dump(by_alias=True)
        assert dumped["name"] == "test_tool"
        assert dumped["inputSchema"]["type"] == "object"
        assert "arg1" in dumped["inputSchema"]["properties"]

    def test_mcp_tools_list_result(self):
        """Test tools list result."""
        result = McpToolsListResult(
            tools=[
                McpTool(
                    name="tool1",
                    description="Tool 1",
                    input_schema=McpToolInputSchema(),
                )
            ]
        )
        assert len(result.tools) == 1
        assert result.tools[0].name == "tool1"

    def test_mcp_tool_call_params(self):
        """Test tool call parameters."""
        params = McpToolCallParams(
            name="langgraph_agent", arguments={"message": "Hello"}
        )
        assert params.name == "langgraph_agent"
        assert params.arguments["message"] == "Hello"

    def test_mcp_tool_call_result_success(self):
        """Test successful tool call result."""
        result = McpToolCallResult(
            content=[McpToolCallContentItem(type="text", text="Response")],
            is_error=False,
        )
        dumped = result.model_dump(by_alias=True)
        assert dumped["isError"] is False
        assert len(dumped["content"]) == 1
        assert dumped["content"][0]["text"] == "Response"

    def test_mcp_tool_call_result_error(self):
        """Test error tool call result."""
        result = McpToolCallResult(
            content=[
                McpToolCallContentItem(type="text", text="Error: something failed")
            ],
            is_error=True,
        )
        dumped = result.model_dump(by_alias=True)
        assert dumped["isError"] is True


# ============================================================================
# Handler Tests
# ============================================================================


class TestMcpHandler:
    """Tests for MCP method handler."""

    @pytest.mark.asyncio
    async def test_handle_ping(self):
        """Test ping method."""
        request = JsonRpcRequest(id="1", method="ping")
        response = await mcp_handler.handle_request(request)
        assert response.error is None
        assert response.result == {}

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """Test initialize method."""
        request = JsonRpcRequest(
            id="1",
            method="initialize",
            params={
                "clientInfo": {"name": "test", "version": "1.0"},
                "protocolVersion": "2024-11-05",
            },
        )
        response = await mcp_handler.handle_request(request)
        assert response.error is None
        assert "protocolVersion" in response.result
        assert "serverInfo" in response.result
        assert "capabilities" in response.result

    @pytest.mark.asyncio
    async def test_handle_initialized(self):
        """Test initialized notification."""
        request = JsonRpcRequest(method="initialized", params={})
        response = await mcp_handler.handle_request(request)
        assert response.error is None
        assert response.result == {}

    @pytest.mark.asyncio
    async def test_handle_tools_list(self):
        """Test tools/list method."""
        request = JsonRpcRequest(id="1", method="tools/list")
        response = await mcp_handler.handle_request(request)
        assert response.error is None
        assert "tools" in response.result
        assert len(response.result["tools"]) > 0
        # Check the langgraph_agent tool exists
        tool_names = [t["name"] for t in response.result["tools"]]
        assert "langgraph_agent" in tool_names

    @pytest.mark.asyncio
    async def test_handle_tools_call_missing_message(self):
        """Test tools/call with missing required argument."""
        request = JsonRpcRequest(
            id="1",
            method="tools/call",
            params={"name": "langgraph_agent", "arguments": {}},
        )
        response = await mcp_handler.handle_request(request)
        assert response.error is not None
        assert response.error.code == JsonRpcErrorCode.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_handle_tools_call_unknown_tool(self):
        """Test tools/call with unknown tool name."""
        request = JsonRpcRequest(
            id="1",
            method="tools/call",
            params={"name": "unknown_tool", "arguments": {"message": "test"}},
        )
        response = await mcp_handler.handle_request(request)
        assert response.error is not None
        assert response.error.code == JsonRpcErrorCode.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_handle_tools_call_langgraph_agent(self):
        """Test tools/call with langgraph_agent tool."""
        request = JsonRpcRequest(
            id="1",
            method="tools/call",
            params={
                "name": "langgraph_agent",
                "arguments": {"message": "Hello, agent!"},
            },
        )
        response = await mcp_handler.handle_request(request)
        # The agent execution might fail (no agent configured), but we should
        # still get a valid MCP response structure
        assert response.id == "1"
        if response.error is None:
            assert "content" in response.result
            assert "isError" in response.result

    @pytest.mark.asyncio
    async def test_handle_prompts_list(self):
        """Test prompts/list method (returns empty)."""
        request = JsonRpcRequest(id="1", method="prompts/list")
        response = await mcp_handler.handle_request(request)
        assert response.error is None
        assert response.result == {"prompts": []}

    @pytest.mark.asyncio
    async def test_handle_resources_list(self):
        """Test resources/list method (returns empty)."""
        request = JsonRpcRequest(id="1", method="resources/list")
        response = await mcp_handler.handle_request(request)
        assert response.error is None
        assert response.result == {"resources": []}

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self):
        """Test unknown method returns method not found error."""
        request = JsonRpcRequest(id="1", method="unknown/method")
        response = await mcp_handler.handle_request(request)
        assert response.error is not None
        assert response.error.code == JsonRpcErrorCode.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_handle_notification_no_id(self):
        """Test that notifications (no id) still work."""
        request = JsonRpcRequest(method="ping")  # No id = notification
        response = await mcp_handler.handle_request(request)
        assert response.id is None
        assert response.error is None


# ============================================================================
# Integration Tests (Route-level)
# ============================================================================


class TestMcpRoutes:
    """Integration tests for MCP HTTP routes.

    These tests require a running test client.
    """

    @pytest.fixture
    def mcp_request_body(self):
        """Create a valid MCP request body."""
        return {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "pytest", "version": "1.0.0"},
                "protocolVersion": "2024-11-05",
                "capabilities": {},
            },
        }

    def test_mcp_request_body_structure(self, mcp_request_body):
        """Test that fixture creates valid request body."""
        assert mcp_request_body["jsonrpc"] == "2.0"
        assert mcp_request_body["method"] == "initialize"

    def test_json_rpc_request_from_dict(self, mcp_request_body):
        """Test parsing request body into JsonRpcRequest."""
        request = JsonRpcRequest.model_validate(mcp_request_body)
        assert request.jsonrpc == "2.0"
        assert request.id == "test-1"
        assert request.method == "initialize"


# ============================================================================
# Error Code Tests
# ============================================================================


class TestJsonRpcErrorCodes:
    """Tests for JSON-RPC error codes."""

    def test_error_codes_values(self):
        """Test that error codes have correct values."""
        assert JsonRpcErrorCode.PARSE_ERROR == -32700
        assert JsonRpcErrorCode.INVALID_REQUEST == -32600
        assert JsonRpcErrorCode.METHOD_NOT_FOUND == -32601
        assert JsonRpcErrorCode.INVALID_PARAMS == -32602
        assert JsonRpcErrorCode.INTERNAL_ERROR == -32603

    def test_create_parse_error(self):
        """Test creating a parse error response."""
        response = create_error_response(
            None, JsonRpcErrorCode.PARSE_ERROR, "Invalid JSON"
        )
        assert response.error.code == -32700

    def test_create_method_not_found_error(self):
        """Test creating a method not found error."""
        response = create_error_response(
            "1", JsonRpcErrorCode.METHOD_NOT_FOUND, "Method not found: foo"
        )
        assert response.error.code == -32601
        assert "foo" in response.error.message
