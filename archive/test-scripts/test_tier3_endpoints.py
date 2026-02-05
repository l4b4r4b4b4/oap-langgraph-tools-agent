#!/usr/bin/env python3
"""Tier 3 endpoint validation test for Robyn server.

Tests metrics, info, and store API endpoints.

Usage:
    uv run python test_tier3_endpoints.py

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

TEST_USER_EMAIL = "tier3-test@example.com"
TEST_USER_PASSWORD = "tier3-test-password-123!"


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


async def test_tier3_endpoints():
    """Test Tier 3 endpoints."""
    print("\n" + "=" * 60)
    print("🧪 Tier 3 Endpoint Validation Test")
    print("=" * 60)

    results: dict[str, bool] = {}

    async with aiohttp.ClientSession() as session:
        # ================================================================
        # Test 1: GET /metrics (Public - no auth required)
        # ================================================================
        print("\n📊 Testing GET /metrics (Prometheus format)...")
        async with session.get(f"{ROBYN_URL}/metrics") as response:
            if response.status == 200:
                content = await response.text()
                has_prometheus_format = "# HELP" in content and "# TYPE" in content
                has_uptime = "robyn_uptime_seconds" in content
                has_storage = "robyn_assistants_total" in content
                print(f"   ✅ Prometheus format: {has_prometheus_format}")
                print(f"   ✅ Has uptime metric: {has_uptime}")
                print(f"   ✅ Has storage metrics: {has_storage}")
                results["metrics_prometheus"] = has_prometheus_format
            else:
                error = await response.text()
                print(f"   ❌ Failed: {response.status} - {error}")
                results["metrics_prometheus"] = False

        # ================================================================
        # Test 2: GET /metrics/json (Public - no auth required)
        # ================================================================
        print("\n📊 Testing GET /metrics/json...")
        async with session.get(f"{ROBYN_URL}/metrics/json") as response:
            if response.status == 200:
                data = await response.json()
                has_uptime = "uptime_seconds" in data
                has_storage = "storage" in data
                has_agent = "agent" in data
                print(f"   ✅ Has uptime: {has_uptime}")
                print(f"   ✅ Has storage: {has_storage}")
                print(f"   ✅ Has agent metrics: {has_agent}")
                results["metrics_json"] = has_uptime and has_storage
            else:
                error = await response.text()
                print(f"   ❌ Failed: {response.status} - {error}")
                results["metrics_json"] = False

        # ================================================================
        # Test 3: GET /info (Enhanced with capabilities)
        # ================================================================
        print("\n📋 Testing GET /info (enhanced)...")
        async with session.get(f"{ROBYN_URL}/info") as response:
            if response.status == 200:
                data = await response.json()
                has_capabilities = "capabilities" in data
                has_build = "build" in data
                has_graphs = "graphs" in data
                has_tiers = "tiers" in data
                print(f"   ✅ Has capabilities: {has_capabilities}")
                print(f"   ✅ Has build info: {has_build}")
                print(f"   ✅ Has graphs: {has_graphs}")
                print(f"   ✅ Has tier status: {has_tiers}")
                if has_capabilities:
                    caps = data["capabilities"]
                    print(f"      Streaming: {caps.get('streaming')}")
                    print(f"      Store: {caps.get('store')}")
                    print(f"      Metrics: {caps.get('metrics')}")
                results["info_enhanced"] = has_capabilities and has_build
            else:
                error = await response.text()
                print(f"   ❌ Failed: {response.status} - {error}")
                results["info_enhanced"] = False

    # Now test Store API (requires authentication)
    user_info = await create_test_user()
    if not user_info:
        print("\n⚠️ Skipping Store API tests (no user)")
        results["store_put"] = False
        results["store_get"] = False
        results["store_search"] = False
        results["store_delete"] = False
    else:
        jwt = await get_user_jwt()
        if not jwt:
            print("\n⚠️ Skipping Store API tests (no JWT)")
            results["store_put"] = False
            results["store_get"] = False
            results["store_search"] = False
            results["store_delete"] = False
        else:
            print("\n✅ Authentication successful for Store API tests")

            headers = {
                "Authorization": f"Bearer {jwt}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                # ================================================================
                # Test 4: PUT /store/items
                # ================================================================
                print("\n💾 Testing PUT /store/items...")
                async with session.put(
                    f"{ROBYN_URL}/store/items",
                    headers=headers,
                    json={
                        "namespace": "test_namespace",
                        "key": "test_key",
                        "value": {"data": "hello world", "count": 42},
                        "metadata": {"test": True},
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        has_namespace = data.get("namespace") == "test_namespace"
                        has_key = data.get("key") == "test_key"
                        has_value = data.get("value", {}).get("data") == "hello world"
                        print(f"   ✅ Namespace correct: {has_namespace}")
                        print(f"   ✅ Key correct: {has_key}")
                        print(f"   ✅ Value correct: {has_value}")
                        results["store_put"] = has_namespace and has_key and has_value
                    else:
                        error = await response.text()
                        print(f"   ❌ Failed: {response.status} - {error}")
                        results["store_put"] = False

                # ================================================================
                # Test 5: GET /store/items
                # ================================================================
                print("\n📖 Testing GET /store/items...")
                async with session.get(
                    f"{ROBYN_URL}/store/items?namespace=test_namespace&key=test_key",
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        has_value = data.get("value", {}).get("count") == 42
                        print(f"   ✅ Retrieved value correctly: {has_value}")
                        results["store_get"] = has_value
                    else:
                        error = await response.text()
                        print(f"   ❌ Failed: {response.status} - {error}")
                        results["store_get"] = False

                # ================================================================
                # Test 6: POST /store/items/search
                # ================================================================
                print("\n🔍 Testing POST /store/items/search...")
                # First add another item
                await session.put(
                    f"{ROBYN_URL}/store/items",
                    headers=headers,
                    json={
                        "namespace": "test_namespace",
                        "key": "test_key_2",
                        "value": {"data": "second item"},
                    },
                )

                async with session.post(
                    f"{ROBYN_URL}/store/items/search",
                    headers=headers,
                    json={
                        "namespace": "test_namespace",
                        "prefix": "test_",
                        "limit": 10,
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        count = len(data) if isinstance(data, list) else 0
                        print(f"   ✅ Found {count} items with prefix 'test_'")
                        results["store_search"] = count >= 2
                    else:
                        error = await response.text()
                        print(f"   ❌ Failed: {response.status} - {error}")
                        results["store_search"] = False

                # ================================================================
                # Test 7: GET /store/namespaces
                # ================================================================
                print("\n📂 Testing GET /store/namespaces...")
                async with session.get(
                    f"{ROBYN_URL}/store/namespaces",
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        has_test_namespace = "test_namespace" in data
                        print(f"   ✅ Found test_namespace: {has_test_namespace}")
                        results["store_namespaces"] = has_test_namespace
                    else:
                        error = await response.text()
                        print(f"   ❌ Failed: {response.status} - {error}")
                        results["store_namespaces"] = False

                # ================================================================
                # Test 8: DELETE /store/items
                # ================================================================
                print("\n🗑️  Testing DELETE /store/items...")
                async with session.delete(
                    f"{ROBYN_URL}/store/items?namespace=test_namespace&key=test_key",
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        # Verify item is deleted
                        async with session.get(
                            f"{ROBYN_URL}/store/items?namespace=test_namespace&key=test_key",
                            headers=headers,
                        ) as verify_response:
                            deleted = verify_response.status == 404
                            print(f"   ✅ Item deleted: {deleted}")
                            results["store_delete"] = deleted
                    else:
                        error = await response.text()
                        print(f"   ❌ Failed: {response.status} - {error}")
                        results["store_delete"] = False

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
        print("\n✅ All Tier 3 endpoints validated successfully!")
        return True
    else:
        print("\n⚠️ Some tests failed")
        return False


async def main():
    """Main entry point."""
    try:
        success = await test_tier3_endpoints()
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
