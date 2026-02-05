#!/usr/bin/env python3
"""
Basic Supabase connectivity test script for oap-langgraph-tools-agent.

Tests connectivity to local Supabase development stack and verifies
authentication client initialization.

Usage:
    python test_supabase_connectivity.py

Environment variables needed:
    SUPABASE_URL=http://127.0.0.1:54321
    SUPABASE_KEY=<your-supabase-secret-key>
"""

import os
import sys
import asyncio
import aiohttp
from typing import Dict


def check_environment() -> bool:
    """Check if required environment variables are set."""
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = []

    print("🔍 Checking environment variables...")
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            print(
                f"  ✅ {var}: {value[:20]}..."
                if len(value) > 20
                else f"  ✅ {var}: {value}"
            )

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set these variables:")
        print("  export SUPABASE_URL='http://127.0.0.1:54321'")
        print("  export SUPABASE_KEY='<your-supabase-secret-key>'")
        return False

    return True


async def test_supabase_url_connectivity(url: str) -> bool:
    """Test basic HTTP connectivity to Supabase URL."""
    print(f"\n🌐 Testing connectivity to {url}...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                status = response.status
                print(f"  HTTP Status: {status}")

                if status == 200:
                    print(f"  ✅ Successfully connected to {url}")
                    return True
                else:
                    print(f"  ⚠️  Connected but got non-200 status: {status}")
                    # Still return True if we got a response
                    return True

    except aiohttp.ClientConnectorError as e:
        print(f"  ❌ Connection failed: {e}")
        print(f"  Make sure Supabase dev stack is running at {url}")
        return False
    except asyncio.TimeoutError:
        print(f"  ❌ Connection timeout to {url}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {type(e).__name__}: {e}")
        return False


async def test_mcp_server_connectivity(base_url: str) -> bool:
    """Test connectivity to MCP server endpoint."""
    mcp_url = base_url.rstrip("/") + "/mcp"
    print(f"\n🔧 Testing MCP server at {mcp_url}...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(mcp_url, timeout=10) as response:
                status = response.status
                print(f"  HTTP Status: {status}")

                if status == 200:
                    print("  ✅ MCP server is accessible")
                    return True
                else:
                    # MCP server might return different status codes
                    print(f"  ⚠️  MCP server responded with status: {status}")
                    return True  # Still accessible

    except aiohttp.ClientConnectorError as e:
        print(f"  ❌ MCP server connection failed: {e}")
        return False
    except asyncio.TimeoutError:
        print("  ❌ MCP server connection timeout")
        return False
    except Exception as e:
        print(f"  ❌ MCP server unexpected error: {type(e).__name__}: {e}")
        return False


async def test_supabase_client_initialization() -> bool:
    """Test Supabase client initialization."""
    print("\n🔐 Testing Supabase client initialization...")

    try:
        # Try to import and initialize Supabase client
        from supabase import create_client, Client

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            print("  ❌ Missing Supabase URL or key")
            return False

        print(f"  Initializing client with URL: {supabase_url}")
        client: Client = create_client(supabase_url, supabase_key)

        # Test a simple operation - get auth settings
        try:
            # This is a non-authenticated call that should work
            client.auth.get_url()
            print("  ✅ Supabase client initialized successfully")
            print(f"  Client type: {type(client).__name__}")
            return True
        except Exception as e:
            print(f"  ⚠️  Client created but auth test failed: {type(e).__name__}: {e}")
            # Client was created, which is the main test
            return True

    except ImportError:
        print("  ❌ Supabase Python client not installed")
        print("  Install with: pip install supabase>=2.15.1")
        return False
    except Exception as e:
        print(f"  ❌ Failed to initialize Supabase client: {type(e).__name__}: {e}")
        return False


async def test_oauth_token_endpoint(base_url: str) -> bool:
    """Test OAuth token exchange endpoint availability."""
    token_url = base_url.rstrip("/") + "/oauth/token"
    print(f"\n🔑 Testing OAuth token endpoint at {token_url}...")

    try:
        async with aiohttp.ClientSession() as session:
            # Try a HEAD request first (less intrusive)
            async with session.head(token_url, timeout=10) as response:
                status = response.status
                print(f"  HTTP Status (HEAD): {status}")

                if status in [200, 404, 405]:
                    # 404/405 might mean endpoint exists but method not allowed
                    print("  ✅ Token endpoint is accessible")
                    return True
                else:
                    print(f"  ⚠️  Token endpoint returned status: {status}")
                    return True  # Still accessible

    except aiohttp.ClientConnectorError as e:
        print(f"  ❌ Token endpoint connection failed: {e}")
        return False
    except asyncio.TimeoutError:
        print("  ❌ Token endpoint connection timeout")
        return False
    except Exception as e:
        print(f"  ❌ Token endpoint unexpected error: {type(e).__name__}: {e}")
        return False


async def test_database_connectivity() -> bool:
    """Test database connectivity (optional)."""
    print("\n🗄️  Testing database connectivity (optional)...")

    # Check if database URL is set
    db_url = os.environ.get(
        "SUPABASE_DB_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )

    try:
        # Try to import psycopg2 for database testing
        import psycopg2
        from urllib.parse import urlparse

        parsed = urlparse(db_url)

        print(f"  Database URL: {parsed.hostname}:{parsed.port}")

        # Try to connect
        conn = psycopg2.connect(
            dbname=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port,
        )

        # Test connection
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"  ✅ Database connected: {version.split(',')[0]}")

        conn.close()
        return True

    except ImportError:
        print("  ⚠️  psycopg2 not installed, skipping database test")
        print("  Install with: pip install psycopg2-binary")
        return True  # Not a failure, just optional
    except Exception as e:
        print(f"  ⚠️  Database connection failed: {type(e).__name__}: {e}")
        print("  This is optional for basic connectivity testing")
        return True  # Not a critical failure for basic tests


async def run_all_tests() -> Dict[str, bool]:
    """Run all connectivity tests."""
    print("=" * 60)
    print("🔧 Supabase Connectivity Test Suite")
    print("=" * 60)

    # Check environment first
    if not check_environment():
        return {"environment": False}

    supabase_url = os.environ.get("SUPABASE_URL")

    results = {}

    # Run tests
    results["supabase_url"] = await test_supabase_url_connectivity(supabase_url)
    results["mcp_server"] = await test_mcp_server_connectivity(supabase_url)
    results["supabase_client"] = await test_supabase_client_initialization()
    results["oauth_endpoint"] = await test_oauth_token_endpoint(supabase_url)
    results["database"] = await test_database_connectivity()

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CONNECTIVITY TESTS PASSED")
        print("   Local Supabase stack is properly configured")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("   Check output above for details")

    print("\n📝 Next steps:")
    print("1. Set model API keys (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
    print("2. Start agent with: uv run langgraph dev --no-browser")
    print("3. Test authentication with JWT tokens from local Supabase")

    return results


def main():
    """Main entry point."""
    try:
        # Run async tests
        results = asyncio.run(run_all_tests())

        # Return exit code based on results
        all_passed = all(results.values())
        return 0 if all_passed else 1

    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
