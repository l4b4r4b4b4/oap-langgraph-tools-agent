import os
import logging
from langchain_core.runnables import RunnableConfig
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from tools_agent.utils.tools import create_rag_tool
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from tools_agent.utils.token import fetch_tokens
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from langchain_core.tools import StructuredTool
from tools_agent.utils.tools import (
    wrap_mcp_authenticate_tool,
    create_langchain_mcp_tool,
)
from robyn_server.database import get_checkpointer, get_store

logger = logging.getLogger(__name__)


def _safe_present_configurable_keys(config: RunnableConfig) -> list[str]:
    """Return a stable, non-sensitive view of the configurable keys present.

    This intentionally does not log values to avoid leaking secrets.
    """
    configurable: dict = config.get("configurable", {}) or {}
    return sorted(str(key) for key in configurable.keys())


def _safe_mask_url(url: Optional[str]) -> Optional[str]:
    """Mask potentially sensitive URL parts (query strings, userinfo).

    This keeps the scheme/host/path which is enough to confirm routing.
    """
    if not url:
        return url
    # Avoid importing urllib just for logging; keep it conservative.
    # Drop query fragments if present.
    return url.split("?", 1)[0].split("#", 1)[0]


def _merge_assistant_configurable_into_run_config(
    config: RunnableConfig,
) -> RunnableConfig:
    """Merge assistant-level configurable settings into the run config.

    LangGraph runtime-inmem passes per-run metadata in `configurable`, but in some
    versions it may not automatically inject assistant `configurable` fields into
    `graph(config)`. This merge reads the assistant settings (if present) and
    overlays them onto the run config so fields such as `base_url` reach the agent.

    Notes:
        - Values are not logged here to avoid leaking secrets.
        - Run-level keys take precedence over assistant-level keys.

    Returns:
        A new RunnableConfig with merged `configurable`.
    """
    original_configurable: dict = config.get("configurable", {}) or {}

    # Common places LangGraph API may attach assistant settings:
    # - "assistant" (object)
    # - "assistant_config" (object)
    # - "assistant_configurable" (already flattened)
    assistant_configurable: dict = {}

    assistant_container = original_configurable.get("assistant")
    if isinstance(assistant_container, dict):
        assistant_cfg = assistant_container.get("configurable")
        if isinstance(assistant_cfg, dict):
            assistant_configurable.update(assistant_cfg)

    assistant_config_container = original_configurable.get("assistant_config")
    if isinstance(assistant_config_container, dict):
        assistant_cfg = assistant_config_container.get("configurable")
        if isinstance(assistant_cfg, dict):
            assistant_configurable.update(assistant_cfg)

    assistant_config_flat = original_configurable.get("assistant_configurable")
    if isinstance(assistant_config_flat, dict):
        assistant_configurable.update(assistant_config_flat)

    if not assistant_configurable:
        return config

    merged_configurable = {**assistant_configurable, **original_configurable}
    return {**config, "configurable": merged_configurable}


UNEDITABLE_SYSTEM_PROMPT = "\nIf the tool throws an error requiring authentication, provide the user with a Markdown link to the authentication page and prompt them to authenticate."

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that has access to a variety of tools."
)


class RagConfig(BaseModel):
    rag_url: Optional[str] = None
    """The URL of the rag server"""
    collections: Optional[List[str]] = None
    """The collections to use for rag"""


class MCPConfig(BaseModel):
    url: Optional[str] = Field(
        default=None,
        optional=True,
    )
    """The URL of the MCP server"""
    tools: Optional[List[str]] = Field(
        default=None,
        optional=True,
    )
    """The tools to make available to the LLM"""
    auth_required: Optional[bool] = Field(
        default=False,
        optional=True,
    )
    """Whether the MCP server requires authentication"""


class GraphConfigPydantic(BaseModel):
    model_name: Optional[str] = Field(
        default="openai:gpt-4o",
        metadata={
            "x_oap_ui_config": {
                "type": "select",
                "default": "openai:gpt-4o",
                "description": "The model to use in all generations",
                "options": [
                    {
                        "label": "Claude Sonnet 4",
                        "value": "anthropic:claude-sonnet-4-0",
                    },
                    {
                        "label": "Claude 3.7 Sonnet",
                        "value": "anthropic:claude-3-7-sonnet-latest",
                    },
                    {
                        "label": "Claude 3.5 Sonnet",
                        "value": "anthropic:claude-3-5-sonnet-latest",
                    },
                    {
                        "label": "Claude 3.5 Haiku",
                        "value": "anthropic:claude-3-5-haiku-latest",
                    },
                    {"label": "o4 mini", "value": "openai:o4-mini"},
                    {"label": "o3", "value": "openai:o3"},
                    {"label": "o3 mini", "value": "openai:o3-mini"},
                    {"label": "GPT 4o", "value": "openai:gpt-4o"},
                    {"label": "GPT 4o mini", "value": "openai:gpt-4o-mini"},
                    {"label": "GPT 4.1", "value": "openai:gpt-4.1"},
                    {"label": "GPT 4.1 mini", "value": "openai:gpt-4.1-mini"},
                    {
                        "label": "Custom OpenAI-compatible endpoint",
                        "value": "custom:",
                    },
                ],
            }
        },
    )
    temperature: Optional[float] = Field(
        default=0.7,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 0.7,
                "min": 0,
                "max": 2,
                "step": 0.1,
                "description": "Controls randomness (0 = deterministic, 2 = creative)",
            }
        },
    )
    max_tokens: Optional[int] = Field(
        default=4000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 4000,
                "min": 1,
                "description": "The maximum number of tokens to generate",
            }
        },
    )
    system_prompt: Optional[str] = Field(
        default=DEFAULT_SYSTEM_PROMPT,
        metadata={
            "x_oap_ui_config": {
                "type": "textarea",
                "placeholder": "Enter a system prompt...",
                "description": f"The system prompt to use in all generations. The following prompt will always be included at the end of the system prompt:\n---{UNEDITABLE_SYSTEM_PROMPT}\n---",
                "default": DEFAULT_SYSTEM_PROMPT,
            }
        },
    )
    mcp_config: Optional[MCPConfig] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "mcp",
                # Here is where you would set the default tools.
                # "default": {
                #     "tools": ["Math_Divide", "Math_Mod"]
                # }
            }
        },
    )
    rag: Optional[RagConfig] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "rag",
                # Here is where you would set the default collection. Use collection IDs
                # "default": {
                #     "collections": [
                #         "fd4fac19-886c-4ac8-8a59-fff37d2b847f",
                #         "659abb76-fdeb-428a-ac8f-03b111183e25",
                #     ]
                # },
            }
        },
    )
    # Custom endpoint configuration
    base_url: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "placeholder": "http://localhost:7374/v1",
                "description": "Base URL for custom OpenAI-compatible API",
                "visible_when": {"model_name": "custom:"},
            }
        },
    )
    custom_model_name: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "placeholder": "mistralai/ministral-3b-instruct",
                "description": "Model name for custom endpoint",
                "visible_when": {"model_name": "custom:"},
            }
        },
    )
    custom_api_key: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "password",
                "placeholder": "Leave empty for local vLLM",
                "description": "API key for custom endpoint (optional)",
                "visible_when": {"model_name": "custom:"},
            }
        },
    )


def get_api_key_for_model(model_name: str, config: RunnableConfig):
    model_name = model_name.lower()

    # Handle custom endpoints
    if model_name.startswith("custom:"):
        # First check config for custom_api_key
        custom_key = config.get("configurable", {}).get("custom_api_key")
        if custom_key:
            return custom_key
        # Fallback to environment variable
        return os.getenv("CUSTOM_API_KEY")

    # Existing logic for standard providers
    model_to_key = {
        "openai:": "OPENAI_API_KEY",
        "anthropic:": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    key_name = next(
        (key for prefix, key in model_to_key.items() if model_name.startswith(prefix)),
        None,
    )
    if not key_name:
        return None
    api_keys = config.get("configurable", {}).get("apiKeys", {})
    if api_keys and api_keys.get(key_name) and len(api_keys[key_name]) > 0:
        return api_keys[key_name]
    # Fallback to environment variable
    return os.getenv(key_name)


async def graph(config: RunnableConfig):
    config = _merge_assistant_configurable_into_run_config(config)

    # INFO-level, runtime-safe logging to confirm config propagation.
    # Do NOT log values that may contain secrets.
    logger.info(
        "graph() invoked; configurable_keys=%s",
        _safe_present_configurable_keys(config),
    )

    cfg = GraphConfigPydantic(**(config.get("configurable", {}) or {}))

    logger.info(
        "graph() parsed_config; model_name=%s base_url_present=%s custom_model_name_present=%s custom_api_key_present=%s",
        cfg.model_name,
        bool(cfg.base_url),
        bool(cfg.custom_model_name),
        bool(cfg.custom_api_key),
    )

    tools = []

    supabase_token = config.get("configurable", {}).get("x-supabase-access-token")
    if cfg.rag and cfg.rag.rag_url and cfg.rag.collections and supabase_token:
        for collection in cfg.rag.collections:
            rag_tool = await create_rag_tool(
                cfg.rag.rag_url, collection, supabase_token
            )
            tools.append(rag_tool)

    if cfg.mcp_config and cfg.mcp_config.auth_required:
        mcp_tokens = await fetch_tokens(config)
    else:
        mcp_tokens = None
    if (
        cfg.mcp_config
        and cfg.mcp_config.url
        and cfg.mcp_config.tools
        and (mcp_tokens or not cfg.mcp_config.auth_required)
    ):
        server_url = cfg.mcp_config.url.rstrip("/") + "/mcp"

        tool_names_to_find = set(cfg.mcp_config.tools)
        fetched_mcp_tools_list: list[StructuredTool] = []
        names_of_tools_added = set()

        # If the tokens are not None, then we need to add the authorization header. otherwise make headers None
        headers = (
            mcp_tokens is not None
            and {"Authorization": f"Bearer {mcp_tokens['access_token']}"}
            or None
        )
        try:
            async with streamablehttp_client(server_url, headers=headers) as streams:
                read_stream, write_stream, _ = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    page_cursor = None

                    while True:
                        tool_list_page = await session.list_tools(cursor=page_cursor)

                        if not tool_list_page or not tool_list_page.tools:
                            break

                        for mcp_tool in tool_list_page.tools:
                            if not tool_names_to_find or (
                                mcp_tool.name in tool_names_to_find
                                and mcp_tool.name not in names_of_tools_added
                            ):
                                langchain_tool = create_langchain_mcp_tool(
                                    mcp_tool, mcp_server_url=server_url, headers=headers
                                )
                                fetched_mcp_tools_list.append(
                                    wrap_mcp_authenticate_tool(langchain_tool)
                                )
                                if tool_names_to_find:
                                    names_of_tools_added.add(mcp_tool.name)

                        page_cursor = tool_list_page.nextCursor

                        if not page_cursor:
                            break
                        if tool_names_to_find and len(names_of_tools_added) == len(
                            tool_names_to_find
                        ):
                            break

                    tools.extend(fetched_mcp_tools_list)
        except Exception as e:
            # Avoid printing (may not route to runtime logs) and avoid leaking headers/tokens.
            logger.warning("Failed to fetch MCP tools: %s", str(e))
            pass

    # Initialize model based on configuration
    if cfg.base_url:
        # Custom endpoint - use ChatOpenAI with OpenAI-compatible base URL.
        # LangChain's vLLM integration docs recommend `openai_api_base` + `openai_api_key="EMPTY"`.
        masked_base_url = _safe_mask_url(cfg.base_url)
        logger.info(
            "LLM routing: custom endpoint enabled; base_url=%s", masked_base_url
        )

        # Get API key for custom endpoint (do not log the key)
        api_key = get_api_key_for_model("custom:", config)
        if not api_key:
            # Use "EMPTY" for local vLLM that doesn't require authentication
            api_key = "EMPTY"
            logger.info("LLM auth: no custom API key provided; using EMPTY")
        else:
            logger.info("LLM auth: custom API key provided (masked)")

        # Use custom model name if provided, otherwise use the configured model_name
        model_name = cfg.custom_model_name or cfg.model_name
        logger.info("LLM model: %s", model_name)

        # Prefer the vLLM-recommended parameters. Avoid passing multiple aliases
        # for the same setting to reduce ambiguity across versions.
        model = ChatOpenAI(
            openai_api_base=cfg.base_url,
            openai_api_key=api_key,
            model=model_name,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    else:
        # Standard provider - use init_chat_model
        logger.info(
            "LLM routing: standard provider enabled; model_name=%s", cfg.model_name
        )
        api_key = get_api_key_for_model(cfg.model_name, config)
        logger.info("LLM auth: standard provider api key present=%s", bool(api_key))

        model = init_chat_model(
            cfg.model_name,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            api_key=api_key or "No token found",
        )

    # Get persistence components (None if DATABASE_URL not set)
    checkpointer = get_checkpointer()
    store = get_store()

    if checkpointer is not None:
        logger.info("graph() using Postgres checkpointer for thread persistence")
    if store is not None:
        logger.info("graph() using Postgres store for cross-thread memory")

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        store=store,
    )
