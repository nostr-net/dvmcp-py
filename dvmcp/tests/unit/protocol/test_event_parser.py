import json
import pytest
from nostr_sdk import Keys, EventBuilder, Tag, Kind, Event

from dvmcp.protocol.event_parser import DVMCPEventParser

@pytest.fixture
def request_event(provider_keys, client_keys):
    """Create a test request event"""
    method = "test/method"
    params = {"param1": "value1", "param2": 42}
    request_id = 123
    
    # Create content
    content = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params
    }
    
    # Create tags
    tags = [
        Tag.parse(["p", provider_keys.public_key().to_hex()]),
        Tag.parse(["method", method])
    ]
    
    # Create event
    builder = EventBuilder(Kind(25910), json.dumps(content))
    for tag in tags:
        builder = builder.tags([tag])
    
    return builder.sign_with_keys(client_keys)

@pytest.fixture
def response_event(provider_keys, request_event):
    """Create a test response event"""
    result = {"status": "success", "data": "test-data"}
    request_id = 123
    
    # Create content
    content = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }
    
    # Create tags
    tags = [
        Tag.parse(["e", request_event.id().to_hex()])
    ]
    
    # Create event
    builder = EventBuilder(Kind(26910), json.dumps(content))
    for tag in tags:
        builder = builder.tags([tag])
    
    return builder.sign_with_keys(provider_keys)

@pytest.fixture
def notification_event(provider_keys, client_keys):
    """Create a test notification event"""
    notification_type = "notifications/test"
    params = {"message": "Test notification"}
    
    # Create content
    content = {
        "jsonrpc": "2.0",
        "method": notification_type,
        "params": params
    }
    
    # Create tags
    tags = [
        Tag.parse(["p", client_keys.public_key().to_hex()]),
        Tag.parse(["method", notification_type])
    ]
    
    # Create event
    builder = EventBuilder(Kind(21316), json.dumps(content))
    for tag in tags:
        builder = builder.tags([tag])
    
    return builder.sign_with_keys(provider_keys)

def test_parse_request(request_event):
    """Test parsing of request event"""
    # Parse event
    request = DVMCPEventParser.parse_request(request_event)
    
    # Verify parsed data
    assert request["event_id"] == request_event.id().to_hex()
    assert request["client_pubkey"] == request_event.author().to_hex()
    assert request["method"] == "test/method"
    assert request["request_id"] == 123
    assert request["params"] == {"param1": "value1", "param2": 42}

def test_parse_response(response_event, request_event):
    """Test parsing of response event"""
    # Parse event
    response = DVMCPEventParser.parse_response(response_event)
    
    # Verify parsed data
    assert response["event_id"] == response_event.id().to_hex()
    assert response["provider_pubkey"] == response_event.author().to_hex()
    assert response["request_event_id"] == request_event.id().to_hex()
    assert response["request_id"] == 123
    assert response["success"] is True
    assert response["result"] == {"status": "success", "data": "test-data"}

def test_parse_notification(notification_event, client_keys):
    """Test parsing of notification event"""
    # Parse event
    notification = DVMCPEventParser.parse_notification(notification_event)
    
    # Verify parsed data
    assert notification["event_id"] == notification_event.id().to_hex()
    assert notification["sender_pubkey"] == notification_event.author().to_hex()
    assert notification["target_pubkey"] == client_keys.public_key().to_hex()
    assert notification["notification_type"] == "notifications/test"
    assert notification["params"] == {"message": "Test notification"}
    assert notification["is_mcp"] is True