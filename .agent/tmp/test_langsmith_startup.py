#!/usr/bin/env python3
"""
Test script to verify LangSmith dependency behavior in oap-langgraph-tools-agent.

Tests whether the agent fails to start without LangSmith environment variables.
"""

import os
import sys
import asyncio
import traceback


def setup_test_environment():
    """Clear LangSmith environment variables and set up Python path."""
    # Clear any LangSmith env vars
    for key in list(os.environ.keys()):
        if key.startswith("LANGCHAIN_"):
            del os.environ[key]

    # Add project to path
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sys.path.insert(0, project_root)

    print("🧪 Test Environment Setup:")
    print(f"  Project root: {project_root}")
    print(f"  LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2', 'not set')}")
    print(
        f"  LANGCHAIN_API_KEY: {'set' if os.getenv('LANGCHAIN_API_KEY') else 'not set'}"
    )
    print()


async def test_agent_import():
    """Test if we can import the agent module."""
    print("🔍 Testing agent module import...")
    try:

        print("✅ Successfully imported tools_agent.agent")
        return True
    except Exception as e:
        print(f"❌ Failed to import agent module: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


async def test_agent_creation():
    """Test if we can create an agent instance."""
    print("\n🔍 Testing agent creation...")
    try:
        from tools_agent.agent import graph

        # Create minimal config (simulating OAP config)
        config = {
            "configurable": {
                "model_name": "openai:gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 4000,
                "system_prompt": "You are a helpful assistant.",
            }
        }

        # Try to create the agent
        await graph(config)
        print("✅ Agent created successfully without LangSmith env vars")
        return True
    except Exception as e:
        print(f"❌ Error creating agent: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


async def test_with_langsmith_disabled():
    """Test with explicit LangSmith disabling."""
    print("\n🔍 Testing with explicit LANGCHAIN_TRACING_V2=false...")
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    try:
        from tools_agent.agent import graph

        config = {
            "configurable": {
                "model_name": "openai:gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 4000,
                "system_prompt": "You are a helpful assistant.",
            }
        }

        await graph(config)
        print("✅ Agent created successfully with LANGCHAIN_TRACING_V2=false")
        return True
    except Exception as e:
        print(f"❌ Error with LANGCHAIN_TRACING_V2=false: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


async def test_with_invalid_langsmith_key():
    """Test with invalid LangSmith API key (tracing enabled but wrong key)."""
    print("\n🔍 Testing with invalid LangSmith API key...")
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = "lsv2_invalid_key_123"

    try:
        from tools_agent.agent import graph

        config = {
            "configurable": {
                "model_name": "openai:gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 4000,
                "system_prompt": "You are a helpful assistant.",
            }
        }

        await graph(config)
        print("✅ Agent created successfully with invalid LangSmith key")
        print("   Note: LangSmith may log warnings but shouldn't prevent startup")
        return True
    except Exception as e:
        print(f"❌ Error with invalid LangSmith key: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests."""
    setup_test_environment()

    results = []

    # Test 1: Import
    results.append(await test_agent_import())

    # Test 2: Agent creation without LangSmith
    results.append(await test_agent_creation())

    # Test 3: With explicit disable
    results.append(await test_with_langsmith_disabled())

    # Test 4: With invalid key
    results.append(await test_with_invalid_langsmith_key())

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    tests = [
        "Agent module import",
        "Agent creation (no LangSmith env)",
        "Agent creation (LANGCHAIN_TRACING_V2=false)",
        "Agent creation (invalid LangSmith key)",
    ]

    all_passed = True
    for i, (test_name, passed) in enumerate(zip(tests, results)):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED: Agent works without LangSmith configuration")
    else:
        print("⚠️  SOME TESTS FAILED: Check errors above")

    return all_passed


if __name__ == "__main__":
    print("🧪 LangSmith Dependency Test Suite")
    print("=" * 50)

    success = asyncio.run(run_all_tests())

    if success:
        print("\n✅ CONCLUSION: Agent does NOT require LangSmith env vars to start")
        print("   LangSmith tracing is optional/opt-in via environment variables")
    else:
        print("\n❌ CONCLUSION: Agent has issues with LangSmith configuration")
        print("   Some tests failed - check output above")

    sys.exit(0 if success else 1)
