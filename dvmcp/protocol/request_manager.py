import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from nostr_sdk import Event

from dvmcp.logging import get_logger

logger = get_logger("protocol.request_manager")

class RequestManager:
    """Manages request-response correlation and timeouts"""
    
    def __init__(self, default_timeout: float = 30.0):
        """
        Initialize request manager
        
        Args:
            default_timeout: Default timeout in seconds for requests
        """
        self.pending_requests = {}
        self.default_timeout = default_timeout
        self.tasks = {}
        
    async def register_request(
        self, 
        request_event_id: str, 
        callback: Callable[[Dict[str, Any]], Awaitable[None]],
        timeout: Optional[float] = None
    ) -> None:
        """
        Register a pending request with callback
        
        Args:
            request_event_id: Event ID of the request
            callback: Async callback function to call when response is received
            timeout: Optional timeout in seconds (default: self.default_timeout)
        """
        if not timeout:
            timeout = self.default_timeout
            
        logger.debug("Registering request", 
                     request_event_id=request_event_id,
                     timeout=timeout)
        
        self.pending_requests[request_event_id] = {
            "callback": callback,
            "timestamp": time.time(),
            "timeout": timeout
        }
        
        # Create timeout task
        self.tasks[request_event_id] = asyncio.create_task(
            self._handle_timeout(request_event_id, timeout)
        )
    
    async def _handle_timeout(self, request_event_id: str, timeout: float) -> None:
        """
        Handle request timeout
        
        Args:
            request_event_id: Event ID of the request
            timeout: Timeout in seconds
        """
        await asyncio.sleep(timeout)
        
        # Check if request is still pending (wasn't handled)
        if request_event_id in self.pending_requests:
            logger.warning("Request timed out", request_event_id=request_event_id)
            
            # Get callback
            request_info = self.pending_requests.pop(request_event_id)
            callback = request_info["callback"]
            
            # Call callback with timeout error
            await callback({
                "success": False,
                "error": {
                    "code": -32000,
                    "message": "Request timed out"
                },
                "request_event_id": request_event_id
            })
            
            # Clean up task
            if request_event_id in self.tasks:
                del self.tasks[request_event_id]
    
    async def handle_response(self, response: Dict[str, Any]) -> bool:
        """
        Process response and trigger appropriate callback
        
        Args:
            response: Parsed response data from DVMCPEventParser
            
        Returns:
            True if response was handled, False if no matching request
        """
        request_event_id = response["request_event_id"]
        
        logger.debug("Handling response", 
                     request_event_id=request_event_id,
                     success=response["success"])
        
        # Check if we have a pending request for this response
        if request_event_id not in self.pending_requests:
            logger.warning("Received response for unknown request", 
                          request_event_id=request_event_id)
            return False
        
        # Get request info and callback
        request_info = self.pending_requests.pop(request_event_id)
        callback = request_info["callback"]
        
        # Cancel timeout task
        if request_event_id in self.tasks:
            self.tasks[request_event_id].cancel()
            del self.tasks[request_event_id]
        
        # Call callback
        await callback(response)
        
        logger.info("Response handled", request_event_id=request_event_id)
        return True
    
    def clear(self) -> None:
        """Clear all pending requests and cancel timeout tasks"""
        logger.debug("Clearing all pending requests", 
                     count=len(self.pending_requests))
        
        # Cancel all timeout tasks
        for task in self.tasks.values():
            task.cancel()
            
        self.tasks.clear()
        self.pending_requests.clear()