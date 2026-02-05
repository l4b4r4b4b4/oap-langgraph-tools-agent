"""MCP Protocol method handlers.

Implements the JSON-RPC 2.0 method handlers for MCP protocol.
"""

import json
import logging
from typing import Any

from robyn_server.mcp.schemas import (
    JsonRpcErrorCode,
    JsonRpcRequest,
    JsonRpcResponse,
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
)

logger = logging.getLogger(__name__)

# MCP Protocol version we support
PROTOCOL_VERSION = "2024-11-05"

# Server information
SERVER_INFO = McpServerInfo(
    name="oap-langgraph-agent",
    version="0.1.0",
)

# The LangGraph agent exposed as an MCP tool
LANGGRAPH_AGENT_TOOL = McpTool(
    name="langgraph_agent",
    description="Execute the LangGraph agent with a message. The agent can use various tools to help answer questions and perform tasks.",
    input_schema=McpToolInputSchema(
        type="object",
        properties={
            "message": {
                "type": "string",
                "description": "The user message to send to the agent",
            },
            "thread_id": {
                "type": "string",
                "description": "Optional thread ID for conversation continuity. If not provided, a new thread will be created.",
            },
            "assistant_id": {
                "type": "string",
                "description": "Optional assistant ID to use. Defaults to 'agent'.",
            },
        },
        required=["message"],
    ),
)


class McpMethodHandler:
    """Handler for MCP JSON-RPC methods."""

    def __init__(self) -> None:
        """Initialize the method handler."""
        self._initialized = False
        self._client_info: dict[str, Any] | None = None

    async def handle_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Route a JSON-RPC request to the appropriate handler.

        Args:
            request: The JSON-RPC request to handle.

        Returns:
            JSON-RPC response with result or error.
        """
        method = request.method
        params = request.params or {}

        logger.debug(f"MCP request: method={method}, id={request.id}")

        # Route to appropriate handler
        handler_map = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "prompts/list": self._handle_prompts_list,
            "resources/list": self._handle_resources_list,
            "ping": self._handle_ping,
        }

        handler = handler_map.get(method)
        if handler is None:
            logger.warning(f"MCP method not found: {method}")
            return create_error_response(
                request.id,
                JsonRpcErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {method}",
            )

        try:
            result = await handler(params)
            return create_success_response(request.id, result)
        except ValueError as e:
            logger.error(f"MCP invalid params: {e}")
            return create_error_response(
                request.id,
                JsonRpcErrorCode.INVALID_PARAMS,
                str(e),
            )
        except Exception as e:
            logger.exception(f"MCP internal error: {e}")
            return create_error_response(
                request.id,
                JsonRpcErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}",
            )

    async def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the initialize method.

        This is the handshake between client and server.

        Args:
            params: Initialize parameters including clientInfo and protocolVersion.

        Returns:
            Server capabilities and info.
        """
        try:
            init_params = McpInitializeParams.model_validate(params)
            self._client_info = {
                "name": init_params.client_info.name,
                "version": init_params.client_info.version,
            }
            logger.info(
                f"MCP client connected: {init_params.client_info.name} "
                f"v{init_params.client_info.version}"
            )
        except Exception as e:
            logger.warning(f"Failed to parse initialize params: {e}")
            # Continue anyway with defaults

        # Return server capabilities
        result = McpInitializeResult(
            protocol_version=PROTOCOL_VERSION,
            server_info=SERVER_INFO,
            capabilities=McpCapabilities(
                tools={},  # We support tools
            ),
        )

        return result.model_dump(by_alias=True)

    async def _handle_initialized(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the initialized notification.

        This is sent by the client after receiving initialize response.
        It's a notification (no response needed), but we return empty dict.

        Args:
            params: Empty or ignored.

        Returns:
            Empty dict (this is a notification).
        """
        self._initialized = True
        logger.info("MCP client initialization complete")
        return {}

    async def _handle_tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the tools/list method.

        Returns the list of tools available on this server.

        Args:
            params: Optional cursor for pagination (not implemented).

        Returns:
            List of available tools.
        """
        result = McpToolsListResult(tools=[LANGGRAPH_AGENT_TOOL])
        return result.model_dump(by_alias=True)

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the tools/call method.

        Executes a tool with the given arguments.

        Args:
            params: Tool name and arguments.

        Returns:
            Tool execution result.
        """
        try:
            call_params = McpToolCallParams.model_validate(params)
        except Exception as e:
            raise ValueError(f"Invalid tool call params: {e}") from e

        if call_params.name != "langgraph_agent":
            raise ValueError(f"Unknown tool: {call_params.name}")

        # Extract arguments
        message = call_params.arguments.get("message")
        if not message:
            raise ValueError("Missing required argument: message")

        thread_id = call_params.arguments.get("thread_id")
        assistant_id = call_params.arguments.get("assistant_id", "agent")

        # Execute the agent
        try:
            result_text = await self._execute_agent(
                message=message,
                thread_id=thread_id,
                assistant_id=assistant_id,
            )
            result = McpToolCallResult(
                content=[McpToolCallContentItem(type="text", text=result_text)],
                is_error=False,
            )
        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            result = McpToolCallResult(
                content=[McpToolCallContentItem(type="text", text=f"Error: {str(e)}")],
                is_error=True,
            )

        return result.model_dump(by_alias=True)

    async def _execute_agent(
        self,
        message: str,
        thread_id: str | None = None,
        assistant_id: str = "agent",
    ) -> str:
        """Execute the LangGraph agent with a message.

        Args:
            message: The user message to send.
            thread_id: Optional thread ID for continuity.
            assistant_id: Assistant ID to use.

        Returns:
            The agent's response text.
        """
        # Import here to avoid circular imports
        from robyn_server.agent import execute_agent_run

        try:
            # Execute the agent and get the response
            result = await execute_agent_run(
                message=message,
                thread_id=thread_id,
                assistant_id=assistant_id,
            )

            # Extract text from result
            if isinstance(result, dict):
                # Try to get the last message content
                messages = result.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        return last_message.get("content", json.dumps(result))
                    elif hasattr(last_message, "content"):
                        return last_message.content
                return json.dumps(result)
            return str(result)

        except ImportError:
            # Agent module not available - return placeholder
            logger.warning("Agent execution not available - returning placeholder")
            return f"[Agent execution placeholder] Received message: {message}"

    async def _handle_prompts_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the prompts/list method.

        We don't expose prompts, so return empty list.

        Args:
            params: Optional cursor for pagination.

        Returns:
            Empty prompts list.
        """
        return {"prompts": []}

    async def _handle_resources_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the resources/list method.

        We don't expose resources, so return empty list.

        Args:
            params: Optional cursor for pagination.

        Returns:
            Empty resources list.
        """
        return {"resources": []}

    async def _handle_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the ping method.

        Simple health check.

        Args:
            params: Ignored.

        Returns:
            Empty dict (pong).
        """
        return {}


# Global handler instance
mcp_handler = McpMethodHandler()
