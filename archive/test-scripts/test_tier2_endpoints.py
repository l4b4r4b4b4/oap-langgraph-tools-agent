#!/usr/bin/env python3
"""Tier 2 endpoint validation test for Robyn server.

Tests search, count, list, and stream join endpoints.

Usage:
    uv run python test_tier2_endpoints.py

Prerequisites:
    - Robyn server running on localhost:8081
    - Supabase running on localhost:54321
"""

import asyncio
import os
from typing import Any

import aiohttp
from dotenv import load_dotenv

load_dotenv()

# Configuration
ROBYN_URL = os.getenv("ROBYN_URL", "http://127.0.0.1:8081")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SECRET = os.getenv("SUPABASE_SECRET", "")

TEST_USER_EMAIL = "tier2-test@example.com"
TEST_USER_PASSWORD = "tier2-test-password-123!"


async def create_test_user() -> dict[str, Any] | None:
    """Create a test user using Supabase admin API."""
    if not SUPABASE_SECRET:
        print("❌ SUPABASE_SECRET not set in environment")
        return None

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
                return await response.json()
            else:
                error_text = await response.text()
                if "already been registered" in error_text:
                    return {"id": "existing"}
                print(f"❌ Failed to create user: {response.status}")
                return None


async def get_user_jwt() -> str | None:
    """Get JWT token for the test user."""
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
                return auth_data.get("access_token")
            return None


async def test_tier2_endpoints():
    """Test Tier 2 endpoints."""
    print("\n" + "=" * 60)
    print("🧪 Tier 2 Endpoint Validation Test")
    print("=" * 60)

    # Setup
    user_info = await create_test_user()
    if not user_info:
        return False

    jwt = await get_user_jwt()
    if not jwt:
        print("❌ Failed to get JWT")
        return False

    print("✅ Authentication successful")

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    results: dict[str, bool] = {}

    async with aiohttp.ClientSession() as session:
        # Create test data first
        print("\n📋 Creating test data...")

        # Create assistants
        for i in range(3):
            await session.post(
                f"{ROBYN_URL}/assistants",
                headers=headers,
                json={
                    "graph_id": "agent",
                    "name": f"Tier2 Test Assistant {i}",
                    "metadata": {"test_group": "tier2", "index": i},
                },
            )

        # Create threads
        thread_ids = []
        for i in range(3):
            async with session.post(
                f"{ROBYN_URL}/threads",
                headers=headers,
                json={"metadata": {"test_group": "tier2", "index": i}},
            ) as response:
                if response.status == 200:
                    thread = await response.json()
                    thread_ids.append(thread.get("thread_id"))

        print(f"   Created 3 assistants and {len(thread_ids)} threads")

        # ================================================================
        # Test 1: POST /assistants/search
        # ================================================================
        print("\n🔍 Testing POST /assistants/search...")
        async with session.post(
            f"{ROBYN_URL}/assistants/search",
            headers=headers,
            json={"graph_id": "agent", "limit": 10},
        ) as response:
            if response.status == 200:
                data = await response.json()
                count = len(data) if isinstance(data, list) else 0
                print(f"   ✅ Found {count} assistants")
                results["assistants_search"] = True
            else:
                error = await response.text()
                print(f"   ❌ Failed: {response.status} - {error}")
                results["assistants_search"] = False

        # ================================================================
        # Test 2: POST /assistants/count
        # ================================================================
        print("\n🔢 Testing POST /assistants/count...")
        async with session.post(
            f"{ROBYN_URL}/assistants/count",
            headers=headers,
            json={"graph_id": "agent"},
        ) as response:
            if response.status == 200:
                data = await response.json()
                count = data.get("count", data) if isinstance(data, dict) else data
                print(f"   ✅ Count: {count}")
                results["assistants_count"] = True
            else:
                error = await response.text()
                print(f"   ❌ Failed: {response.status} - {error}")
                results["assistants_count"] = False

        # ================================================================
        # Test 3: POST /threads/search
        # ================================================================
        print("\n🔍 Testing POST /threads/search...")
        async with session.post(
            f"{ROBYN_URL}/threads/search",
            headers=headers,
            json={"limit": 10},
        ) as response:
            if response.status == 200:
                data = await response.json()
                count = len(data) if isinstance(data, list) else 0
                print(f"   ✅ Found {count} threads")
                results["threads_search"] = True
            else:
                error = await response.text()
                print(f"   ❌ Failed: {response.status} - {error}")
                results["threads_search"] = False

        # ================================================================
        # Test 4: POST /threads/count
        # ================================================================
        print("\n🔢 Testing POST /threads/count...")
        async with session.post(
            f"{ROBYN_URL}/threads/count",
            headers=headers,
            json={},
        ) as response:
            if response.status == 200:
                data = await response.json()
                count = data.get("count", data) if isinstance(data, dict) else data
                print(f"   ✅ Count: {count}")
                results["threads_count"] = True
            else:
                error = await response.text()
                print(f"   ❌ Failed: {response.status} - {error}")
                results["threads_count"] = False

        # ================================================================
        # Test 5: GET /threads/{thread_id}/runs (list runs)
        # ================================================================
        print("\n📋 Testing GET /threads/{thread_id}/runs...")
        if thread_ids:
            test_thread_id = thread_ids[0]
            async with session.get(
                f"{ROBYN_URL}/threads/{test_thread_id}/runs",
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    count = len(data) if isinstance(data, list) else 0
                    print(f"   ✅ Found {count} runs for thread")
                    results["list_runs"] = True
                else:
                    error = await response.text()
                    print(f"   ❌ Failed: {response.status} - {error}")
                    results["list_runs"] = False
        else:
            print("   ⚠️ No threads available to test")
            results["list_runs"] = False

        # ================================================================
        # Test 6: GET /threads/{thread_id}/stream (thread stream)
        # ================================================================
        print("\n🌊 Testing GET /threads/{thread_id}/stream...")
        if thread_ids:
            test_thread_id = thread_ids[0]
            async with session.get(
                f"{ROBYN_URL}/threads/{test_thread_id}/stream",
                headers=headers,
            ) as response:
                if response.status == 200:
                    content = await response.text()
                    has_events = "event:" in content
                    print(f"   ✅ SSE stream received (has events: {has_events})")
                    results["thread_stream"] = True
                else:
                    error = await response.text()
                    print(f"   ❌ Failed: {response.status} - {error}")
                    results["thread_stream"] = False
        else:
            print("   ⚠️ No threads available to test")
            results["thread_stream"] = False

    # ================================================================
    # Summary
    # ================================================================
    print("\n" + "=" * 60)
    print("📊 Results Summary")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✅" if passed_test else "❌"
        print(f"   {status} {test_name}")

    print(f"\n   {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All Tier 2 endpoints validated successfully!")
        return True
    else:
        print("\n⚠️ Some tests failed")
        return False


async def main():
    """Main entry point."""
    try:
        success = await test_tier2_endpoints()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
