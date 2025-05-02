import pytest
import asyncio
from nostr_sdk import Keys

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def provider_keys():
    """Generate test keys for provider"""
    return Keys.generate()

@pytest.fixture
def client_keys():
    """Generate test keys for client"""
    return Keys.generate()

@pytest.fixture
def server_info():
    """Create test server info"""
    return {
        "name": "Test Server",
        "version": "1.0.0",
        "description": "Test server for unit testing"
    }

@pytest.fixture
def capabilities():
    """Create test capabilities"""
    return {
        "prompts": {"listChanged": True},
        "resources": {"subscribe": True, "listChanged": True},
        "tools": {"listChanged": True}
    }

@pytest.fixture
def server_id():
    """Create test server ID"""
    return "test-server-123"