import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from dvmcp.client import DVMCPClient
from dvmcp.models.server import ServerInfo, ServerCapabilities

@pytest.fixture
def client_keys():
    """Generate test keys for client"""
    from nostr_sdk import Keys
    return Keys.generate()

@pytest.fixture
def mock_client():
    """Create a mock Nostr client"""
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.send_event = AsyncMock()
    client.subscribe_with_id = AsyncMock()
    client.handle_notifications = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_progress_callback(client_keys, mock_client):
    """Test progress callback handling"""
    # Create client
    client = DVMCPClient(client_keys, client=mock_client)
    
    # Create mock progress callback
    progress_callback = AsyncMock()
    
    # Register progress callback
    request_id = "test-request-123"
    client.register_progress_callback(request_id, progress_callback)
    
    # Create progress notification
    notification = {
        "notification_type": "notifications/progress",
        "event_id": "test-event-id",
        "params": {
            "id": request_id,
            "message": "Progress update"
        }
    }
    
    # Handle notification
    await client._handle_notification_event(notification)
    
    # Verify callback was called
    progress_callback.assert_called_once_with("Progress update")
    
    # Unregister callback
    client.unregister_progress_callback(request_id)
    
    # Reset mock
    progress_callback.reset_mock()
    
    # Handle notification again
    await client._handle_notification_event(notification)
    
    # Verify callback was not called
    progress_callback.assert_not_called()

@pytest.mark.asyncio
async def test_payment_handler(client_keys, mock_client):
    """Test payment handler"""
    # Create client
    client = DVMCPClient(client_keys, client=mock_client)
    
    # Create mock payment handler
    payment_handler = AsyncMock()
    
    # Register payment handler
    client.register_payment_handler(payment_handler)
    
    # Create payment notification
    notification = {
        "notification_type": "payment-required",
        "event_id": "test-event-id",
        "amount": 1000,
        "bolt11": "lnbc10n1...",
        "request_event_id": "test-request-id"
    }
    
    # Handle notification
    await client._handle_notification_event(notification)
    
    # Verify handler was called
    payment_handler.assert_called_once_with(1000, "lnbc10n1...", "test-request-id")
    
    # Unregister handler
    client.unregister_payment_handler()
    
    # Reset mock
    payment_handler.reset_mock()
    
    # Handle notification again
    await client._handle_notification_event(notification)
    
    # Verify handler was not called
    payment_handler.assert_not_called()

@pytest.mark.asyncio
async def test_list_refresh_notifications(client_keys, mock_client):
    """Test list refresh notifications"""
    # Create client
    client = DVMCPClient(client_keys, client=mock_client)
    
    # Mock refresh methods
    client._refresh_tools_list = AsyncMock()
    client._refresh_resources_list = AsyncMock()
    client._refresh_resource = AsyncMock()
    client._refresh_prompts_list = AsyncMock()
    
    # Create server ID
    server_id = "test-server-123"
    
    # Create tools list changed notification
    tools_notification = {
        "notification_type": "notifications/tools/list_changed",
        "event_id": "test-event-id-1",
        "server_id": server_id
    }
    
    # Handle notification
    await client._handle_notification_event(tools_notification)
    
    # Verify refresh method was called
    client._refresh_tools_list.assert_called_once_with(server_id)
    
    # Create resources list changed notification
    resources_notification = {
        "notification_type": "notifications/resources/list_changed",
        "event_id": "test-event-id-2",
        "server_id": server_id
    }
    
    # Handle notification
    await client._handle_notification_event(resources_notification)
    
    # Verify refresh method was called
    client._refresh_resources_list.assert_called_once_with(server_id)
    
    # Create resource updated notification
    resource_notification = {
        "notification_type": "notifications/resources/updated",
        "event_id": "test-event-id-3",
        "server_id": server_id,
        "params": {
            "uri": "resource://test"
        }
    }
    
    # Handle notification
    await client._handle_notification_event(resource_notification)
    
    # Verify refresh method was called
    client._refresh_resource.assert_called_once_with("resource://test", server_id)
    
    # Create prompts list changed notification
    prompts_notification = {
        "notification_type": "notifications/prompts/list_changed",
        "event_id": "test-event-id-4",
        "server_id": server_id
    }
    
    # Handle notification
    await client._handle_notification_event(prompts_notification)
    
    # Verify refresh method was called
    client._refresh_prompts_list.assert_called_once_with(server_id)