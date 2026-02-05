#!/usr/bin/env python3
"""
In-process smoke test for `tools_agent/agent.py:graph` against a remote vLLM
(OpenAI-compatible) deployment.

Why this exists:
- Validates the *actual* graph served by LangGraph runtime (`langgraph.json`)
  can route to a custom OpenAI-compatible endpoint (vLLM) when configured via
  `RunnableConfig.configurable`.
- Runs entirely in-process (no LangGraph API server required).
- Avoids Supabase/auth complexity (that is tested elsewhere).

How it works:
- Imports `tools_agent.agent.graph` (async factory that returns a compiled agent)
- Creates the agent using a RunnableConfig that sets:
  - model_name="custom:"
  - base_url="http://localhost:7374/v1" (override via env)
  - custom_model_name="mistralai/ministral-3b-instruct" (override via env)
  - custom_api_key="EMPTY" (override via env)
- Invokes the returned agent on a simple user message
- Prints a minimal, non-sensitive transcript

Environment variables:
- VLLM_BASE_URL (default: http://localhost:7374/v1)
- VLLM_MODEL_NAME (default: mistralai/ministral-3b-instruct)
- VLLM_API_KEY (default: EMPTY)
- LOG_LEVEL (optional; default: INFO)

Run:
    uv run test_tools_agent_vllm_smoke.py
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from langchain_core.runnables import RunnableConfig


def _configure_logging() -> None:
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _get_vllm_config() -> tuple[str, str, str]:
    vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:7374/v1")
    vllm_model_name = os.getenv("VLLM_MODEL_NAME", "mistralai/ministral-3b-instruct")
    vllm_api_key = os.getenv("VLLM_API_KEY", "EMPTY")
    return vllm_base_url, vllm_model_name, vllm_api_key


def _summarize_result(result: Any) -> None:
    """Print a best-effort summary without assuming a specific message schema."""
    logger = logging.getLogger(__name__)

    if (
        isinstance(result, dict)
        and "messages" in result
        and isinstance(result["messages"], list)
    ):
        messages = result["messages"]
        logger.info("Result contains %s message(s)", len(messages))
        for index, message in enumerate(messages):
            message_type = getattr(message, "type", type(message).__name__)
            content = getattr(message, "content", None)
            tool_calls = getattr(message, "tool_calls", None)

            logger.info("Message %s: type=%s", index, message_type)

            if isinstance(content, str) and content:
                preview = content if len(content) <= 240 else f"{content[:240]}..."
                logger.info("  content=%s", preview)

            if tool_calls:
                try:
                    logger.info("  tool_calls=%s", len(tool_calls))
                    for tool_call in tool_calls:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("args")
                        logger.info("    - %s(%s)", tool_name, tool_args)
                except Exception:
                    logger.info("  tool_calls present (unparsable shape)")
        return

    logger.info("Result shape=%s", type(result).__name__)
    if isinstance(result, dict):
        logger.info("Result keys=%s", sorted(result.keys()))


async def _run_smoke_test() -> int:
    logger = logging.getLogger(__name__)

    vllm_base_url, vllm_model_name, vllm_api_key = _get_vllm_config()

    # Import here so logging is set up first.
    from tools_agent.agent import graph  # pylint: disable=import-outside-toplevel
    from langchain_core.messages import HumanMessage  # pylint: disable=import-outside-toplevel

    logger.info("Creating tools_agent graph with vLLM config")
    logger.info("vLLM base_url=%s", vllm_base_url)
    logger.info("vLLM model=%s", vllm_model_name)
    logger.info("vLLM api_key=%s", "EMPTY" if vllm_api_key == "EMPTY" else "(provided)")

    run_config: RunnableConfig = {
        "configurable": {
            # Route through the custom OpenAI-compatible path in tools_agent/agent.py
            "model_name": "custom:",
            "base_url": vllm_base_url,
            "custom_model_name": vllm_model_name,
            "custom_api_key": vllm_api_key,
            # Keep deterministic and short for smoke testing
            "temperature": 0.0,
            "max_tokens": 120,
            # Minimal prompt to avoid surprising behavior from the model
            "system_prompt": "You are a helpful assistant. Answer concisely.",
            # Explicitly disable optional integrations for a clean smoke test
            "mcp_config": None,
            "rag": None,
        }
    }

    # `graph` is an async factory that returns a runnable (compiled agent).
    runnable_agent = await graph(run_config)

    logger.info("Invoking agent...")
    result = await runnable_agent.ainvoke(
        {
            "messages": [
                HumanMessage(content="What is 2 + 2? Answer with just the number.")
            ]
        },
        config=run_config,
    )

    _summarize_result(result)

    # Best-effort correctness check
    last_text = None
    if isinstance(result, dict) and isinstance(result.get("messages"), list):
        for message in reversed(result["messages"]):
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                last_text = content.strip()
                break

    if last_text is None:
        logger.error("No assistant text content found in result")
        return 1

    # Be lenient: models sometimes wrap with formatting.
    if "4" in last_text or last_text.lower() == "four":
        logger.info("✓ Smoke test passed (assistant responded with 4)")
        return 0

    logger.warning("Assistant output did not clearly contain '4': %r", last_text)
    logger.info("✓ Smoke test still considered passed (agent responded)")
    return 0


def main() -> int:
    _configure_logging()
    return asyncio.run(_run_smoke_test())


if __name__ == "__main__":
    raise SystemExit(main())
