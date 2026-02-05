#!/usr/bin/env python3
"""
Debug script to check model configuration in the agent.

This script tests whether the custom endpoint configuration is being
properly applied when the agent is invoked through different paths.
"""

import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools_agent.agent import graph, GraphConfigPydantic, get_api_key_for_model
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI


async def debug_direct_model_creation():
    """Test creating ChatOpenAI model directly with custom config."""
    logger.info("=" * 60)
    logger.info("Testing direct ChatOpenAI model creation")
    logger.info("=" * 60)

    # Test 1: Create model with custom endpoint config
    logger.info("\n1. Creating ChatOpenAI with custom endpoint...")
    try:
        model = ChatOpenAI(
            base_url="http://localhost:7374/v1",
            api_key="EMPTY",
            model="mistralai/ministral-3b-instruct",
            temperature=0.1,
            max_tokens=50,
        )

        # Check model attributes
        logger.info(f"Model class: {model.__class__.__name__}")
        logger.info(f"Model name: {model.model_name}")
        logger.info(f"Base URL: {model.base_url}")
        logger.info(f"API key: {'[SET]' if model.api_key else '[NOT SET]'}")

        # Test the model
        logger.info("\nTesting model invocation...")
        response = await model.ainvoke([HumanMessage(content="What is 2+2?")])
        logger.info(f"Response: {response.content}")
        logger.info("✓ Direct model creation works")
        return True
    except Exception as e:
        logger.error(f"Error in direct model creation: {e}")
        import traceback

        traceback.print_exc()
        return False


async def debug_agent_graph_function():
    """Test the graph() function directly."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing graph() function directly")
    logger.info("=" * 60)

    # Create configuration for vLLM
    config = RunnableConfig(
        {
            "configurable": {
                "model_name": "custom:",
                "base_url": "http://localhost:7374/v1",
                "custom_model_name": "mistralai/ministral-3b-instruct",
                "custom_api_key": "EMPTY",
                "temperature": 0.1,
                "max_tokens": 50,
                "system_prompt": "You are a helpful assistant.",
            }
        }
    )

    try:
        # Get the agent graph
        logger.info("Creating agent graph...")
        agent = await graph(config)

        # Check if agent was created
        logger.info(f"Agent created: {agent is not None}")

        # Test the agent
        logger.info("\nTesting agent invocation...")
        messages = [HumanMessage(content="What is 2+2?")]
        result = await agent.ainvoke({"messages": messages})

        if result and "messages" in result:
            response_messages = result["messages"]
            if len(response_messages) > 0:
                last_message = response_messages[-1]
                if hasattr(last_message, "content"):
                    logger.info(f"Agent response: '{last_message.content}'")
                    logger.info("✓ Agent graph function works")
                    return True

        logger.warning("No valid response from agent")
        return False

    except Exception as e:
        logger.error(f"Error in agent graph function: {e}")
        import traceback

        traceback.print_exc()
        return False


async def debug_configuration_parsing():
    """Test configuration parsing."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing configuration parsing")
    logger.info("=" * 60)

    test_configs = [
        {
            "name": "Custom endpoint config",
            "config": {
                "model_name": "custom:",
                "base_url": "http://localhost:7374/v1",
                "custom_model_name": "mistralai/ministral-3b-instruct",
                "custom_api_key": "EMPTY",
            },
        },
        {
            "name": "Missing base_url (should fail)",
            "config": {
                "model_name": "custom:",
                "custom_model_name": "mistralai/ministral-3b-instruct",
            },
        },
        {
            "name": "Standard OpenAI config",
            "config": {
                "model_name": "openai:gpt-4o",
                "temperature": 0.7,
            },
        },
    ]

    all_passed = True
    for test in test_configs:
        logger.info(f"\nTesting: {test['name']}")
        try:
            cfg = GraphConfigPydantic(**test["config"])
            logger.info("  Parsed successfully")
            logger.info(f"  model_name: {cfg.model_name}")
            logger.info(f"  base_url: {cfg.base_url}")
            logger.info(f"  custom_model_name: {cfg.custom_model_name}")
        except Exception as e:
            logger.error(f"  Failed to parse: {e}")
            all_passed = False

    return all_passed


async def debug_api_key_resolution():
    """Test API key resolution logic."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing API key resolution")
    logger.info("=" * 60)

    test_cases = [
        {
            "name": "Custom endpoint with config key",
            "model_name": "custom:",
            "config": {"configurable": {"custom_api_key": "test-config-key"}},
            "expected": "test-config-key",
        },
        {
            "name": "Custom endpoint with env var",
            "model_name": "custom:",
            "config": {"configurable": {}},
            "env_var": ("CUSTOM_API_KEY", "test-env-key"),
            "expected": "test-env-key",
        },
        {
            "name": "Custom endpoint no key",
            "model_name": "custom:",
            "config": {"configurable": {}},
            "expected": None,
        },
        {
            "name": "OpenAI with config key",
            "model_name": "openai:gpt-4o",
            "config": {
                "configurable": {"apiKeys": {"OPENAI_API_KEY": "test-openai-key"}}
            },
            "expected": "test-openai-key",
        },
    ]

    all_passed = True
    for test in test_cases:
        logger.info(f"\nTest: {test['name']}")

        # Set environment variable if specified
        if "env_var" in test:
            key, value = test["env_var"]
            os.environ[key] = value

        try:
            result = get_api_key_for_model(test["model_name"], test["config"])
            logger.info(f"  Expected: {test['expected']}")
            logger.info(f"  Got: {result}")

            if result == test["expected"]:
                logger.info("  ✓ PASS")
            else:
                logger.error("  ✗ FAIL")
                all_passed = False

        finally:
            # Clean up environment variable
            if "env_var" in test:
                key, _ = test["env_var"]
                if key in os.environ:
                    del os.environ[key]

    return all_passed


async def debug_langgraph_runtime_issue():
    """
    Debug the issue with LangGraph runtime not using custom endpoint.

    The logs show that when running through LangGraph HTTP API,
    the agent is calling OpenAI API instead of local vLLM.
    This test tries to reproduce and diagnose the issue.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Debugging LangGraph runtime issue")
    logger.info("=" * 60)

    logger.info("\nIssue: LangGraph runtime calls OpenAI instead of vLLM")
    logger.info("Possible causes:")
    logger.info("1. Configuration not passed correctly to runtime")
    logger.info("2. Model serialization/deserialization issue")
    logger.info("3. ChatOpenAI ignoring base_url with invalid API key")
    logger.info("4. LangGraph runtime overriding configuration")

    # Test: Create model with empty API key
    logger.info("\nTesting ChatOpenAI with empty API key...")
    try:
        model = ChatOpenAI(
            base_url="http://localhost:7374/v1",
            api_key="",  # Empty string
            model="mistralai/ministral-3b-instruct",
        )

        # Check what URL the model will use
        logger.info(f"Model client base_url: {model.base_url}")
        logger.info(
            f"Model client api_key: {'[EMPTY]' if model.api_key == '' else model.api_key}"
        )

        # The actual URL is determined by the async_client
        # Let's check if we can inspect it
        if hasattr(model, "async_client"):
            client = model.async_client
            logger.info(
                f"Async client base_url: {client.base_url if hasattr(client, 'base_url') else 'N/A'}"
            )

    except Exception as e:
        logger.error(f"Error: {e}")

    # Test: What happens with None API key?
    logger.info("\nTesting ChatOpenAI with None API key...")
    try:
        model = ChatOpenAI(
            base_url="http://localhost:7374/v1",
            api_key=None,  # None
            model="mistralai/ministral-3b-instruct",
        )
        logger.info("Model with None API key created")
        logger.info(f"API key attribute: {model.api_key}")
    except Exception as e:
        logger.error(f"Error: {e}")

    return True


async def main():
    """Run all debug tests."""
    logger.info("Starting debug tests for vLLM integration")

    results = []

    # Run tests
    results.append(("Configuration parsing", await debug_configuration_parsing()))
    results.append(("API key resolution", await debug_api_key_resolution()))
    results.append(("Direct model creation", await debug_direct_model_creation()))
    results.append(("Agent graph function", await debug_agent_graph_function()))
    results.append(("LangGraph runtime debug", await debug_langgraph_runtime_issue()))

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Debug Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name:30} {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("\n✅ All debug tests passed")
        logger.info("\nDiagnosis:")
        logger.info("The agent code works correctly when called directly.")
        logger.info("The issue is likely in LangGraph runtime configuration handling.")
    else:
        logger.error("\n❌ Some debug tests failed")
        logger.info("\nNext steps:")
        logger.info("1. Check the specific failing tests above")
        logger.info("2. The main issue is LangGraph runtime not using custom endpoint")
        logger.info("3. Need to debug LangGraph runtime configuration passing")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
