# Task 02: Agent Migration — `create_react_agent` → `create_agent`

> **Status**: 🟢 Complete
> **Parent Goal**: [11-Create-Agent-Migration](../scratchpad.md)
> **Depends On**: [Task-01-Package-Upgrades](../Task-01-Package-Upgrades/scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Migrate `tools_agent/agent.py` from the deprecated `langgraph.prebuilt.create_react_agent` to the new `langchain.agents.create_agent` API. This is the core migration task — the agent factory function `graph()` must produce a compiled graph using the new API while preserving all existing functionality (dynamic model selection, MCP tools, RAG tools, custom endpoints, OAP UI config metadata).

## Current Implementation Analysis

### `tools_agent/agent.py` — Key Points

1. **Entry point**: `async def graph(config: RunnableConfig)` — a factory that returns a compiled graph
2. **Config parsing**: Manually parses `config["configurable"]` into `GraphConfigPydantic` (Pydantic model)
3. **Dynamic model init**: Supports standard providers (`openai:gpt-4o`, `anthropic:claude-*`) AND custom OpenAI-compatible endpoints (vLLM)
4. **Dynamic tools**: MCP tools fetched from remote servers, RAG tools from Supabase — all built at invocation time
5. **System prompt**: `cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT` concatenation
6. **Final call**:
   ```python
   return create_react_agent(
       prompt=cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT,
       model=model,
       tools=tools,
       config_schema=GraphConfigPydantic,
   )
   ```

### What Changes

| Aspect | Current Code | New Code |
|--------|-------------|----------|
| Import | `from langgraph.prebuilt import create_react_agent` | `from langchain.agents import create_agent` |
| Call | `create_react_agent(prompt=..., model=..., tools=..., config_schema=...)` | `create_agent(model=model, tools=tools, system_prompt=...)` |
| `prompt=` | String passed as `prompt` | String passed as `system_prompt` |
| `config_schema=` | `GraphConfigPydantic` passed | **Removed** — not a parameter of `create_agent` |
| Return type | CompiledGraph | CompiledGraph (same) |

### What Stays the Same

- The `graph()` factory function signature and return semantics
- `GraphConfigPydantic` model and its `x_oap_ui_config` metadata (used by OAP frontend)
- All config merging logic (`_merge_assistant_configurable_into_run_config`)
- Dynamic model initialization (`ChatOpenAI` for custom, `init_chat_model` for standard)
- MCP tool fetching via `streamablehttp_client`
- RAG tool creation via `create_rag_tool`
- API key resolution logic

## Implementation Plan

### Step 1: Update import

```python
# OLD
from langgraph.prebuilt import create_react_agent

# NEW
from langchain.agents import create_agent
```

### Step 2: Update the `create_react_agent` call to `create_agent`

```python
# OLD
return create_react_agent(
    prompt=cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT,
    model=model,
    tools=tools,
    config_schema=GraphConfigPydantic,
)

# NEW
return create_agent(
    model=model,
    tools=tools,
    system_prompt=cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT,
)
```

### Step 3: Handle `config_schema` removal

The `config_schema=GraphConfigPydantic` was passed to `create_react_agent` so that the LangGraph runtime could introspect available configurable fields. In our Robyn runtime, this introspection is **not used** — the config is parsed manually:

```python
cfg = GraphConfigPydantic(**(config.get("configurable", {}) or {}))
```

The OAP frontend reads `x_oap_ui_config` metadata from the `GraphConfigPydantic` model schema directly (via the assistants API), not from the compiled graph's config schema. So removing `config_schema` from the compile call should have **no impact** on the Robyn runtime.

**However**, if anyone uses `langgraph dev` (the LangGraph inmem runtime), the config schema introspection would be lost. This is acceptable since our primary runtime is Robyn.

### Step 4: Verify `create_agent` returns a compatible compiled graph

Both `create_react_agent` and `create_agent` return a `CompiledStateGraph` that supports:
- `.astream_events()` — used in `streams.py`
- `.ainvoke()` — standard invocation
- `.astream()` — streaming

The key difference is the **node names** inside the graph:
- `create_react_agent`: node named `"agent"` for the model call
- `create_agent`: node named `"model"` for the model call

This affects `streams.py` and is handled in **Task-03**.

### Step 5: Remove unused import

After migration, remove `from langgraph.prebuilt import create_react_agent` if no other code references it.

## Files to Modify

- `tools_agent/agent.py` — primary migration target
  - Change import
  - Change function call (`create_react_agent` → `create_agent`)
  - `prompt=` → `system_prompt=`
  - Remove `config_schema=` parameter

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `create_agent` compiled graph has different event structure for `astream_events` | High | Medium | Verify in Task-03; the migration guide says node name changes from "agent" to "model" |
| `config_schema` removal breaks `langgraph dev` introspection | Low | High | Acceptable — Robyn is primary runtime; `langgraph dev` is dev-only fallback |
| `create_agent` doesn't support all `create_react_agent` features | Medium | Low | Signatures confirmed compatible via introspection; both accept checkpointer/store |
| Dynamic model object passed to `create_agent` behaves differently | Low | Low | `create_agent` accepts `BaseChatModel` objects the same way |

## Acceptance Criteria

- [x] `tools_agent/agent.py` uses `from langchain.agents import create_agent`
- [x] `create_react_agent` import fully removed
- [x] `system_prompt=` used instead of `prompt=`
- [x] `config_schema=` removed from the call
- [x] `GraphConfigPydantic` class and all its metadata preserved (used by OAP UI)
- [x] `graph()` function still returns a compiled graph successfully
- [ ] Agent can be built with standard providers (OpenAI, Anthropic) — deferred to Task-04 live testing
- [ ] Agent can be built with custom vLLM endpoint — deferred to Task-04 live testing
- [ ] Agent can load MCP tools — deferred to Task-04 live testing
- [ ] Agent can load RAG tools — deferred to Task-04 live testing
- [x] `ruff check` and `ruff format` pass

## Notes

- The `create_agent` API also supports a `middleware=` parameter for advanced customization (dynamic prompts, tool error wrapping, guardrails). We are **not** adopting middleware in this task — the existing manual config parsing in `graph()` works fine. Middleware adoption can be a future enhancement.
- The `create_agent` API supports `cache=` parameter for caching. Not relevant for this migration.
- The `name=` parameter can be used to set a custom name for the agent graph. Could be useful but not required.
- `create_agent` signature confirmed to accept `checkpointer` and `store` params — ready for Goal 12.

## Completion Log

### What was done
1. **Changed import**: `from langgraph.prebuilt import create_react_agent` → `from langchain.agents import create_agent`
2. **Updated function call**:
   - `prompt=` → `system_prompt=`
   - Removed `config_schema=GraphConfigPydantic` (not a parameter of `create_agent`; was only used for LangGraph runtime introspection, not by our Robyn server)
3. **Verified `create_agent` signature** via `inspect.signature()` — confirmed it accepts `model`, `tools`, `system_prompt`, `checkpointer`, `store`, `middleware`, `response_format`, `state_schema`, `context_schema`, `name`, `cache`, etc.
4. **All 440 tests pass**, ruff clean
5. **Task-03 (streaming node name fix) done simultaneously** — see Task-03 scratchpad

### Key decisions
- **`config_schema` safely removed**: `GraphConfigPydantic` is manually parsed via `config.get("configurable", {})` in `graph()`. The `config_schema` param was only for LangGraph runtime introspection (used by `langgraph dev`), not by our Robyn server. OAP UI reads the schema via the assistants API, not from the compiled graph.
- **No middleware adoption**: The existing manual config parsing pattern works. Middleware is a future enhancement.