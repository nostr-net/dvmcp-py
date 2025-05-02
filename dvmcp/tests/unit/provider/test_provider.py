import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nostr_sdk import Keys, Client, Event

from dvmcp.provider import DVMCPProvider
from dvmcp.models.server import ServerInfo, ServerCapabilities

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
async def test_provider_init(provider_keys):
    """Test provider initialization"""
    # Create provider with default client
    provider = DVMCPProvider(provider_keys)
    
    # Verify provider state
    assert provider.keys == provider_keys
    assert provider.client is not None
    assert provider.announced_servers == {}
    assert provider.request_handlers == {}

@pytest.mark.asyncio
async def test_provider_init_with_client(provider_keys, mock_client):
    """Test provider initialization with custom client"""
    # Create provider with custom client
    provider = DVMCPProvider(provider_keys, client=mock_client)
    
    # Verify provider state
    assert provider.keys == provider_keys
    assert provider.client == mock_client
    assert provider.announced_servers == {}
    assert provider.request_handlers == {}

@pytest.mark.asyncio
async def test_connect_disconnect(provider_keys, mock_client):
    """Test connect and disconnect methods"""
    # Create provider
    provider = DVMCPProvider(provider_keys, client=mock_client)
    
    # Connect
    await provider.connect()
    mock_client.connect.assert_called_once()
    
    # Disconnect
    await provider.disconnect()
    mock_client.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_announce_server(provider_keys, mock_client, server_id):
    """Test announcing a server"""
    # Create provider
    provider = DVMCPProvider(provider_keys, client=mock_client)
    
    # Create server info and capabilities
    server_info = ServerInfo(
        name="Test Server",
        version="1.0.0",
        description="Test server for unit testing"
    )
    
    capabilities = ServerCapabilities()
    
    # Mock event ID
    mock_event = MagicMock()
    mock_event.id().to_hex.return_value = "test-event-id"
    
    # Mock event builder
    with patch("dvmcp.protocol.event_builder.DVMCPEventBuilder.create_server_announcement") as mock_create:
        mock_create.return_value = mock_event
        
        # Announce server
        event_id = await provider.announce_server(server_id, server_info, capabilities)
        
        # Verify event was created and sent
        mock_create.assert_called_once_with(
            provider_keys=provider_keys,
            server_info=server_info,
            capabilities=capabilities,
            server_id=server_id
        )
        mock_client.send_event.assert_called_once_with(mock_event)
        
        # Verify event ID was returned
        assert event_id == "test-event-id"
        
        # Verify server was stored
        assert server_id in provider.announced_servers
        assert provider.announced_servers[server_id]["event_id"] == "test-event-id"
        assert provider.announced_servers[server_id]["server_id"] == server_id
        assert provider.announced_servers[server_id]["server_info"] == server_info
        assert provider.announced_servers[server_id]["capabilities"] == capabilities

@pytest.mark.asyncio
async def test_publish_tools_list(provider_keys, mock_client, server_id):
    """Test publishing tools list"""
    # Create provider
    provider = DVMCPProvider(provider_keys, client=mock_client)
    
    # Create tools
    tools = [
        {
            "name": "test-tool",
            "description": "Test tool",
            "inputSchema": {"type": "object"}
        }
    ]
    
    # Mock event ID
    mock_event = MagicMock()
    mock_event.id().to_hex.return_value = "test-event-id"
    
    # Mock event builder
    with patch("dvmcp.protocol.event_builder.DVMCPEventBuilder.create_tools_list") as mock_create:
        mock_create.return_value = mock_event
        
        # Publish tools list
        event_id = await provider.publish_tools_list(tools, server_id)
        
        # Verify event was created and sent
        mock_create.assert_called_once_with(
            provider_keys=provider_keys,
            tools=tools,
            server_id=server_id,
            list_id=None
        )
        mock_client.send_event.assert_called_once_with(mock_event)
        
        # Verify event ID was returned
        assert event_id == "test-event-id"

@pytest.mark.asyncio
async def test_handle_requests(provider_keys, mock_client, server_id):
    """Test handling requests"""
    # Create provider
    provider = DVMCPProvider(provider_keys, client=mock_client)
    
    # Create mock callback
    callback = AsyncMock()
    
    # Setup request handler
    await provider.handle_requests(server_id, callback)
    
    # Verify callback was stored
    assert server_id in provider.request_handlers
    assert provider.request_handlers[server_id] == callback
    
    # Verify subscriptions were created
    assert mock_client.subscribe_with_id.call_count == 3
    assert mock_client.handle_notifications.call_count == 1

@pytest.mark.asyncio
async def test_send_response(provider_keys, mock_client):
    """Test sending response"""
    # Create provider
    provider = DVMCPProvider(provider_keys, client=mock_client)
    
    # Create request event
    request_event = {
        "event_id": "test-request-id",
        "request_id": 123
    }
    
    # Create result
    result = {"status": "success"}
    
    # Mock event ID
    mock_event = MagicMock()
    mock_event.id().to_hex.return_value = "test-response-id"
    
    # Mock event builder
    with patch("dvmcp.protocol.event_builder.DVMCPEventBuilder.create_response") as mock_create:
        mock_create.return_value = mock_event
        
        # Send response
        event_id = await provider.send_response(request_event, result)
        
        # Verify event was created and sent
        mock_create.assert_called_once_with(
            provider_keys=provider_keys,
            request_event_id=request_event["event_id"],
            result=result,
            request_id=request_event["request_id"]
        )
        mock_client.send_event.assert_called_once_with(mock_event)
        
        # Verify event ID was returned
        assert event_id == "test-response-id"

@pytest.mark.asyncio
async def test_send_error_response(provider_keys, mock_client):
    """Test sending error response"""
    # Create provider
    provider = DVMCPProvider(provider_keys, client=mock_client)
    
    # Create error details
    request_event_id = "test-request-id"
    error_code = -32601
    error_message = "Method not found"
    request_id = 123
    
    # Mock event ID
    mock_event = MagicMock()
    mock_event.id().to_hex.return_value = "test-error-id"
    
    # Mock event builder
    with patch("dvmcp.protocol.event_builder.DVMCPEventBuilder.create_error_response") as mock_create:
        mock_create.return_value = mock_event
        
        # Send error response
        event_id = await provider.send_error_response(
            request_event_id, error_code, error_message, request_id
        )
        
        # Verify event was created and sent
        mock_create.assert_called_once_with(
            provider_keys=provider_keys,
            request_event_id=request_event_id,
            error_code=error_code,
            error_message=error_message,
            request_id=request_id
        )
        mock_client.send_event.assert_called_once_with(mock_event)
        
        # Verify event ID was returned
        assert event_id == "test-error-id"