#!/usr/bin/env python3
"""Manual integration test for Robyn server.

Tests the full flow: create user -> get JWT -> create assistant -> create thread -> stream run

Usage:
    uv run python test_robyn_manual.py

Prerequisites:
    - Robyn server running on localhost:8081
    - Supabase running on localhost:54321
    - vLLM running (default: localhost:8001, override with VLLM_BASE_URL env var)
"""

import asyncio
import os
import sys
from typing import Any

import aiohttp
from dotenv import load_dotenv

load_dotenv()

# Enable debug mode
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")

# Configuration
ROBYN_URL = os.getenv("ROBYN_URL", "http://127.0.0.1:8081")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SECRET = os.getenv("SUPABASE_SECRET", "")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "ministral-3b-instruct")

TEST_USER_EMAIL = "robyn-test@example.com"
TEST_USER_PASSWORD = "robyn-test-password-123!"


async def create_test_user() -> dict[str, Any] | None:
    """Create a test user using Supabase admin API."""
    if not SUPABASE_SECRET:
        print("❌ SUPABASE_SECRET not set in environment")
        return None

    print(f"📝 Creating test user: {TEST_USER_EMAIL}")

    headers = {
        "apikey": SUPABASE_SECRET,
        "Authorization": f"Bearer {SUPABASE_SECRET}",
        "Content-Type": "application/json",
    }

    user_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "email_confirm": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers,
            json=user_data,
        ) as response:
            if response.status == 200:
                user_info = await response.json()
                print(f"✅ Created user: {user_info.get('id')}")
                return user_info
            else:
                error_text = await response.text()
                # User might already exist
                if "already been registered" in error_text:
                    print("ℹ️  User already exists, continuing...")
                    return {"id": "existing"}
                print(f"❌ Failed to create user: {response.status} - {error_text}")
                return None


async def get_user_jwt() -> str | None:
    """Get JWT token for the test user."""
    print(f"🔑 Getting JWT for {TEST_USER_EMAIL}")

    headers = {
        "apikey": SUPABASE_SECRET,
        "Content-Type": "application/json",
    }

    signin_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers=headers,
            json=signin_data,
        ) as response:
            if response.status == 200:
                auth_data = await response.json()
                access_token = auth_data.get("access_token")
                if access_token:
                    print("✅ Got JWT token")
                    if DEBUG:
                        print(f"   Token (first 50 chars): {access_token[:50]}...")
                    return access_token
            error_text = await response.text()
            print(f"❌ Failed to get JWT: {response.status} - {error_text}")
            return None


async def delete_test_user(user_id: str) -> bool:
    """Delete the test user."""
    if not user_id or user_id == "existing":
        return True

    print(f"🗑️  Deleting test user: {user_id}")

    headers = {
        "apikey": SUPABASE_SECRET,
        "Authorization": f"Bearer {SUPABASE_SECRET}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers=headers,
        ) as response:
            if response.status in (200, 204):
                print("✅ Deleted test user")
                return True
            print(f"⚠️  Failed to delete user: {response.status}")
            return False


async def test_robyn_flow():
    """Run the full test flow against Robyn server."""
    print("\n" + "=" * 60)
    print("🚀 Robyn Server Manual Integration Test")
    print("=" * 60)

    # Check Robyn is up
    print(f"\n📡 Checking Robyn server at {ROBYN_URL}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{ROBYN_URL}/ok") as response:
                if response.status != 200:
                    print(f"❌ Robyn not responding: {response.status}")
                    return False
                data = await response.json()
                print(f"✅ Robyn is up: {data}")
        except aiohttp.ClientError as e:
            print(f"❌ Cannot connect to Robyn: {e}")
            return False

    # Create user and get JWT
    user_info = await create_test_user()
    if not user_info:
        return False

    user_id = user_info.get("id")

    jwt = await get_user_jwt()
    if not jwt:
        await delete_test_user(user_id)
        return False

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            # 1. Create Assistant
            print("\n📋 Creating assistant...")
            assistant_data = {
                "graph_id": "agent",
                "name": "Robyn Test Assistant",
                "config": {
                    "configurable": {
                        "model_name": "custom:",
                        "base_url": VLLM_BASE_URL,
                        "custom_model_name": VLLM_MODEL_NAME,
                        "temperature": 0.1,
                        "max_tokens": 100,
                        "system_prompt": "You are a helpful assistant. Answer concisely.",
                    }
                },
            }

            if DEBUG:
                print(f"   Headers: Authorization: Bearer {jwt[:30]}...")
                print(f"   URL: {ROBYN_URL}/assistants")

            async with session.post(
                f"{ROBYN_URL}/assistants",
                headers=headers,
                json=assistant_data,
            ) as response:
                if response.status not in (200, 201):
                    error = await response.text()
                    print(f"❌ Failed to create assistant: {response.status} - {error}")
                    if DEBUG:
                        print(f"   Response headers: {dict(response.headers)}")
                    return False
                assistant = await response.json()
                assistant_id = assistant.get("assistant_id")
                print(f"✅ Created assistant: {assistant_id}")

            # 2. Create Thread
            print("\n🧵 Creating thread...")
            async with session.post(
                f"{ROBYN_URL}/threads",
                headers=headers,
                json={},
            ) as response:
                if response.status not in (200, 201):
                    error = await response.text()
                    print(f"❌ Failed to create thread: {response.status} - {error}")
                    return False
                thread = await response.json()
                thread_id = thread.get("thread_id")
                print(f"✅ Created thread: {thread_id}")

            # 3. Stream a Run
            print("\n🌊 Streaming run...")
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

            print(f"   POST {ROBYN_URL}/threads/{thread_id}/runs/stream")
            print(f"   Input: {run_data['input']['messages'][0]['content']}")
            print("\n   --- SSE Events ---")

            async with session.post(
                f"{ROBYN_URL}/threads/{thread_id}/runs/stream",
                headers=headers,
                json=run_data,
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    print(f"❌ Failed to stream: {response.status} - {error}")
                    return False

                # Read SSE stream
                event_count = 0
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line:
                        # Truncate long lines for readability
                        display_line = line[:120] + "..." if len(line) > 120 else line
                        print(f"   {display_line}")
                        if line.startswith("event:"):
                            event_count += 1

                print(f"\n   --- End SSE ({event_count} events) ---")

            # 4. Get Thread State
            print("\n📊 Getting thread state...")
            async with session.get(
                f"{ROBYN_URL}/threads/{thread_id}/state",
                headers=headers,
            ) as response:
                if response.status == 200:
                    state = await response.json()
                    values = state.get("values", {})
                    messages = values.get("messages", [])
                    print(f"✅ Thread has {len(messages)} messages")
                    for msg in messages:
                        msg_type = msg.get("type", "unknown")
                        content = msg.get("content", "")[:80]
                        print(f"   [{msg_type}] {content}")
                else:
                    error = await response.text()
                    print(f"⚠️  Failed to get state: {response.status} - {error}")

            print("\n" + "=" * 60)
            print("✅ Test completed successfully!")
            print("=" * 60)
            return True

    finally:
        # Cleanup
        if user_id and user_id != "existing":
            await delete_test_user(user_id)


async def main():
    """Main entry point."""
    try:
        success = await test_robyn_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
