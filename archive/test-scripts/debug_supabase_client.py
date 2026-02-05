#!/usr/bin/env python3
"""
Detailed Supabase client debugging script.
Tests the Supabase Python client with local development stack.
"""

import os
import sys
import asyncio
import aiohttp


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"🔍 {text}")
    print("=" * 60)


def test_supabase_import():
    """Test Supabase library import and version."""
    print_header("Supabase Library Import Test")

    try:
        import supabase

        print("✅ Supabase module imported successfully")
        print(f"   Module location: {supabase.__file__}")

        # Try to get version
        try:
            import pkg_resources

            version = pkg_resources.get_distribution("supabase").version
            print(f"   Version: {version}")
        except:
            print("   Version: Unknown")

        return True
    except ImportError as e:
        print(f"❌ Failed to import supabase: {e}")
        print("\nInstall with:")
        print("  pip install supabase>=2.15.1")
        print("  or")
        print("  uv add supabase")
        return False


def test_create_client_directly():
    """Test creating Supabase client directly."""
    print_header("Direct Supabase Client Creation Test")

    supabase_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.environ.get(
        "SUPABASE_KEY", "<REDACTED>"
    )

    print(f"URL: {supabase_url}")
    print(f"Key: {supabase_key[:20]}... (truncated)")

    try:
        from supabase import create_client, Client

        print("\nAttempting to create client...")
        client: Client = create_client(supabase_url, supabase_key)
        print(f"✅ Client created: {type(client).__name__}")

        # Try to access client attributes
        print("\nClient attributes:")
        print(f"  - supabase_url: {client.supabase_url}")
        print(f"  - has auth: {hasattr(client, 'auth')}")
        print(f"  - has storage: {hasattr(client, 'storage')}")
        print(f"  - has functions: {hasattr(client, 'functions')}")

        return True, client

    except Exception as e:
        print(f"❌ Failed to create client: {type(e).__name__}: {e}")

        # Provide more detailed error analysis
        print("\nError analysis:")

        # Check if it's a URL issue
        if "url" in str(e).lower():
            print("  - Issue might be with the Supabase URL")
            print(f"  - Current URL: {supabase_url}")
            print(
                "  - Expected format: http://localhost:54321 or https://your-project.supabase.co"
            )

        # Check if it's a key issue
        if "key" in str(e).lower() or "api" in str(e).lower():
            print("  - Issue might be with the Supabase key")
            print("  - Local Supabase keys typically start with 'sb_'")
            print("  - Ensure you're using the SERVICE ROLE key (not anon key)")

        # Check if it's a connection issue
        if "connection" in str(e).lower() or "refused" in str(e).lower():
            print("  - Issue might be network connectivity")
            print("  - Ensure Supabase dev stack is running")
            print("  - Try: curl -I http://127.0.0.1:54321")

        return False, None


def test_auth_methods(client):
    """Test authentication methods."""
    print_header("Authentication Methods Test")

    if not client:
        print("❌ No client available for auth test")
        return False

    try:
        # Test getting auth URL (non-authenticated)
        print("Testing auth.get_url()...")
        auth_url = client.auth.get_url()
        print("✅ auth.get_url() succeeded")
        print(f"   Result type: {type(auth_url)}")

        # Try to get session (will fail without token, but should not crash)
        print("\nTesting auth.get_session() without token...")
        try:
            session = client.auth.get_session()
            print("✅ auth.get_session() succeeded (unexpected)")
            print(f"   Session: {session}")
        except Exception as e:
            print(f"⚠️  auth.get_session() failed (expected): {type(e).__name__}: {e}")

        return True

    except Exception as e:
        print(f"❌ Auth test failed: {type(e).__name__}: {e}")
        return False


async def test_rest_api_directly():
    """Test Supabase REST API directly via HTTP."""
    print_header("Direct REST API Test")

    supabase_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
    supabase_key = os.environ.get(
        "SUPABASE_KEY", "<REDACTED>"
    )

    # Test health endpoint
    health_url = f"{supabase_url.rstrip('/')}/rest/v1/"

    print(f"Testing REST API at: {health_url}")
    print(f"Using key: {supabase_key[:20]}...")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Try to access a public endpoint
            async with session.get(health_url, headers=headers, timeout=10) as response:
                status = response.status
                print(f"\nHTTP Status: {status}")

                if status == 200:
                    print("✅ REST API is accessible")
                    return True
                elif status == 404:
                    print("⚠️  REST API endpoint not found (404)")
                    print("   This might be normal for some Supabase configurations")
                    return True  # Still counts as accessible
                elif status == 401:
                    print("❌ REST API returned 401 Unauthorized")
                    print(
                        "   The API key might be invalid or have insufficient permissions"
                    )
                    return False
                else:
                    print(f"⚠️  REST API returned unexpected status: {status}")
                    return True  # Still got a response

    except Exception as e:
        print(f"❌ REST API test failed: {type(e).__name__}: {e}")
        return False


def test_environment_alternatives():
    """Test alternative environment variable names."""
    print_header("Environment Variable Alternatives Test")

    # Common Supabase environment variable patterns
    env_patterns = [
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SECRET",
        "SUPABASE_ANON_KEY",
        "SUPABASE_JWT_SECRET",
    ]

    print("Checking for Supabase-related environment variables:")

    found_vars = []
    for var in env_patterns:
        value = os.environ.get(var)
        if value:
            found_vars.append(var)
            print(f"  ✅ {var}: {value[:30]}...")
        else:
            print(f"  ❌ {var}: Not set")

    if not found_vars:
        print("\n⚠️  No Supabase environment variables found!")
        print("Set them with:")
        print("  export SUPABASE_URL='http://127.0.0.1:54321'")
        print("  export SUPABASE_KEY='your-service-role-key'")

    return found_vars


def test_local_supabase_ports():
    """Test common local Supabase ports."""
    print_header("Local Supabase Port Scan")

    common_ports = [
        ("Studio", 54323),
        ("Project", 54321),
        ("Database", 54322),
        ("Mailpit", 54324),
    ]

    import socket

    for service, port in common_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)

        result = sock.connect_ex(("127.0.0.1", port))

        if result == 0:
            print(f"✅ {service} port {port}: OPEN")
        else:
            print(f"❌ {service} port {port}: CLOSED")

        sock.close()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🔧 SUPABASE CLIENT DEBUGGING SCRIPT")
    print("=" * 60)

    # Check environment
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("⚠️  Environment variables not set")
        print("Using defaults:")
        print(f"  SUPABASE_URL: {supabase_url or 'http://127.0.0.1:54321'}")
        print(
            f"  SUPABASE_KEY: {supabase_key or '<REDACTED>'}"
        )
        print()

    # Run tests
    import_ok = test_supabase_import()
    if not import_ok:
        return False

    client_ok, client = test_create_client_directly()

    if client_ok and client:
        auth_ok = test_auth_methods(client)
    else:
        auth_ok = False

    rest_ok = await test_rest_api_directly()

    # Additional diagnostics
    test_environment_alternatives()
    test_local_supabase_ports()

    # Summary
    print_header("DEBUGGING SUMMARY")

    print("Test Results:")
    print(f"  ✅ Supabase import: {'PASS' if import_ok else 'FAIL'}")
    print(f"  ✅ Client creation: {'PASS' if client_ok else 'FAIL'}")
    print(f"  ✅ Auth methods: {'PASS' if auth_ok else 'FAIL'}")
    print(f"  ✅ REST API: {'PASS' if rest_ok else 'FAIL'}")

    print("\nCommon Issues and Solutions:")
    print("1. ❌ 'Invalid API key' - Use SERVICE ROLE key (starts with 'sb_')")
    print("2. ❌ Connection refused - Ensure Supabase dev stack is running")
    print("3. ❌ Module not found - Install: pip install supabase>=2.15.1")
    print("4. ❌ URL format wrong - Use: http://127.0.0.1:54321 (not https)")

    print("\nNext Steps:")
    print("1. Check Supabase logs: supabase status")
    print("2. Verify key in Supabase Studio: http://127.0.0.1:54323")
    print(
        "3. Test with curl: curl -H 'apikey: YOUR_KEY' http://127.0.0.1:54321/rest/v1/"
    )

    return all([import_ok, client_ok, auth_ok, rest_ok])


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Debugging interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
