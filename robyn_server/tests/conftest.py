"""Pytest configuration for Robyn server tests."""

import pytest

# Configure pytest-asyncio to use function-scoped event loops
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def anyio_backend():
    """Configure anyio to use asyncio backend only."""
    return "asyncio"
