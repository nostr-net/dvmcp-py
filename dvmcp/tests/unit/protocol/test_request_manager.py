import asyncio
import pytest
import time
from unittest.mock import AsyncMock

from dvmcp.protocol.request_manager import RequestManager

@pytest.mark.asyncio
async def test_register_request():
    """Test registering a request"""
    # Create request manager
    manager = RequestManager()
    
    # Create mock callback
    callback = AsyncMock()
    
    # Register request
    request_event_id = "test-request-123"
    await manager.register_request(request_event_id, callback)
    
    # Verify request is registered
    assert request_event_id in manager.pending_requests
    assert manager.pending_requests[request_event_id]["callback"] == callback
    assert "timestamp" in manager.pending_requests[request_event_id]
    assert "timeout" in manager.pending_requests[request_event_id]
    
    # Verify timeout task is created
    assert request_event_id in manager.tasks

@pytest.mark.asyncio
async def test_handle_response():
    """Test handling a response"""
    # Create request manager
    manager = RequestManager()
    
    # Create mock callback
    callback = AsyncMock()
    
    # Register request
    request_event_id = "test-request-123"
    await manager.register_request(request_event_id, callback)
    
    # Create response
    response = {
        "request_event_id": request_event_id,
        "success": True,
        "result": {"status": "success"}
    }
    
    # Handle response
    result = await manager.handle_response(response)
    
    # Verify response was handled
    assert result is True
    callback.assert_called_once_with(response)
    
    # Verify request is removed
    assert request_event_id not in manager.pending_requests
    assert request_event_id not in manager.tasks

@pytest.mark.asyncio
async def test_handle_unknown_response():
    """Test handling a response for unknown request"""
    # Create request manager
    manager = RequestManager()
    
    # Create response
    response = {
        "request_event_id": "unknown-request",
        "success": True,
        "result": {"status": "success"}
    }
    
    # Handle response
    result = await manager.handle_response(response)
    
    # Verify response was not handled
    assert result is False

@pytest.mark.asyncio
async def test_timeout():
    """Test request timeout"""
    # Create request manager with short timeout
    manager = RequestManager(default_timeout=0.1)
    
    # Create mock callback
    callback = AsyncMock()
    
    # Register request
    request_event_id = "test-request-123"
    await manager.register_request(request_event_id, callback, timeout=0.1)
    
    # Wait for timeout
    await asyncio.sleep(0.2)
    
    # Verify callback was called with timeout error
    callback.assert_called_once()
    call_args = callback.call_args[0][0]
    assert call_args["success"] is False
    assert call_args["error"]["code"] == -32000
    assert "timed out" in call_args["error"]["message"].lower()
    
    # Verify request is removed
    assert request_event_id not in manager.pending_requests
    assert request_event_id not in manager.tasks

@pytest.mark.asyncio
async def test_clear():
    """Test clearing all pending requests"""
    # Create request manager
    manager = RequestManager()
    
    # Create mock callbacks
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    
    # Register requests
    await manager.register_request("request-1", callback1)
    await manager.register_request("request-2", callback2)
    
    # Verify requests are registered
    assert len(manager.pending_requests) == 2
    assert len(manager.tasks) == 2
    
    # Clear requests
    manager.clear()
    
    # Verify all requests are cleared
    assert len(manager.pending_requests) == 0
    assert len(manager.tasks) == 0