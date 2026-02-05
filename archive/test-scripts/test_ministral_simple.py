#!/usr/bin/env python3
"""
Simple test script for Ministral vLLM server on port 7374.
Tests basic chat completion and tool calling capabilities.
"""

import json
import sys
from openai import OpenAI


def test_basic_chat():
    """Test basic chat completion."""
    print("🧪 Testing basic chat completion...")

    client = OpenAI(
        api_key="EMPTY",  # vLLM doesn't require API key
        base_url="http://localhost:7374/v1",
    )

    # List available models
    models = client.models.list()
    model_id = models.data[0].id
    print(f"📦 Model ID: {model_id}")

    # Test simple chat
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2 + 2?"},
        ],
        max_tokens=50,
        temperature=0.1,
    )

    content = response.choices[0].message.content
    print(f"💬 Response: {content}")

    return True


def test_tool_calling():
    """Test tool calling capability (critical for agent)."""
    print("\n🧪 Testing tool calling...")

    client = OpenAI(
        api_key="EMPTY",
        base_url="http://localhost:7374/v1",
    )

    models = client.models.list()
    model_id = models.data[0].id

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
                },
            },
        }
    ]

    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant with access to tools.",
            },
            {
                "role": "user",
                "content": "What is 15 * 3? Use the calculator tool if needed.",
            },
        ],
        tools=tools,
        tool_choice="auto",
        max_tokens=100,
        temperature=0.1,
    )

    message = response.choices[0].message

    if message.tool_calls:
        print("✅ Tool calling supported!")
        print(f"   Found {len(message.tool_calls)} tool call(s)")

        for i, tool_call in enumerate(message.tool_calls):
            func = tool_call.function
            print(f"   Tool call {i + 1}: {func.name}({func.arguments})")

        # Simulate tool execution
        tool_results = []
        for tool_call in message.tool_calls:
            if tool_call.function.name == "calculator":
                # In real agent, this would execute the tool
                args = json.loads(tool_call.function.arguments)
                expression = args.get("expression", "")
                print(f"   Would calculate: {expression}")
                tool_results.append("45")  # Simulated result

        return True
    else:
        content = message.content or "(no content)"
        print(f"⚠️ No tool calls returned, got: {content[:100]}...")
        return False  # Tool calling is critical for agent


def test_streaming():
    """Test streaming response."""
    print("\n🧪 Testing streaming...")

    client = OpenAI(
        api_key="EMPTY",
        base_url="http://localhost:7374/v1",
    )

    models = client.models.list()
    model_id = models.data[0].id

    stream = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "user", "content": "Say 'Hello World' in 3 different languages."},
        ],
        stream=True,
        max_tokens=100,
        temperature=0.1,
    )

    print("   Streaming response: ", end="", flush=True)
    collected = []

    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            collected.append(content)

    print()  # New line after streaming
    return len(collected) > 0


def main():
    """Run all tests."""
    print("=" * 60)
    print("🔧 Ministral vLLM Server Test")
    print("=" * 60)
    print("Server: http://localhost:7374")
    print()

    try:
        # Test 1: Basic connectivity and chat
        chat_ok = test_basic_chat()

        # Test 2: Tool calling (most important for agent)
        tool_ok = test_tool_calling()

        # Test 3: Streaming
        stream_ok = test_streaming()

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        print(f"✅ Basic chat: {'PASS' if chat_ok else 'FAIL'}")
        print(f"✅ Tool calling: {'PASS' if tool_ok else 'FAIL'}")
        print(f"✅ Streaming: {'PASS' if stream_ok else 'FAIL'}")

        print("\n" + "=" * 60)
        if chat_ok and tool_ok:
            print("🎉 SUCCESS: Ministral server is working!")
            print("   The agent can use this LLM with tool calling.")

            print("\n📝 AGENT CONFIGURATION:")
            print("   Base URL: http://localhost:7374/v1")
            print("   Model: mistralai/ministral-3b-instruct")
            print("   API Key: (not required for local vLLM)")

            return 0
        else:
            print("⚠️  WARNING: Some tests failed")
            if not tool_ok:
                print("   Tool calling failed - agent functionality will be limited")
            return 1

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
