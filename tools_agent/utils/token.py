import logging
from typing import Any

import aiohttp
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_store


async def get_mcp_access_token(
    supabase_token: str,
    base_mcp_url: str,
) -> dict[str, Any] | None:
    """
    Exchange a Supabase token for an MCP access token.

    Args:
        supabase_token: The Supabase token to exchange
        base_mcp_url: The base URL for the MCP server

    Returns:
        The token data as a dictionary if successful, None otherwise
    """
    try:
        # Exchange Supabase token for MCP access token
        form_data = {
            "client_id": "mcp_default",
            "subject_token": supabase_token,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "resource": base_mcp_url.rstrip("/") + "/mcp",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                base_mcp_url.rstrip("/") + "/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=form_data,
            ) as token_response:
                if token_response.status != 200:
                    response_text = await token_response.text()
                    logging.error(f"Token exchange failed: {response_text}")
                    return None

                token_data = await token_response.json()
                return token_data if isinstance(token_data, dict) else None
    except Exception as e:
        logging.error(f"Error during token exchange: {e}")

    return None


async def get_tokens(config: RunnableConfig) -> dict[str, Any] | None:
    """Return cached MCP tokens from the LangGraph store if present and valid.

    This function is deliberately defensive:
    - Store may be unavailable (returns None).
    - Token objects may have unexpected shapes.
    - Missing/invalid expiration metadata results in cache eviction + None.
    """
    store = get_store()
    if store is None:
        return None

    configurable = config.get("configurable", {}) or {}
    thread_id = configurable.get("thread_id")
    if not thread_id:
        return None

    user_id = configurable.get("owner")
    if not user_id:
        return None

    try:
        token_record = await store.aget((user_id, "tokens"), "data")
    except Exception:
        return None

    if not token_record:
        return None

    tokens_value = getattr(token_record, "value", None)
    if not isinstance(tokens_value, dict):
        return None

    created_at = getattr(token_record, "created_at", None)
    if created_at is None:
        # Without created_at, we cannot safely evaluate expiry.
        try:
            await store.adelete((user_id, "tokens"), "data")
        except Exception:
            pass
        return None

    expires_in_raw = tokens_value.get("expires_in")
    expires_in_seconds: float | None = None
    if expires_in_raw is not None:
        try:
            expires_in_seconds = float(expires_in_raw)
        except (TypeError, ValueError):
            pass

    if expires_in_seconds is None:
        try:
            await store.adelete((user_id, "tokens"), "data")
        except Exception:
            pass
        return None

    # At this point expires_in_seconds is guaranteed to be a float.
    validated_expires: float = expires_in_seconds

    from datetime import datetime, timedelta, timezone

    current_time = datetime.now(timezone.utc)
    expiration_time = created_at + timedelta(seconds=validated_expires)

    if current_time > expiration_time:
        try:
            await store.adelete((user_id, "tokens"), "data")
        except Exception:
            pass
        return None

    return tokens_value


async def set_tokens(config: RunnableConfig, tokens: dict[str, Any] | None) -> None:
    """Persist MCP tokens to the LangGraph store (best-effort)."""
    if tokens is None:
        return

    store = get_store()
    if store is None:
        return

    configurable = config.get("configurable", {}) or {}
    thread_id = configurable.get("thread_id")
    if not thread_id:
        return

    user_id = configurable.get("owner")
    if not user_id:
        return

    try:
        await store.aput((user_id, "tokens"), "data", tokens)
    except Exception:
        # Best-effort cache; ignore storage failures.
        return


async def fetch_tokens(config: RunnableConfig) -> dict[str, Any] | None:
    """Fetch MCP access token if it doesn't already exist in the store.

    Supports the multi-server MCP config shape::

        configurable.mcp_config.servers = [
            {"name": "...", "url": "...", "auth_required": bool, ...},
            ...
        ]

    Returns a token dict that can be reused for one or more auth-required
    MCP servers, or ``None`` when tokens are unavailable.
    """
    current_tokens = await get_tokens(config)
    if isinstance(current_tokens, dict) and current_tokens:
        return current_tokens

    configurable = config.get("configurable", {}) or {}

    supabase_token = configurable.get("x-supabase-access-token")
    if not supabase_token:
        return None

    mcp_config = configurable.get("mcp_config")
    if not isinstance(mcp_config, dict):
        return None

    servers = mcp_config.get("servers")
    if not isinstance(servers, list) or not servers:
        return None

    # Find the first auth-required server with a usable URL.
    base_mcp_url: str | None = None
    for server in servers:
        if not isinstance(server, dict):
            continue
        if not server.get("auth_required"):
            continue
        url_value = server.get("url")
        if isinstance(url_value, str) and url_value.strip():
            base_mcp_url = url_value.strip()
            break

    if not base_mcp_url:
        return None

    mcp_tokens: dict[str, Any] | None = await get_mcp_access_token(
        supabase_token, base_mcp_url
    )
    if mcp_tokens is None:
        return None

    await set_tokens(config, mcp_tokens)
    return mcp_tokens
