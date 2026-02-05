# Task 02 — Configuration Schema Extension ✅ COMPLETE

Status: 🟢 Complete  
Parent Goal: [05-LLM-Integration](../scratchpad.md)  
Priority: Critical  
Owner: You  
Last Updated: 2026-01-27

## Objective

Extend the agent's configuration schema to support custom OpenAI-compatible LLM endpoints, enabling integration with local vLLM servers (like our Ministral-3-3B instance) and other OpenAI-compatible APIs. This involves modifying `GraphConfigPydantic`, updating the model initialization logic, and ensuring backward compatibility.

## Context

Task 01 successfully verified that:
- ✅ Local vLLM server is running on port 7374 with Ministral-3-3B-Instruct
- ✅ OpenAI-compatible API is fully functional (chat, tool calling, streaming)
- ✅ Configuration requirements identified: `base_url` + `model_name` + optional `api_key`

Now we need to modify the agent to use this local LLM by:
1. Extending `GraphConfigPydantic` with custom endpoint fields
2. Updating `get_api_key_for_model` to handle custom endpoints
3. Modifying `init_chat_model` calls to use custom configurations
4. Updating the model selection UI in OAP

## Success Criteria

- [x] `GraphConfigPydantic` extended with `base_url` and `custom_model_name` fields
- [x] `get_api_key_for_model` handles custom endpoint API keys
- [x] Model initialization supports custom `base_url` via LangChain `ChatOpenAI`
- [x] Backward compatibility maintained for existing model configurations
- [x] Agent can connect to local vLLM server at `http://localhost:7374/v1`
- [ ] Tool calling works with custom LLM endpoint (requires full agent test)
- [x] Model selection UI includes custom endpoint option
- [x] Environment variable support for custom configurations
- [x] Tests verify custom endpoint integration

## Implementation Plan

### Phase 1: Schema Extension ✅ COMPLETE
1. **Extend `GraphConfigPydantic`** ✅:
   - ✅ Added `base_url: Optional[str]` field for custom endpoints
   - ✅ Added `custom_model_name: Optional[str]` field for non-standard model names
   - ✅ Added `custom_api_key: Optional[str]` field for endpoint-specific keys
   - ✅ Updated `x_oap_ui_config` metadata for new fields with `visible_when` conditions

2. **Update Model Selection UI** ✅:
   - ✅ Added "Custom OpenAI-compatible endpoint" option to model dropdown
   - ✅ Show/hide custom fields based on model selection using `visible_when`
   - ✅ Validation handled by Pydantic schema

### Phase 2: Model Initialization ✅ COMPLETE
1. **Modify `get_api_key_for_model`** ✅:
   - ✅ Handles `custom_api_key` from configuration (config → env var → None)
   - ✅ Fallback to `CUSTOM_API_KEY` environment variable
   - ✅ Supports empty API keys for local vLLM (returns `None` → uses "EMPTY")

2. **Update `init_chat_model` usage** ✅:
   - ✅ Detects custom endpoints by checking `cfg.base_url`
   - ✅ Uses `ChatOpenAI` with `base_url` parameter for custom endpoints
   - ✅ Maintains existing behavior for standard providers (OpenAI, Anthropic, Google)

3. **Add Custom Model Detection** ✅:
   - ✅ New model prefix: `custom:` for explicit custom endpoint selection
   - ✅ Auto-detection: If `base_url` provided, uses custom endpoint logic
   - ✅ Uses `custom_model_name` if provided, falls back to `model_name`

### Phase 3: Integration Testing ✅ COMPLETE
1. **Test with Local vLLM** ✅:
   - ✅ Verified connection to `http://localhost:7374/v1`
   - ✅ Tested chat completion with Ministral-3-3B (via separate test script)
   - ⏳ Tool calling verification requires full agent test (Task 03)
   - ⏳ Error handling tests deferred to Task 03

2. **Backward Compatibility Tests** ✅:
   - ✅ Verified existing OpenAI models still work (API key resolution)
   - ✅ Verified Anthropic models still work (API key resolution)
   - ✅ Google model support maintained (unchanged)
   - ✅ No breaking changes to existing configurations

### Phase 4: Documentation & Polish ✅ PARTIAL
1. **Update Configuration Documentation** ✅:
   - ✅ Documented custom endpoint configuration in this scratchpad
   - ✅ Added example for vLLM integration
   - ⏳ Azure OpenAI examples deferred to later task
   - ✅ Environment variable usage documented

2. **Add Validation & Error Messages** ⏳:
   - ⏳ URL format validation deferred (Pydantic handles basic validation)
   - ⏳ Enhanced error messages deferred to Task 03
   - ⏳ Timeout configuration deferred (can be added via `ChatOpenAI` kwargs)

## Technical Design

### Extended Configuration Schema ✅ IMPLEMENTED
```python
# ACTUAL IMPLEMENTATION in agent.py:
class GraphConfigPydantic(BaseModel):
    model_name: Optional[str] = Field(
        default="openai:gpt-4o",
        metadata={
            "x_oap_ui_config": {
                "type": "select",
                "default": "openai:gpt-4o",
                "description": "The model to use in all generations",
                "options": [
                    # Existing options...
                    {
                        "label": "Custom OpenAI-compatible endpoint",
                        "value": "custom:",
                    },
                ],
            }
        },
    )
    
    # New fields for custom endpoints ✅ IMPLEMENTED
    base_url: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "placeholder": "http://localhost:7374/v1",
                "description": "Base URL for custom OpenAI-compatible API",
                "visible_when": {"model_name": "custom:"},
            }
        },
    )
    
    custom_model_name: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "placeholder": "mistralai/ministral-3b-instruct",
                "description": "Model name for custom endpoint",
                "visible_when": {"model_name": "custom:"},
            }
        },
    )
    
    custom_api_key: Optional[str] = Field(
        default=None,
        optional=True,
        metadata={
            "x_oap_ui_config": {
                "type": "password",
                "placeholder": "Leave empty for local vLLM",
                "description": "API key for custom endpoint (optional)",
                "visible_when": {"model_name": "custom:"},
            }
        },
    )
```

### Updated Model Initialization Logic ✅ IMPLEMENTED
```python
# ACTUAL IMPLEMENTATION in agent.py:
def get_api_key_for_model(model_name: str, config: RunnableConfig):
    model_name = model_name.lower()

    # Handle custom endpoints ✅ IMPLEMENTED
    if model_name.startswith("custom:"):
        # First check config for custom_api_key
        custom_key = config.get("configurable", {}).get("custom_api_key")
        if custom_key:
            return custom_key
        # Fallback to environment variable
        return os.getenv("CUSTOM_API_KEY")

    # Existing logic for standard providers...
    model_to_key = {
        "openai:": "OPENAI_API_KEY",
        "anthropic:": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    key_name = next(
        (key for prefix, key in model_to_key.items() if model_name.startswith(prefix)),
        None,
    )
    if not key_name:
        return None
    api_keys = config.get("configurable", {}).get("apiKeys", {})
    if api_keys and api_keys.get(key_name) and len(api_keys[key_name]) > 0:
        return api_keys[key_name]
    # Fallback to environment variable
    return os.getenv(key_name)
```

### Custom Model Initialization ✅ IMPLEMENTED
```python
# ACTUAL IMPLEMENTATION in agent.py graph() function:
# Initialize model based on configuration
if cfg.base_url:
    # Custom endpoint - use ChatOpenAI directly with base_url ✅ IMPLEMENTED
    from langchain_openai import ChatOpenAI

    # Get API key for custom endpoint
    api_key = get_api_key_for_model("custom:", config)
    if not api_key:
        # Use "EMPTY" for local vLLM that doesn't require authentication
        api_key = "EMPTY"

    # Use custom model name if provided, otherwise use the configured model_name
    model_name = cfg.custom_model_name or cfg.model_name

    model = ChatOpenAI(
        base_url=cfg.base_url,
        api_key=api_key,
        model=model_name,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )
else:
    # Standard provider - use init_chat_model
    model = init_chat_model(
        cfg.model_name,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        api_key=get_api_key_for_model(cfg.model_name, config) or "No token found",
    )
```

## Files Modified/Created

### Primary Files Modified ✅:
- ✅ `tools_agent/agent.py` - Extended `GraphConfigPydantic`, updated `get_api_key_for_model`, modified `graph()` function
- ✅ `GraphConfigPydantic` class - Added `base_url`, `custom_model_name`, `custom_api_key` fields
- ✅ `get_api_key_for_model` function - Added custom endpoint API key resolution

### Supporting Files Created ✅:
- ✅ `test_custom_endpoint_integration.py` - Comprehensive integration tests
- ✅ `test_ministral_simple.py` - Ministral-specific API tests
- ✅ `test_vllm_server.py` - vLLM server connectivity tests
- ⏳ `docs/custom-llm-setup.md` - Documentation deferred to Task 03

### Configuration Files ✅:
- ✅ `.env.example` already has placeholders for API keys
- ✅ Model selection UI updated in `x_oap_ui_config` metadata

## Testing Strategy

### Unit Tests ✅ COMPLETED:
1. **Schema Validation** ✅:
   - ✅ Tested `base_url` acceptance (Pydantic validation)
   - ✅ Tested conditional field logic via `visible_when`
   - ✅ Tested backward compatibility with existing models

2. **API Key Resolution** ✅:
   - ✅ Tested `get_api_key_for_model` with custom endpoint
   - ✅ Tested config → environment variable fallback
   - ✅ Tested empty API key handling for local vLLM


   config = {
       "model_name": "custom:",
       "base_url": "http://localhost:7374/v1",
       "custom_model_name": "mistralai/ministral-3b-instruct"
   }
   # Verify agent can initialize and make requests
   ```

2. **Tool Calling Test**:
   - Verify tool calling works with custom endpoint
   - Test complete agent workflow with custom LLM

3. **Error Handling**:
   - Test unavailable endpoint handling
   - Test invalid URL handling
   - Test missing model name handling

### End-to-End Tests:
1. **Complete Agent Workflow**:
   - Authentication → Custom LLM → Tool execution
   - Verify response quality and performance
   - Test with multiple concurrent requests

## Risks & Mitigations

### Risk 1: Breaking Existing Configurations
**Mitigation**: Maintain backward compatibility, test all existing model options, use feature flags if needed.

### Risk 2: Complex Configuration UI
**Mitigation**: Progressive disclosure - show custom fields only when "Custom endpoint" selected.

### Risk 3: Performance Issues with Local LLM
**Mitigation**: Configurable timeouts, connection pooling, graceful degradation.

### Risk 4: Authentication Variations
**Mitigation**: Support multiple auth methods (API key, bearer token, none for local).

### Risk 5: Tool Calling Compatibility
**Mitigation**: Test thoroughly with target LLM, provide compatibility matrix.

## Dependencies

- ✅ Local vLLM server running (verified in Task 01)
- LangChain `ChatOpenAI` support for `base_url` parameter
- OAP UI support for conditional field visibility
- No breaking changes to existing functionality

## Integration Points

### With Supabase Integration (Goal 04):
- Authentication independent of LLM choice
- RAG tools work with any LLM that supports tool calling

### With LangSmith/Langfuse (Goals 02/03):
- Tracing works with any LLM via LangChain callbacks
- No dependency on specific LLM providers

### With MCP Tools:
- Tool execution independent of LLM choice
- All LLMs must support OpenAI tool calling format

## Next Steps

1. **Implement Schema Extension**:
   - Modify `GraphConfigPydantic` in `agent.py`
   - Add new fields with appropriate metadata

2. **Update Model Initialization**:
   - Modify `get_api_key_for_model` for custom endpoints
   - Update `graph()` function to handle custom endpoints

3. **Test Integration**:
   - Test with local vLLM server
   - Verify tool calling works
   - Test backward compatibility

4. **Documentation & Examples**:
   - Update README with custom endpoint setup
   - Add configuration examples
   - Document troubleshooting steps

## Notes

- Local vLLM server: `http://localhost:7374/v1`, model: `mistralai/ministral-3b-instruct`
- Custom endpoint prefix: `custom:` for explicit selection
- Auto-detection: If `base_url` provided, treat as custom endpoint
- API key: Optional for local vLLM, can be `EMPTY` or empty string
- Timeout: Consider adding `request_timeout` configuration for custom endpoints

## References

- [LangChain ChatOpenAI Documentation](https://python.langchain.com/docs/integrations/chat/openai/)
- [vLLM OpenAI-compatible API](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [OpenAI API Compatibility Guide](https://platform.openai.com/docs/api-reference/introduction)
- [Task 01 Research Findings](../Task-01-Research-Architecture/scratchpad.md)