"""
Resources implementation for DVMCP

This module provides base classes and utilities for implementing MCP resources.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, List, Union

from dvmcp.logging import get_logger
from dvmcp.models.capabilities import Resource

logger = get_logger("capabilities.resources")

class ResourceRegistry:
    """Registry for resource implementations"""
    
    def __init__(self):
        """Initialize resource registry"""
        self.resources: Dict[str, 'ResourceImplementation'] = {}
    
    def register(self, resource_impl: 'ResourceImplementation') -> None:
        """
        Register a resource implementation
        
        Args:
            resource_impl: Resource implementation to register
        """
        self.resources[resource_impl.resource.uri] = resource_impl
        logger.debug(f"Registered resource: {resource_impl.resource.uri}")
    
    def get(self, uri: str) -> Optional['ResourceImplementation']:
        """
        Get resource implementation by URI
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource implementation or None if not found
        """
        return self.resources.get(uri)
    
    def list_resources(self) -> List[Resource]:
        """
        Get list of all registered resources
        
        Returns:
            List of resource definitions
        """
        return [impl.resource for impl in self.resources.values()]

class ResourceImplementation:
    """Base class for resource implementations"""
    
    def __init__(self, resource: Resource):
        """
        Initialize resource implementation
        
        Args:
            resource: Resource definition
        """
        self.resource = resource
    
    async def read(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Read resource content
        
        Args:
            params: Optional parameters for reading the resource
            
        Returns:
            Resource content
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Resource reading not implemented")
    
    async def subscribe(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> str:
        """
        Subscribe to resource updates
        
        Args:
            callback: Async callback function to call when resource is updated
            
        Returns:
            Subscription ID
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Resource subscription not implemented")
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from resource updates
        
        Args:
            subscription_id: Subscription ID returned from subscribe
            
        Returns:
            True if unsubscribed successfully, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Resource unsubscription not implemented")

class SystemInfoResource(ResourceImplementation):
    """Example system info resource implementation"""
    
    def __init__(self):
        """Initialize system info resource"""
        super().__init__(Resource(
            uri="system://info",
            name="System Information",
            description="System information and status",
            mime_type="application/json"
        ))
        self.subscribers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
    
    async def read(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Read system information
        
        Args:
            params: Optional parameters (unused)
            
        Returns:
            System information
        """
        import platform
        import psutil
        
        logger.debug("Reading system information")
        
        try:
            # Basic system info
            info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "free": psutil.disk_usage('/').free
                }
            }
            return {"content": info}
        except ImportError:
            # Fallback if psutil is not available
            return {
                "content": {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "note": "Install psutil for more detailed system information"
                }
            }
    
    async def subscribe(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> str:
        """
        Subscribe to system info updates
        
        Args:
            callback: Async callback function to call when system info is updated
            
        Returns:
            Subscription ID
        """
        import uuid
        
        subscription_id = str(uuid.uuid4())
        self.subscribers[subscription_id] = callback
        logger.debug(f"Subscribed to system info: {subscription_id}")
        
        # Initial update
        info = await self.read()
        await callback(info)
        
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from system info updates
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        if subscription_id in self.subscribers:
            del self.subscribers[subscription_id]
            logger.debug(f"Unsubscribed from system info: {subscription_id}")
            return True
        return False

# Create global resource registry
registry = ResourceRegistry()

# Register built-in resources
try:
    registry.register(SystemInfoResource())
except Exception as e:
    logger.warning(f"Failed to register SystemInfoResource: {e}")