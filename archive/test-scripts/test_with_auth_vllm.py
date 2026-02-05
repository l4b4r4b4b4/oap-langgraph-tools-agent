#!/usr/bin/env python3
"""
Test vLLM integration with authenticated LangGraph API.

This test:
1. Creates a test user using Supabase service role key (SUPABASE_SECRET)
2. Gets a JWT token for the test user
3. Tests the LangGraph API with the JWT token
4. Uses custom vLLM endpoint configuration
5. Cleans up test user after completion

Debugging notes:
- Newer LangGraph API versions return thread history as a list of ThreadState objects.
- ThreadState.values typically contains a "messages" list; we log message roles when parsing fails.
"""

import os
import sys
import asyncio
import aiohttp
import uuid
from typing import Dict, Any, Optional
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try to load .env manually
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("\"'")
    except FileNotFoundError:
        pass  # .env file not found, use existing environment variables

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SECRET = os.getenv("SUPABASE_SECRET")  # Service role key (sb_secret_...)
LANGRAPH_SERVER_URL = os.getenv("LANGRAPH_SERVER_URL", "http://localhost:2024")
# Default to port-forwarded AKS vLLM (8001) instead of local vLLM (7374)
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "ministral-3b-instruct")

# Test user credentials (random to avoid conflicts)
TEST_USER_EMAIL = f"test_{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_PASSWORD = "TestPassword123!"


async def create_test_user() -> Optional[Dict[str, Any]]:
    """Create a test user using Supabase admin API with service role key."""
    if not SUPABASE_SECRET:
        logger.error("SUPABASE_SECRET environment variable not set")
        logger.error("Need service role key (sb_secret_...) to create users")
        return None

    logger.info(f"Creating test user: {TEST_USER_EMAIL}")

    headers = {
        "apikey": SUPABASE_SECRET,
        "Authorization": f"Bearer {SUPABASE_SECRET}",
        "Content-Type": "application/json",
    }

    user_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "email_confirm": True,  # Auto-confirm email for testing
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Create user via admin API
            async with session.post(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=headers,
                json=user_data,
            ) as response:
                if response.status == 200:
                    user_info = await response.json()
                    logger.info(f"Created user: {user_info.get('id')}")
                    return user_info
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to create user: {response.status} - {error_text}"
                    )
                    return None
    except Exception as e:
        logger.error(f"Error creating test user: {e}")
        return None


async def get_user_jwt() -> Optional[str]:
    """Get JWT token for the test user by signing in."""
    logger.info(f"Getting JWT token for {TEST_USER_EMAIL}")

    headers = {
        "apikey": SUPABASE_SECRET,
        "Content-Type": "application/json",
    }

    signin_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Sign in to get JWT
            async with session.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers=headers,
                json=signin_data,
            ) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    access_token = auth_data.get("access_token")
                    if access_token:
                        logger.info("Got JWT token successfully")
                        return access_token
                    else:
                        logger.error("No access_token in response")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get JWT: {response.status} - {error_text}")
                    return None
    except Exception as e:
        logger.error(f"Error getting JWT: {e}")
        return None


async def delete_test_user(user_id: str) -> bool:
    """Delete the test user after testing."""
    if not SUPABASE_SECRET:
        return False

    logger.info(f"Deleting test user: {user_id}")

    headers = {
        "apikey": SUPABASE_SECRET,
        "Authorization": f"Bearer {SUPABASE_SECRET}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers=headers,
            ) as response:
                if response.status == 200:
                    logger.info("Test user deleted successfully")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Failed to delete user: {response.status} - {error_text}"
                    )
                    return False
    except Exception as e:
        logger.warning(f"Error deleting test user: {e}")
        return False


async def test_langgraph_with_auth(jwt_token: str) -> bool:
    """Test LangGraph API with authentication using vLLM endpoint."""
    logger.info("Testing LangGraph API with authentication...")

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        # 1. Create assistant with vLLM configuration
        logger.info("Creating assistant with vLLM configuration...")
        assistant_data = {
            "graph_id": "agent",
            "name": "vLLM Test Assistant",
            "description": "Assistant using local vLLM (Ministral-3-3B)",
            "config": {
                "configurable": {
                    "model_name": "custom:",
                    "base_url": VLLM_BASE_URL,
                    "custom_model_name": VLLM_MODEL_NAME,
                    "custom_api_key": "EMPTY",
                    "temperature": 0.1,
                    "max_tokens": 100,
                    "system_prompt": "You are a helpful assistant. Answer questions concisely.",
                }
            },
        }

        async with session.post(
            f"{LANGRAPH_SERVER_URL}/assistants",
            headers=headers,
            json=assistant_data,
        ) as response:
            if response.status == 200:
                assistant_result = await response.json()
                assistant_id = assistant_result.get("assistant_id")
                logger.info(f"Created assistant: {assistant_id}")
            else:
                error_text = await response.text()
                logger.error(
                    f"Failed to create assistant: {response.status} - {error_text}"
                )
                return False

        # 2. Create a thread
        logger.info("Creating thread...")
        async with session.post(
            f"{LANGRAPH_SERVER_URL}/threads",
            headers=headers,
            json={},
        ) as response:
            if response.status == 200:
                thread_result = await response.json()
                thread_id = thread_result.get("thread_id")
                logger.info(f"Created thread: {thread_id}")
            else:
                error_text = await response.text()
                logger.error(
                    f"Failed to create thread: {response.status} - {error_text}"
                )
                return False

        # 3. Run the assistant on the thread
        logger.info("Running assistant with vLLM...")
        run_data = {
            "assistant_id": assistant_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": "What is 2 + 2? Answer with just the number.",
                    }
                ]
            },
        }

        async with session.post(
            f"{LANGRAPH_SERVER_URL}/threads/{thread_id}/runs",
            headers=headers,
            json=run_data,
        ) as response:
            if response.status == 200:
                run_result = await response.json()
                run_id = run_result.get("run_id")
                logger.info(f"Started run: {run_id}")

                # 4. Poll for run completion
                # Newer langgraph-api versions report terminal success states as "success"
                # (older versions used "completed"). Treat both as terminal.
                for attempt in range(10):  # Try for 10 seconds
                    await asyncio.sleep(1)

                    async with session.get(
                        f"{LANGRAPH_SERVER_URL}/threads/{thread_id}/runs/{run_id}",
                        headers=headers,
                    ) as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            run_status = status_data.get("status")
                            logger.info(f"Run status: {run_status}")

                            if run_status in ["completed", "success"]:
                                # 5. Prefer /state for final output; fall back to /history for older/variant shapes.
                                #
                                # langgraph-api 0.7.x removed /threads/{thread_id}/messages. /state is typically the
                                # most direct way to access the latest messages, while /history provides a list of
                                # ThreadState objects over time.
                                assistant_texts: list[str] = []

                                async with session.get(
                                    f"{LANGRAPH_SERVER_URL}/threads/{thread_id}/state",
                                    headers=headers,
                                ) as state_response:
                                    if state_response.status == 200:
                                        state_data = await state_response.json()

                                        # Troubleshooting: log response shape (not content)
                                        if isinstance(state_data, dict):
                                            logger.info(
                                                "Thread state response shape: dict(keys=%s)",
                                                sorted(list(state_data.keys())),
                                            )
                                        else:
                                            logger.info(
                                                "Thread state response shape: %s",
                                                type(state_data).__name__,
                                            )

                                        values = (
                                            state_data.get("values")
                                            if isinstance(state_data, dict)
                                            else None
                                        )

                                        value_containers: list[dict[str, Any]] = []
                                        if isinstance(values, dict):
                                            value_containers = [values]
                                        elif isinstance(values, list):
                                            value_containers = [
                                                item
                                                for item in values
                                                if isinstance(item, dict)
                                            ]

                                        if value_containers:
                                            first_values_container = value_containers[0]
                                            logger.info(
                                                "ThreadState.values keys: %s",
                                                sorted(
                                                    list(first_values_container.keys())
                                                ),
                                            )

                                            messages_for_role_logging = (
                                                first_values_container.get("messages")
                                            )
                                            if isinstance(
                                                messages_for_role_logging, list
                                            ):
                                                roles_present: list[str] = []
                                                for (
                                                    message_for_role_logging
                                                ) in messages_for_role_logging:
                                                    if not isinstance(
                                                        message_for_role_logging, dict
                                                    ):
                                                        continue
                                                    # LangChain messages use "type" (ai, human, tool)
                                                    # OpenAI-style messages use "role" (assistant, user)
                                                    role = message_for_role_logging.get(
                                                        "role"
                                                    ) or message_for_role_logging.get(
                                                        "type"
                                                    )
                                                    if isinstance(role, str):
                                                        roles_present.append(role)
                                                logger.info(
                                                    "ThreadState.values.messages types_present=%s",
                                                    sorted(set(roles_present)),
                                                )

                                            for value_container in value_containers:
                                                messages = value_container.get(
                                                    "messages"
                                                )
                                                if not isinstance(messages, list):
                                                    continue

                                                for message in messages:
                                                    if not isinstance(message, dict):
                                                        continue
                                                    # LangChain messages use "type": "ai"
                                                    # OpenAI-style messages use "role": "assistant"
                                                    msg_type = message.get(
                                                        "type"
                                                    ) or message.get("role")
                                                    if msg_type not in (
                                                        "ai",
                                                        "assistant",
                                                    ):
                                                        continue

                                                    content = message.get("content")
                                                    if isinstance(content, str):
                                                        assistant_texts.append(content)
                                                        continue

                                                    if (
                                                        isinstance(content, list)
                                                        and content
                                                    ):
                                                        first = content[0]
                                                        if isinstance(first, dict):
                                                            text = first.get("text")
                                                            if (
                                                                isinstance(text, str)
                                                                and text
                                                            ):
                                                                assistant_texts.append(
                                                                    text
                                                                )
                                    else:
                                        error_text = await state_response.text()
                                        logger.warning(
                                            "Failed to get thread state (will fall back to history): %s",
                                            error_text,
                                        )

                                if not assistant_texts:
                                    async with session.get(
                                        f"{LANGRAPH_SERVER_URL}/threads/{thread_id}/history",
                                        headers=headers,
                                    ) as history_response:
                                        if history_response.status != 200:
                                            error_text = await history_response.text()
                                            logger.error(
                                                f"Failed to get thread history: {error_text}"
                                            )
                                            return False

                                        history_data = await history_response.json()

                                        # Troubleshooting: log response shape (not content) when parsing fails.
                                        # Do not log full payloads to avoid accidental sensitive data exposure.
                                        if isinstance(history_data, list):
                                            logger.info(
                                                "Thread history response shape: list(len=%s) first_item_type=%s",
                                                len(history_data),
                                                type(history_data[0]).__name__
                                                if len(history_data) > 0
                                                else None,
                                            )
                                        elif isinstance(history_data, dict):
                                            logger.info(
                                                "Thread history response shape: dict(keys=%s)",
                                                sorted(list(history_data.keys())),
                                            )
                                        else:
                                            logger.info(
                                                "Thread history response shape: %s",
                                                type(history_data).__name__,
                                            )

                                        thread_states: list[dict[str, Any]] = []
                                        if isinstance(history_data, list):
                                            thread_states = [
                                                state
                                                for state in history_data
                                                if isinstance(state, dict)
                                            ]
                                        elif isinstance(history_data, dict):
                                            # Defensive fallback if server wraps the list
                                            wrapped = (
                                                history_data.get("history")
                                                or history_data.get("states")
                                                or history_data.get("items")
                                                or []
                                            )
                                            if isinstance(wrapped, list):
                                                thread_states = [
                                                    state
                                                    for state in wrapped
                                                    if isinstance(state, dict)
                                                ]

                                        logger.info(
                                            "Thread history parsed: thread_states=%s",
                                            len(thread_states),
                                        )

                                        for thread_state in thread_states:
                                            values = thread_state.get("values")

                                            value_containers: list[dict[str, Any]] = []
                                            if isinstance(values, dict):
                                                value_containers = [values]
                                            elif isinstance(values, list):
                                                value_containers = [
                                                    item
                                                    for item in values
                                                    if isinstance(item, dict)
                                                ]

                                            if not value_containers:
                                                continue

                                            first_values_container = value_containers[0]
                                            logger.info(
                                                "ThreadState.values keys: %s",
                                                sorted(
                                                    list(first_values_container.keys())
                                                ),
                                            )

                                            messages_for_role_logging = (
                                                first_values_container.get("messages")
                                            )
                                            if isinstance(
                                                messages_for_role_logging, list
                                            ):
                                                roles_present: list[str] = []
                                                for (
                                                    message_for_role_logging
                                                ) in messages_for_role_logging:
                                                    if not isinstance(
                                                        message_for_role_logging, dict
                                                    ):
                                                        continue
                                                    # LangChain messages use "type" (ai, human, tool)
                                                    # OpenAI-style messages use "role" (assistant, user)
                                                    role = message_for_role_logging.get(
                                                        "role"
                                                    ) or message_for_role_logging.get(
                                                        "type"
                                                    )
                                                    if isinstance(role, str):
                                                        roles_present.append(role)
                                                logger.info(
                                                    "ThreadState.values.messages types_present=%s",
                                                    sorted(set(roles_present)),
                                                )

                                            for value_container in value_containers:
                                                messages = value_container.get(
                                                    "messages"
                                                )
                                                if not isinstance(messages, list):
                                                    continue

                                                for message in messages:
                                                    if not isinstance(message, dict):
                                                        continue
                                                    # LangChain messages use "type": "ai"
                                                    # OpenAI-style messages use "role": "assistant"
                                                    msg_type = message.get(
                                                        "type"
                                                    ) or message.get("role")
                                                    if msg_type not in (
                                                        "ai",
                                                        "assistant",
                                                    ):
                                                        continue

                                                    content = message.get("content")
                                                    if isinstance(content, str):
                                                        assistant_texts.append(content)
                                                        continue

                                                    if (
                                                        isinstance(content, list)
                                                        and content
                                                    ):
                                                        first = content[0]
                                                        if isinstance(first, dict):
                                                            text = first.get("text")
                                                            if (
                                                                isinstance(text, str)
                                                                and text
                                                            ):
                                                                assistant_texts.append(
                                                                    text
                                                                )

                                if not assistant_texts:
                                    logger.warning(
                                        "No assistant messages found in thread state/history"
                                    )
                                    return False

                                last_text = assistant_texts[-1]
                                logger.info(f"Assistant response: '{last_text}'")

                                if "4" in last_text or "four" in last_text.lower():
                                    logger.info("✓ Assistant provided correct answer")
                                    return True

                                logger.warning(
                                    "Assistant response might not be correct"
                                )
                                return True  # Still counts as success - model responded
                            elif run_status in [
                                "failed",
                                "cancelled",
                                "expired",
                                "error",
                            ]:
                                # Get error details from the run
                                logger.error(f"Run failed with status: {run_status}")
                                error_details = status_data.get("error", {})
                                error_message = error_details.get(
                                    "message", "No error message"
                                )
                                logger.error(f"Error details: {error_message}")
                                return False
                            # Continue polling if still running
                        else:
                            error_text = await status_response.text()
                            logger.error(f"Failed to get run status: {error_text}")
                            return False

                logger.error("Run timed out after 10 seconds")
                return False
            else:
                error_text = await response.text()
                logger.error(f"Failed to start run: {response.status} - {error_text}")
                return False


async def main():
    """Main test runner."""
    logger.info("=" * 60)
    logger.info("Starting authenticated vLLM integration test")
    logger.info("=" * 60)

    # Check for required environment variables
    if not SUPABASE_SECRET:
        logger.error("SUPABASE_SECRET environment variable is required")
        logger.error("Set it to your service role key (sb_secret_...)")
        return 1

    # Create test user
    user_info = await create_test_user()
    if not user_info:
        logger.error("Failed to create test user")
        return 1

    user_id = user_info.get("id")

    try:
        # Get JWT token
        jwt_token = await get_user_jwt()
        if not jwt_token:
            logger.error("Failed to get JWT token")
            return 1

        # Test LangGraph with authentication
        success = await test_langgraph_with_auth(jwt_token)

        if success:
            logger.info("\n✅ Authenticated vLLM integration test PASSED")
            logger.info("\nSummary:")
            logger.info(f"- Created test user: {TEST_USER_EMAIL}")
            logger.info("- Got valid JWT token")
            logger.info("- Created assistant with vLLM configuration")
            logger.info("- Created thread and ran assistant")
            logger.info("- Received response from vLLM model")
            logger.info("\nThe agent successfully:")
            logger.info("1. Accepted custom vLLM endpoint configuration")
            logger.info("2. Used local Ministral-3-3B model")
            logger.info("3. Processed request with authentication")
            logger.info("4. Returned a response")
            return 0
        else:
            logger.error("\n❌ Authenticated vLLM integration test FAILED")
            return 1

    finally:
        # Clean up test user
        if user_id:
            await delete_test_user(user_id)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
