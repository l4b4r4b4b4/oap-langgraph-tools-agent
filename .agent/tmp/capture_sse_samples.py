#!/usr/bin/env python3
"""
Capture SSE (Server-Sent Events) samples from langgraph dev streaming endpoints.

This script:
1. Creates a test user and gets a JWT token
2. Creates an assistant and thread
3. Captures raw SSE output from:
   - POST /threads/{thread_id}/runs/stream (stateful)
   - POST /runs/stream (stateless)
4. Saves the raw SSE frames to files for reference

The captured output is used as the reference for implementing SSE
streaming in the Robyn runtime server.
"""

import os
import sys
import asyncio
import aiohttp
import uuid
import json
from datetime import datetime
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("\"'")
    except FileNotFoundError:
        pass

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SECRET = os.getenv("SUPABASE_SECRET")
LANGRAPH_SERVER_URL = os.getenv("LANGRAPH_SERVER_URL", "http://localhost:2024")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:7374/v1")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "ministral-3b-instruct")

# Output directory for captured samples
OUTPUT_DIR = Path(__file__).parent


def log(msg: str):
    """Simple logging with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


async def create_test_user() -> tuple[str | None, str | None]:
    """Create a test user and return (user_id, email)."""
    if not SUPABASE_SECRET:
        log("ERROR: SUPABASE_SECRET not set")
        return None, None

    email = f"sse_capture_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    headers = {
        "apikey": SUPABASE_SECRET,
        "Authorization": f"Bearer {SUPABASE_SECRET}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers,
            json={"email": email, "password": password, "email_confirm": True},
        ) as response:
            if response.status == 200:
                data = await response.json()
                log(f"Created test user: {email}")
                return data.get("id"), email
            else:
                log(f"Failed to create user: {await response.text()}")
                return None, None


async def get_jwt(email: str, password: str = "TestPassword123!") -> str | None:
    """Get JWT token for user."""
    headers = {"apikey": SUPABASE_SECRET, "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers=headers,
            json={"email": email, "password": password},
        ) as response:
            if response.status == 200:
                data = await response.json()
                log("Got JWT token")
                return data.get("access_token")
            else:
                log(f"Failed to get JWT: {await response.text()}")
                return None


async def delete_user(user_id: str):
    """Clean up test user."""
    headers = {
        "apikey": SUPABASE_SECRET,
        "Authorization": f"Bearer {SUPABASE_SECRET}",
    }
    async with aiohttp.ClientSession() as session:
        await session.delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}", headers=headers
        )
        log(f"Deleted test user: {user_id}")


async def create_assistant(jwt: str) -> str | None:
    """Create an assistant and return its ID."""
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}

    assistant_data = {
        "graph_id": "agent",
        "name": "SSE Capture Assistant",
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

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{LANGRAPH_SERVER_URL}/assistants",
            headers=headers,
            json=assistant_data,
        ) as response:
            if response.status == 200:
                data = await response.json()
                assistant_id = data.get("assistant_id")
                log(f"Created assistant: {assistant_id}")
                return assistant_id
            else:
                log(f"Failed to create assistant: {await response.text()}")
                return None


async def create_thread(jwt: str) -> str | None:
    """Create a thread and return its ID."""
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{LANGRAPH_SERVER_URL}/threads",
            headers=headers,
            json={},
        ) as response:
            if response.status == 200:
                data = await response.json()
                thread_id = data.get("thread_id")
                log(f"Created thread: {thread_id}")
                return thread_id
            else:
                log(f"Failed to create thread: {await response.text()}")
                return None


async def capture_stateful_stream(jwt: str, assistant_id: str, thread_id: str) -> str:
    """
    Capture SSE from POST /threads/{thread_id}/runs/stream

    Returns the raw SSE output as a string.
    """
    log(f"Capturing stateful stream: POST /threads/{thread_id}/runs/stream")

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

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
        "stream_mode": ["values", "messages", "updates"],
    }

    raw_sse = []

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{LANGRAPH_SERVER_URL}/threads/{thread_id}/runs/stream",
            headers=headers,
            json=run_data,
        ) as response:
            log(f"Response status: {response.status}")
            log(f"Response headers: {dict(response.headers)}")

            if response.status != 200:
                error = await response.text()
                log(f"Error: {error}")
                return f"ERROR: {response.status}\n{error}"

            # Read the raw SSE stream
            async for line in response.content:
                decoded = line.decode("utf-8")
                raw_sse.append(decoded)
                # Print progress (truncated)
                if decoded.strip():
                    preview = decoded[:80] + "..." if len(decoded) > 80 else decoded
                    print(f"  SSE: {preview.strip()}")

    return "".join(raw_sse)


async def capture_stateless_stream(jwt: str, assistant_id: str) -> str:
    """
    Capture SSE from POST /runs/stream (stateless)

    Returns the raw SSE output as a string.
    """
    log("Capturing stateless stream: POST /runs/stream")

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    run_data = {
        "assistant_id": assistant_id,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "What is 3 + 3? Answer with just the number.",
                }
            ]
        },
        "stream_mode": ["values", "messages", "updates"],
    }

    raw_sse = []

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{LANGRAPH_SERVER_URL}/runs/stream",
            headers=headers,
            json=run_data,
        ) as response:
            log(f"Response status: {response.status}")
            log(f"Response headers: {dict(response.headers)}")

            if response.status != 200:
                error = await response.text()
                log(f"Error: {error}")
                return f"ERROR: {response.status}\n{error}"

            # Read the raw SSE stream
            async for line in response.content:
                decoded = line.decode("utf-8")
                raw_sse.append(decoded)
                # Print progress (truncated)
                if decoded.strip():
                    preview = decoded[:80] + "..." if len(decoded) > 80 else decoded
                    print(f"  SSE: {preview.strip()}")

    return "".join(raw_sse)


def save_sample(filename: str, content: str):
    """Save SSE sample to file."""
    filepath = OUTPUT_DIR / filename
    filepath.write_text(content)
    log(f"Saved: {filepath}")


async def main():
    log("=" * 60)
    log("SSE Capture Script for LangGraph Runtime Parity")
    log("=" * 60)

    # Create test user
    user_id, email = await create_test_user()
    if not user_id:
        log("Failed to create test user")
        return 1

    try:
        # Get JWT
        jwt = await get_jwt(email)
        if not jwt:
            log("Failed to get JWT")
            return 1

        # Create assistant
        assistant_id = await create_assistant(jwt)
        if not assistant_id:
            log("Failed to create assistant")
            return 1

        # Create thread for stateful stream
        thread_id = await create_thread(jwt)
        if not thread_id:
            log("Failed to create thread")
            return 1

        # Capture stateful stream
        log("")
        log("-" * 40)
        stateful_sse = await capture_stateful_stream(jwt, assistant_id, thread_id)
        save_sample("sse_stateful_runs_stream.txt", stateful_sse)

        # Capture stateless stream
        log("")
        log("-" * 40)
        stateless_sse = await capture_stateless_stream(jwt, assistant_id)
        save_sample("sse_stateless_runs_stream.txt", stateless_sse)

        log("")
        log("=" * 60)
        log("SSE capture complete!")
        log(f"Samples saved to: {OUTPUT_DIR}")
        log("=" * 60)

        return 0

    finally:
        # Clean up
        await delete_user(user_id)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
