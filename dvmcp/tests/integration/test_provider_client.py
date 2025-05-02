import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

from dvmcp.client import DVMCPClient
from dvmcp.provider import DVMCPProvider
from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool

class MockRelay:
    """Mock relay for testing provider-client interaction"""
    
    def __init__(self):
        self.events = []
        self.subscribers = {}
    
    async def publish_event(self, event):
        """Publish event to subscribers"""
        self.events.append(event)
        
        # Notify subscribers
        for sub_id, callback in self.subscribers.items():
            await callback(self.url, sub_id, event)
    
    async def subscribe(self, sub_id, filter_obj, callback):
        """Subscribe to events"""
        self.subscribers[sub_id] = callback

class MockClient:
    """Mock Nostr client for testing"""
    
    def __init__(self, keys, relay=None):
        self.keys = keys
        self.relay = relay or MockRelay()
        self.relay.url = "wss://mock-relay.example.com"
        self.notification_handler = None
    
    async def connect(self):
        """Connect to relay"""
        pass
    
    async def disconnect(self):
        """Disconnect from relay"""
        pass
    
    async def send_event(self, event):
        """Send event to relay"""
        await self.relay.publish_event(event)
    
    async def subscribe_with_id(self, id, filter):
        """Subscribe to events"""
        await self.relay.subscribe(id, filter, self.notification_handler)
    
    async def handle_notifications(self, handler):
        """Set notification handler"""
        self.notification_handler = handler

@pytest.fixture
def shared_relay():
    """Create a shared mock relay"""
    return MockRelay()

@pytest.fixture
def provider_client(provider_keys, client_keys, shared_relay):
    """Create provider and client with shared relay"""
    # Create mock clients
    provider_client = MockClient(provider_keys, shared_relay)
    client_client = MockClient(client_keys, shared_relay)
    
    # Create provider and client
    provider = DVMCPProvider(provider_keys, client=provider_client)
    client = DVMCPClient(client_keys, client=client_client)
    
    return provider, client

@pytest.mark.asyncio
async def test_server_discovery(provider_client):
    """Test server discovery"""
    provider, client = provider_client
    
    # Connect provider and client
    await provider.connect()
    await client.connect()
    
    # Create server info and capabilities
    server_info = ServerInfo(
        name="Test Server",
        version="1.0.0",
        description="Test server for integration testing"
    )
    
    capabilities = ServerCapabilities()
    server_id = "test-integration-server"
    
    # Announce server
    await provider.announce_server(server_id, server_info, capabilities)
    
    # Discover servers
    with patch("dvmcp.client.DVMCPClient.discover_servers", return_value={
        server_id: {
            "server_id": server_id,
            "provider_pubkey": provider.keys.public_key().to_hex(),
            "server_info": server_info.to_dict(),
            "capabilities": capabilities.to_dict(),
            "protocol_version": "2025-03-26"
        }
    }):
        discovered = await client.discover_servers()
        
        # Verify server was discovered
        assert server_id in discovered
        assert discovered[server_id]["server_id"] == server_id
        assert discovered[server_id]["provider_pubkey"] == provider.keys.public_key().to_hex()

@pytest.mark.asyncio
async def test_tools_list_and_call(provider_client):
    """Test listing tools and calling a tool"""
    provider, client = provider_client
    
    # Connect provider and client
    await provider.connect()
    await client.connect()
    
    # Create server info and capabilities
    server_info = ServerInfo(
        name="Test Server",
        version="1.0.0",
        description="Test server for integration testing"
    )
    
    capabilities = ServerCapabilities()
    server_id = "test-integration-server"
    
    # Announce server
    await provider.announce_server(server_id, server_info, capabilities)
    
    # Create tools
    tools = [
        Tool(
            name="echo",
            description="Echo back the input",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }
        )
    ]
    
    # Publish tools list
    await provider.publish_tools_list(tools, server_id)
    
    # Setup request handler
    async def handle_request(request):
        if request["method"] == "tools/list":
            return {"tools": [tool.to_dict() for tool in tools]}
        elif request["method"] == "tools/call":
            if request["params"]["name"] == "echo":
                return {"result": request["params"]["arguments"]["message"]}
            else:
                raise ValueError(f"Unknown tool: {request['params']['name']}")
        else:
            raise ValueError(f"Unknown method: {request['method']}")
    
    await provider.handle_requests(server_id, handle_request)
    
    # Mock client connection to server
    with patch.object(client, "active_servers", {
        server_id: {
            "server_id": server_id,
            "provider_pubkey": provider.keys.public_key().to_hex(),
            "server_info": server_info.to_dict(),
            "capabilities": capabilities.to_dict()
        }
    }):
        # Mock _get_server_info to return the server info
        with patch.object(client, "_get_server_info", return_value={
            "server_id": server_id,
            "provider_pubkey": provider.keys.public_key().to_hex()
        }):
            # List tools
            with patch.object(client.request_manager, "register_request", 
                             side_effect=lambda request_event_id, callback, timeout: 
                                 asyncio.create_task(callback({
                                     "success": True,
                                     "result": {"tools": [tool.to_dict() for tool in tools]}
                                 }))):
                tools_list = await client.list_tools(server_id)
                
                # Verify tools were listed
                assert "tools" in tools_list
                assert len(tools_list["tools"]) == 1
                assert tools_list["tools"][0]["name"] == "echo"
            
            # Call tool
            with patch.object(client.request_manager, "register_request", 
                             side_effect=lambda request_event_id, callback, timeout: 
                                 asyncio.create_task(callback({
                                     "success": True,
                                     "result": {"result": "Hello, world!"}
                                 }))):
                result = await client.call_tool("echo", {"message": "Hello, world!"}, server_id)
                
                # Verify tool was called
                assert "result" in result
                assert result["result"] == "Hello, world!"