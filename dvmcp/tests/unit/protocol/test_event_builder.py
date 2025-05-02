import json
import pytest
from nostr_sdk import Keys

from dvmcp.protocol.event_builder import DVMCPEventBuilder
from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool, Resource, Prompt

def test_create_server_announcement(provider_keys, server_info, capabilities, server_id):
    """Test creation of server announcement event"""
    # Create event
    event = DVMCPEventBuilder.create_server_announcement(
        provider_keys=provider_keys,
        server_info=server_info,
        capabilities=capabilities,
        server_id=server_id
    )
    
    # Verify event properties
    assert event.kind().as_u16() == 31316
    assert event.author().to_hex() == provider_keys.public_key().to_hex()
    
    # Verify content structure
    content = json.loads(event.content())
    assert content["jsonrpc"] == "2.0"
    assert "result" in content
    assert content["result"]["protocolVersion"] == "2025-03-26"
    
    # Verify tags
    tags = event.tags().to_vec()
    d_tags = [tag for tag in tags if tag.kind_str() == "d"]
    assert len(d_tags) == 1
    assert d_tags[0].content() == server_id
    
    # Verify signature
    assert event.verify()

def test_create_tools_list(provider_keys, server_id):
    """Test creation of tools list event"""
    # Create test tools
    tools = [
        Tool(
            name="test-tool",
            description="Test tool for unit testing",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        )
    ]
    
    # Create event
    event = DVMCPEventBuilder.create_tools_list(
        provider_keys=provider_keys,
        tools=tools,
        server_id=server_id
    )
    
    # Verify event properties
    assert event.kind().as_u16() == 31317
    assert event.author().to_hex() == provider_keys.public_key().to_hex()
    
    # Verify content structure
    content = json.loads(event.content())
    assert content["jsonrpc"] == "2.0"
    assert "result" in content
    assert "tools" in content["result"]
    assert len(content["result"]["tools"]) == 1
    assert content["result"]["tools"][0]["name"] == "test-tool"
    
    # Verify tags
    tags = event.tags().to_vec()
    s_tags = [tag for tag in tags if tag.kind_str() == "s"]
    assert len(s_tags) == 1
    assert s_tags[0].content() == server_id
    
    # Verify signature
    assert event.verify()

def test_create_response(provider_keys):
    """Test creation of response event"""
    # Create test data
    request_event_id = "abcdef1234567890"
    result = {"status": "success", "data": "test-data"}
    request_id = 42
    
    # Create event
    event = DVMCPEventBuilder.create_response(
        provider_keys=provider_keys,
        request_event_id=request_event_id,
        result=result,
        request_id=request_id
    )
    
    # Verify event properties
    assert event.kind().as_u16() == 26910
    assert event.author().to_hex() == provider_keys.public_key().to_hex()
    
    # Verify content structure
    content = json.loads(event.content())
    assert content["jsonrpc"] == "2.0"
    assert content["id"] == request_id
    assert content["result"] == result
    
    # Verify tags
    tags = event.tags().to_vec()
    e_tags = [tag for tag in tags if tag.kind_str() == "e"]
    assert len(e_tags) == 1
    assert e_tags[0].content() == request_event_id
    
    # Verify signature
    assert event.verify()