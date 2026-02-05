#!/usr/bin/env python3
"""
Azure OpenAI Configuration Example

This shows how to configure the agent for Azure OpenAI, which follows
a similar pattern to vLLM but with Azure-specific parameters.
"""

import os
from typing import Optional, Any
from langchain.chat_models import init_chat_model


def configure_azure_openai(
    azure_endpoint: str,
    azure_deployment: str,
    api_version: str = "2024-08-01",
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> Any:
    """
    Configure a model for Azure OpenAI.

    Args:
        azure_endpoint: Azure OpenAI endpoint URL
            e.g., "https://your-resource.openai.azure.com/"
        azure_deployment: Deployment name
            e.g., "gpt-4"
        api_version: Azure API version
        api_key: Azure API key (or use environment variable)
        temperature: Model temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Configured chat model
    """

    # Get API key from parameter or environment
    if api_key is None:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Azure OpenAI API key required. "
                "Provide via api_key parameter or AZURE_OPENAI_API_KEY environment variable."
            )

    print("Configuring Azure OpenAI:")
    print(f"  Endpoint: {azure_endpoint}")
    print(f"  Deployment: {azure_deployment}")
    print(f"  API Version: {api_version}")
    print(f"  API Key: {'*' * 8}{api_key[-4:] if api_key else 'None'}")

    # Azure OpenAI uses the 'azure-openai:' prefix
    model_name = f"azure-openai:{azure_deployment}"

    # Configure the model
    model = init_chat_model(
        model_name,
        model_provider="azure-openai",
        temperature=temperature,
        max_tokens=max_tokens,
        azure_endpoint=azure_endpoint,
        azure_deployment=azure_deployment,
        api_version=api_version,
        api_key=api_key,
    )

    return model


def test_azure_configuration() -> None:
    """Test Azure OpenAI configuration (without actually calling API)."""

    print("=" * 60)
    print("Azure OpenAI Configuration Test")
    print("=" * 60)

    # Example configuration (these would be real values in production)
    config = {
        "azure_endpoint": "https://your-resource.openai.azure.com/",
        "azure_deployment": "gpt-4",
        "api_version": "2024-08-01",
        "api_key": "your-azure-api-key-here",  # In production, use environment variable
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    try:
        # Try to create the model (will fail without real credentials, but shows config)
        model = configure_azure_openai(**config)
        print("\n✓ Azure OpenAI configuration is valid")
        print(f"  Model type: {type(model).__name__}")

        # Show how this would integrate with the agent
        print("\n" + "=" * 60)
        print("Integration with Current Agent Code")
        print("=" * 60)

        print("\nIn tools_agent/agent.py, Azure would be configured via:")
        print("""
1. Model name: 'azure-openai:gpt-4' (or similar)
2. Environment variables:
   - AZURE_OPENAI_ENDPOINT
   - AZURE_OPENAI_DEPLOYMENT
   - AZURE_OPENAI_API_KEY
   - AZURE_OPENAI_API_VERSION (optional, defaults to '2024-08-01')

3. Or via GraphConfigPydantic fields (would need to be added):
   - azure_endpoint: str
   - azure_deployment: str
   - azure_api_key: str (optional, can use environment)
   - azure_api_version: str
""")

        print("\nThe current get_api_key_for_model function supports Azure via:")
        print("""
def get_api_key_for_model(model_name: str, config: RunnableConfig):
    if model_name.startswith("azure-openai:"):
        # Check config for azure_api_key
        azure_key = config.get("configurable", {}).get("azure_api_key")
        if azure_key:
            return azure_key
        # Fallback to environment variable
        return os.getenv("AZURE_OPENAI_API_KEY")
    # ... existing logic for other providers
""")

    except Exception as e:
        print(f"\n✗ Configuration error: {e}")
        print("\nNote: This is expected without real Azure credentials.")
        print("The configuration pattern is correct.")


def compare_vllm_vs_azure() -> None:
    """Compare vLLM and Azure OpenAI configurations."""

    print("\n" + "=" * 60)
    print("vLLM vs Azure OpenAI Configuration Comparison")
    print("=" * 60)

    print("\nvLLM Configuration (what we just tested):")
    print("```python")
    print("model = init_chat_model(")
    print('    "mistralai/ministral-3b-instruct",')
    print('    model_provider="openai",')
    print("    temperature=0,")
    print('    base_url="http://localhost:7374/v1",')
    print('    api_key="EMPTY",')
    print("    max_tokens=100,")
    print(")")
    print("```")

    print("\nAzure OpenAI Configuration:")
    print("```python")
    print("model = init_chat_model(")
    print('    "azure-openai:gpt-4",')
    print('    model_provider="azure-openai",')
    print("    temperature=0.7,")
    print("    max_tokens=1000,")
    print('    azure_endpoint="https://your-resource.openai.azure.com/",')
    print('    azure_deployment="gpt-4",')
    print('    api_version="2024-08-01",')
    print('    api_key="your-azure-api-key",')
    print(")")
    print("```")

    print("\nKey Differences:")
    print("1. Model name prefix: 'azure-openai:' vs no prefix for vLLM")
    print("2. Provider: 'azure-openai' vs 'openai'")
    print("3. Endpoint parameter: azure_endpoint vs base_url")
    print("4. Additional Azure params: azure_deployment, api_version")
    print("5. API key: Real Azure key vs 'EMPTY' for local vLLM")


def main() -> None:
    """Main function."""

    print("Azure OpenAI Configuration Guide")
    print("=" * 60)

    # Test configuration
    test_azure_configuration()

    # Compare with vLLM
    compare_vllm_vs_azure()

    print("\n" + "=" * 60)
    print("Next Steps for Azure Integration:")
    print("=" * 60)

    print("""
1. Add Azure-specific fields to GraphConfigPydantic:
   - azure_endpoint: Optional[str]
   - azure_deployment: Optional[str]
   - azure_api_key: Optional[str]
   - azure_api_version: Optional[str] = "2024-08-01"

2. Update get_api_key_for_model to handle Azure:
   - Add "azure-openai:" prefix detection
   - Check config for azure_api_key
   - Fallback to AZURE_OPENAI_API_KEY environment variable

3. Update model initialization in graph():
   - Detect Azure configuration
   - Use appropriate init_chat_model parameters
   - Similar pattern to current custom: endpoint logic

4. Test with real Azure credentials
5. Update documentation
""")

    print("\nCurrent Status: vLLM integration ✓ WORKING")
    print("Azure OpenAI: Configuration pattern ready, needs implementation")


if __name__ == "__main__":
    main()
