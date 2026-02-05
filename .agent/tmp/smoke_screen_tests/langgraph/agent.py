# Step 1: Define tools and model

from langchain.tools import tool
from langchain.chat_models import init_chat_model


# Use vLLM with remote server
model = init_chat_model(
    "mistralai/ministral-3b-instruct",  # Model name as shown in vLLM /models endpoint
    model_provider="openai",  # Uses ChatOpenAI under the hood
    temperature=0,
    # vLLM endpoint params
    base_url="http://localhost:7374/v1",
    api_key="EMPTY",  # Required but ignored by vLLM
    max_tokens=100,
)


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


# Augment the LLM with tools
tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)

# Step 2: Define state

from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


# Step 3: Define model node
from langchain.messages import SystemMessage


def llm_call(state: dict):
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


# Step 4: Define tool node

from langchain.messages import ToolMessage


def tool_node(state: dict):
    """Performs the tool call"""

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


# Step 5: Define logic to determine whether to end

from typing import Literal
from langgraph.graph import StateGraph, START, END


# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END


# Step 6: Build agent

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
agent = agent_builder.compile()


# Invoke
from langchain.messages import HumanMessage

print("Testing vLLM agent with arithmetic...")
messages = [HumanMessage(content="Add 3 and 4.")]
try:
    result = agent.invoke({"messages": messages, "llm_calls": 0})
    print("\nAgent execution successful!")
    print(f"Number of LLM calls: {result.get('llm_calls', 0)}")

    # Print all messages
    for i, m in enumerate(result["messages"]):
        print(f"\nMessage {i}:")
        print(f"  Type: {m.type}")
        if hasattr(m, "content") and m.content:
            print(f"  Content: {m.content[:200]}")
        if hasattr(m, "tool_calls") and m.tool_calls:
            print(f"  Tool calls: {len(m.tool_calls)}")
            for tc in m.tool_calls:
                print(f"    - {tc['name']}({tc['args']})")
except Exception as e:
    print(f"\nError during agent execution: {e}")
    import traceback

    traceback.print_exc()
