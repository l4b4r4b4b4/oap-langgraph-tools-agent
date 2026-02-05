"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

from typing_extensions import Literal, TypedDict, Dict, List, Union, Optional
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from copilotkit import CopilotKitState
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from copilotkit.langgraph import copilotkit_exit
from langfuse.callback import CallbackHandler
from dotenv import load_dotenv


import os

import logging

load_dotenv()

# Check required environment variables
required_vars = ["OPENAI_BASE_URL", "OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    raise EnvironmentError(
        f"Required environment variables are missing: {', '.join(missing_vars)}"
    )

# Set up logging
# Get log level from environment variable, default to DEBUG
log_level_name = os.environ.get("LOG_LEVEL", "DEBUG")
log_level = getattr(logging, log_level_name.upper(), logging.DEBUG)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


# Define the connection type structures
class StdioConnection(TypedDict):
    command: str
    args: List[str]
    transport: Literal["stdio"]


class SSEConnection(TypedDict):
    url: str
    transport: Literal["sse"]


# Type for MCP configuration
MCPConfig = Dict[str, Union[StdioConnection, SSEConnection]]


class AgentState(CopilotKitState):
    """
    Here we define the state of the agent

    In this instance, we're inheriting from CopilotKitState, which will bring in
    the CopilotKitState fields. We're also adding a custom field, `mcp_config`,
    which will be used to configure MCP services for the agent.
    """

    # Define mcp_config as an optional field without skipping validation
    mcp_config: Optional[MCPConfig]


os.environ["MCP_CACHES_INITIALIZED"] = "1"
os.environ["MCP_USE_EXISTING_CACHES"] = "1"
os.environ["MCP_CACHE_CONFIGURED"] = "1"
# os.environ["ER_CACHE_BASE"] = os.environ.get(
#     "ER_CACHE_BASE", "redis://localhost:6379/0"
# )


# Default MCP configuration to use when no configuration is provided in the state
# Uses relative paths that will work within the project structure
DEFAULT_MCP_CONFIG: MCPConfig = {
    "math_toolset": {
        "command": "python",
        # Use a relative path that will be resolved based on the current working directory
        "args": [
            os.path.join(
                os.path.dirname(__file__), "..", "system_2/servers/", "math_toolset.py"
            )
        ],
        # "args": ["/app/src/system_2/servers/math_toolset.py"],
        "transport": "stdio",
    },
}

model_params = {
    "model": "mistralai/mistral-large-2411",  # uai/lm-small | mistralai/mistral-large-2411
    "openai_api_base": os.environ.get("OPENAI_BASE_URL"),
    "openai_api_key": os.environ.get("OPENAI_API_KEY"),
    "temperature": 0,
}

langfuse_handler = CallbackHandler(
    public_key="lf_pk_12345abcdefghijklmnopqrstuvwxyz",  # "lf_pk_12345abcdefghijklmnopqrstuvwxyz" | pk-lf-82ec6f90-b253-443d-92ee-e20a5838bb53
    secret_key="lf_sk_67890abcdefghijklmnopqrstuvwxyz",  # "lf_sk_67890abcdefghijklmnopqrstuvwxyz" | sk-lf-3add59b0-cbaf-4377-b105-78d45c188eda
    host="http://localhost:3003",
    session_id="dev_cluster_test",
    user_id="dev_cluster_user",
    # flush_at=1,
)
print(f"langfuse_handler: {repr(langfuse_handler)}")


async def chat_node(
    state: AgentState, config: RunnableConfig
) -> Command[Literal["__end__"]]:
    """
    This is a simplified agent that uses the ReAct agent as a subgraph.
    It handles both chat responses and tool execution in one node.
    """
    # Get MCP configuration from state, or use the default config if not provided
    mcp_config = state.get("mcp_config", DEFAULT_MCP_CONFIG)
    logger.debug(f"mcp_config: {mcp_config}, default: {DEFAULT_MCP_CONFIG}")

    print(f"mcp_config: {mcp_config}, default: {DEFAULT_MCP_CONFIG}")

    # Set up the MCP client and tools using the configuration from state
    async with MultiServerMCPClient(mcp_config) as mcp_client:
        # Get the tools
        mcp_tools = mcp_client.get_tools()
        logger.debug(f"Client's mcp_tools: {repr(mcp_tools)}")

        # Create the react agent
        model = ChatOpenAI(
            **model_params,
            model_kwargs={"tool_choice": "auto"},
            extra_body={"tool_choice": "auto"},
        )
        react_agent = create_react_agent(model, mcp_tools)

        # Prepare messages for the react agent
        agent_input = {"messages": state["messages"]}

        # Run the react agent subgraph with our input
        agent_response = await react_agent.ainvoke(
            agent_input,
            # config={"callbacks": [langfuse_handler]},
        )

        # Update the state with the new messages
        updated_messages = state["messages"] + agent_response.get("messages", [])
        await copilotkit_exit(config)
        # End the graph with the updated messages
        return Command(
            goto=END,
            update={"messages": updated_messages},
        )


# Define the workflow graph with only a chat node
workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.set_entry_point("chat_node")

# Compile the workflow graph
graph = workflow.compile(MemorySaver())
