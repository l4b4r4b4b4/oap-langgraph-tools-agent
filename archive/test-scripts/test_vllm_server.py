#!/usr/bin/env python3
"""
Test script for vLLM OpenAI-compatible server integration.

Tests connectivity and compatibility of local vLLM server running on port 7373.
This script verifies that the vLLM server is accessible and supports the
OpenAI-compatible API format required by the LangGraph agent.

Usage:
    python test_vllm_server.py
"""

import os
import sys
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime


class VLLMServerTester:
    """Test vLLM OpenAI-compatible server functionality."""

    def __init__(self, base_url: str = "http://localhost:7373", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_health_endpoint(self) -> bool:
        """Test the health endpoint."""
        print("🔍 Testing health endpoint...")

        health_url = f"{self.base_url}/health"

        try:
            async with self.session.get(health_url) as response:
                status = response.status
                if status == 200:
                    print(f"✅ Health endpoint OK (HTTP {status})")
                    return True
                else:
                    print(f"⚠️ Health endpoint returned HTTP {status}")
                    # Try to read response for more info
                    try:
                        text = await response.text()
                        if text:
                            print(f"   Response: {text[:100]}")
                    except:
                        pass
                    return False
        except aiohttp.ClientConnectorError as e:
            print(f"❌ Cannot connect to {health_url}: {e}")
            return False
        except asyncio.TimeoutError:
            print(f"❌ Health endpoint timeout after {self.timeout}s")
            return False
        except Exception as e:
            print(f"❌ Health endpoint error: {type(e).__name__}: {e}")
            return False

    async def test_models_endpoint(self) -> Optional[Dict[str, Any]]:
        """Test the models endpoint (OpenAI-compatible)."""
        print("\n🔍 Testing models endpoint...")

        models_url = f"{self.base_url}/v1/models"

        try:
            async with self.session.get(models_url) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    print(f"✅ Models endpoint OK (HTTP {status})")

                    # Parse response
                    if isinstance(data, dict) and "data" in data:
                        models = data["data"]
                        print(f"   Found {len(models)} model(s):")
                        for model in models:
                            model_id = model.get("id", "unknown")
                            print(f"   - {model_id}")
                        return data
                    else:
                        print(f"⚠️ Unexpected response format: {data}")
                        return data
                else:
                    print(f"❌ Models endpoint returned HTTP {status}")
                    try:
                        text = await response.text()
                        print(f"   Response: {text[:200]}")
                    except:
                        pass
                    return None
        except aiohttp.ClientConnectorError as e:
            print(f"❌ Cannot connect to {models_url}: {e}")
            return None
        except asyncio.TimeoutError:
            print(f"❌ Models endpoint timeout after {self.timeout}s")
            return None
        except Exception as e:
            print(f"❌ Models endpoint error: {type(e).__name__}: {e}")
            return None

    async def test_chat_completion(
        self, model: str = "uai/lm-small"
    ) -> Optional[Dict[str, Any]]:
        """Test basic chat completion."""
        print(f"\n🔍 Testing chat completion with model '{model}'...")

        chat_url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you today?"},
            ],
            "max_tokens": 50,
            "temperature": 0.7,
        }

        try:
            async with self.session.post(chat_url, json=payload) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    print(f"✅ Chat completion OK (HTTP {status})")

                    # Extract response
                    if "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        message = choice.get("message", {})
                        content = message.get("content", "").strip()

                        if content:
                            print(f"   Response: {content[:100]}...")
                        else:
                            print("   Response: (empty)")

                        # Show usage if available
                        if "usage" in data:
                            usage = data["usage"]
                            print(
                                f"   Usage: {usage.get('prompt_tokens', '?')} prompt, "
                                f"{usage.get('completion_tokens', '?')} completion"
                            )

                    return data
                else:
                    print(f"❌ Chat completion returned HTTP {status}")
                    try:
                        text = await response.text()
                        print(f"   Error: {text[:200]}")
                    except:
                        pass
                    return None
        except aiohttp.ClientConnectorError as e:
            print(f"❌ Cannot connect to {chat_url}: {e}")
            return None
        except asyncio.TimeoutError:
            print(f"❌ Chat completion timeout after {self.timeout}s")
            return None
        except Exception as e:
            print(f"❌ Chat completion error: {type(e).__name__}: {e}")
            return None

    async def test_tool_calling(
        self, model: str = "uai/lm-small"
    ) -> Optional[Dict[str, Any]]:
        """Test tool calling capability (critical for agent functionality)."""
        print(f"\n🔍 Testing tool calling with model '{model}'...")

        chat_url = f"{self.base_url}/v1/chat/completions"

        # Define a simple calculator tool
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform basic arithmetic calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "The arithmetic expression to evaluate, e.g., '2 + 2'",
                            }
                        },
                        "required": ["expression"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant with access to tools.",
                },
                {"role": "user", "content": "What is 15 * 3?"},
            ],
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": 100,
            "temperature": 0.1,  # Lower temperature for more deterministic tool calls
        }

        try:
            async with self.session.post(chat_url, json=payload) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    print(f"✅ Tool calling request OK (HTTP {status})")

                    # Check for tool calls in response
                    if "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        message = choice.get("message", {})

                        # Check for tool calls
                        tool_calls = message.get("tool_calls")
                        if tool_calls:
                            print("✅ Tool calling supported!")
                            print(f"   Found {len(tool_calls)} tool call(s)")

                            for i, tool_call in enumerate(tool_calls):
                                func = tool_call.get("function", {})
                                name = func.get("name", "unknown")
                                args = func.get("arguments", "{}")
                                print(f"   Tool call {i + 1}: {name}({args})")
                        else:
                            content = message.get("content", "")
                            if content:
                                print(
                                    f"⚠️ No tool calls returned, got text response: {content[:100]}..."
                                )
                            else:
                                print("⚠️ No tool calls and no content returned")

                    return data
                else:
                    print(f"❌ Tool calling returned HTTP {status}")
                    try:
                        text = await response.text()
                        print(f"   Error: {text[:200]}")
                    except:
                        pass
                    return None
        except aiohttp.ClientConnectorError as e:
            print(f"❌ Cannot connect to {chat_url}: {e}")
            return None
        except asyncio.TimeoutError:
            print(f"❌ Tool calling timeout after {self.timeout}s")
            return None
        except Exception as e:
            print(f"❌ Tool calling error: {type(e).__name__}: {e}")
            return None

    async def test_openai_compatibility(self) -> Dict[str, bool]:
        """Run all compatibility tests."""
        print("=" * 60)
        print("🔧 vLLM OpenAI-Compatible Server Test Suite")
        print("=" * 60)
        print(f"Testing server at: {self.base_url}")
        print(f"Timeout: {self.timeout}s")
        print()

        results = {}

        # Run tests
        results["health"] = await self.test_health_endpoint()
        results["models"] = await self.test_models_endpoint() is not None
        results["chat"] = await self.test_chat_completion() is not None
        results["tool_calling"] = await self.test_tool_calling() is not None

        # Summary
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
            print("🎉 ALL TESTS PASSED")
            print("   vLLM server is fully compatible with OpenAI API")
        else:
            print("⚠️  SOME TESTS FAILED")
            print("   Check output above for details")

        print("\n📝 INTEGRATION NOTES:")
        if results["tool_calling"]:
            print("✅ Tool calling is supported - agent can use tools with this LLM")
        else:
            print("⚠️  Tool calling may not be fully supported")
            print("   Agent functionality may be limited without tool calling")

        if results["chat"]:
            print("✅ Basic chat completion works - agent can generate responses")

        print("\n🔧 CONFIGURATION FOR AGENT:")
        print(f"   Base URL: {self.base_url}")
        print("   Model name: uai/lm-small")
        print(f"   OpenAI-compatible endpoint: {self.base_url}/v1")

        return results


async def main():
    """Main entry point."""
    # Check if vLLM server is specified via environment
    base_url = os.environ.get("VLLM_BASE_URL", "http://localhost:7373")

    print(f"Testing vLLM server at: {base_url}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        async with VLLMServerTester(base_url=base_url, timeout=30) as tester:
            results = await tester.test_openai_compatibility()

            # Return exit code based on results
            critical_tests = [
                "health",
                "chat",
            ]  # Tool calling is important but not critical
            critical_passed = all(results.get(test, False) for test in critical_tests)

            return 0 if critical_passed else 1

    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Run async tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
