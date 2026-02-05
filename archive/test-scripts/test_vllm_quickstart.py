#!/usr/bin/env python3
"""
Test vLLM integration with LangGraph using the quickstart example.
This tests basic LLM provider connectivity with vLLM.
"""

import asyncio
import sys
from typing import List, Dict, Any
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from typing_extensions import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from typing import Literal


# Define tools
@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b


class MessagesState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    llm_calls: int


def create_agent_with_vllm(
    base_url: str = "http://localhost:7374/v1",
    model_name: str = "mistralai/ministral-3b-instruct",
) -> Any:
    """Create a LangGraph agent configured to use vLLM."""

    print(f"Configuring agent with vLLM at {base_url}")
    print(f"Using model: {model_name}")

    # Initialize model with vLLM
    # Using openai:// prefix as suggested in LangChain documentation
    model = init_chat_model(
        f"openai://{model_name}",
        model_provider="openai",
        temperature=0,
        base_url=base_url,
        api_key="EMPTY",  # Required but ignored by vLLM
        max_tokens=100,
    )

    # Augment the LLM with tools
    tools = [add, multiply, divide]
    tools_by_name = {tool.name: tool for tool in tools}
    model_with_tools = model.bind_tools(tools)

    # Define model node
    def llm_call(state: Dict[str, Any]) -> Dict[str, Any]:
        """LLM decides whether to call a tool or not"""
        return {
            "messages": [
                model_with_tools.invoke(
                    [
                        SystemMessage(
                            content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                        )
                    ]
                    + state["messages"]
                )
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    # Define tool node
    def tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Performs the tool call"""
        result = []
        for tool_call in state["messages"][-1].tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            result.append(
                ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
            )
        return {"messages": result}

    # Conditional edge function
    def should_continue(state: MessagesState) -> Literal["tool_node", END]:
        """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM makes a tool call, then perform an action
        if last_message.tool_calls:
            return "tool_node"

        # Otherwise, we stop (reply to the user)
        return END

    # Build workflow
    agent_builder = StateGraph(MessagesState)

    # Add nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    agent_builder.add_edge("tool_node", "llm_call")

    # Compile the agent
    return agent_builder.compile()


async def test_vllm_connection(base_url: str = "http://localhost:7374/v1") -> bool:
    """Test basic connection to vLLM server."""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/models", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✓ vLLM connection successful")
                    print(
                        f"  Available models: {[m['id'] for m in data.get('data', [])]}"
                    )
                    return True
                else:
                    print(f"✗ vLLM connection failed: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"✗ vLLM connection error: {e}")
        return False


async def test_agent_with_vllm() -> bool:
    """Test the agent with vLLM integration."""

    print("\n" + "=" * 60)
    print("Testing vLLM integration with LangGraph")
    print("=" * 60)

    # Test vLLM connection first
    print("\n1. Testing vLLM server connection...")
    if not await test_vllm_connection():
        print("Failed to connect to vLLM server. Make sure it's running.")
        return False

    # Create agent with vLLM
    print("\n2. Creating agent with vLLM configuration...")
    try:
        agent = create_agent_with_vllm()
        print("✓ Agent created successfully")
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")
        return False

    # Test simple arithmetic
    print("\n3. Testing agent with arithmetic tasks...")

    test_cases = [
        ("Add 3 and 4.", "3 + 4 = 7"),
        ("Multiply 5 and 6.", "5 * 6 = 30"),
        ("Divide 10 by 2.", "10 / 2 = 5.0"),
    ]

    all_passed = True

    for query, expected in test_cases:
        print(f"\n  Testing: '{query}'")
        try:
            messages = [HumanMessage(content=query)]
            result = agent.invoke({"messages": messages, "llm_calls": 0})

            # Extract assistant messages
            assistant_messages = [
                msg
                for msg in result["messages"]
                if hasattr(msg, "content") and msg.content and msg.type == "ai"
            ]

            if assistant_messages:
                last_message = assistant_messages[-1]
                print(f"  Response: {last_message.content[:100]}...")
                print("  ✓ Query processed successfully")
            else:
                print("  ✗ No assistant response received")
                all_passed = False

        except Exception as e:
            print(f"  ✗ Error during agent invocation: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False


async def test_azure_openai_config() -> None:
    """Show how to configure Azure OpenAI (for reference)."""
    print("\n" + "=" * 60)
    print("Azure OpenAI Configuration Example")
    print("=" * 60)

    # Example Azure OpenAI configuration
    azure_config = {
        "model_name": "azure-openai:gpt-4",
        "azure_endpoint": "https://your-resource.openai.azure.com/",
        "azure_deployment": "gpt-4",
        "api_version": "2024-08-01",
        "api_key": "your-azure-api-key",
    }

    print("\nFor Azure OpenAI, you would use:")
    print("```python")
    print("model = init_chat_model(")
    print(f'    "{azure_config["model_name"]}",')
    print(f'    azure_endpoint="{azure_config["azure_endpoint"]}",')
    print(f'    azure_deployment="{azure_config["azure_deployment"]}",')
    print(f'    api_version="{azure_config["api_version"]}",')
    print(f'    api_key="{azure_config["api_key"]}",')
    print("    temperature=0,")
    print(")")
    print("```")

    print("\nIn the current agent code, Azure would be configured via:")
    print("- model_name: 'azure-openai:gpt-4'")
    print(
        "- Environment variables or config for azure_endpoint, azure_deployment, api_key"
    )
    print("- The get_api_key_for_model function handles Azure API key resolution")


async def main() -> None:
    """Main test function."""

    print("LangGraph vLLM Integration Test")
    print("=" * 60)

    # Test vLLM integration
    vllm_success = await test_agent_with_vllm()

    if vllm_success:
        print("\n✓ vLLM integration test completed successfully")
    else:
        print("\n✗ vLLM integration test failed")
        sys.exit(1)

    # Show Azure OpenAI configuration example
    await test_azure_openai_config()

    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. For production, consider using langgraph dev server")
    print("2. Azure OpenAI can be configured similarly with appropriate endpoints")
    print("3. Test with actual LangGraph runtime API for full integration")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
