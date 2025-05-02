import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple, Callable, Awaitable
from nostr_sdk import Keys, Client, Filter, SubscribeOptions, Event, Kind, NostrSigner, SingleLetterTag, Alphabet

from dvmcp.logging import get_logger
from dvmcp.protocol.event_builder import DVMCPEventBuilder
from dvmcp.protocol.event_parser import DVMCPEventParser
from dvmcp.protocol.request_manager import RequestManager
from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool, Resource, Prompt

logger = get_logger("client.dvmcp_client")

class DVMCPClient:
    """Main client for consuming MCP services via Nostr"""
    
    def __init__(
        self, 
        client_keys: 'Keys',
        client: Optional['Client'] = None,
        relays: Optional[List[str]] = None
    ):
        """
        Initialize DVMCP client
        
        Args:
            client_keys: Client keys for signing events
            client: Optional existing Nostr client
            relays: List of relay URLs to connect to (if client not provided)
        """
        self.keys = client_keys
        
        # Initialize Nostr client if not provided
        if client:
            self.client = client
        else:
            self.client = Client(NostrSigner.keys(self.keys))
            
            # Add relays if provided
            if relays:
                for relay in relays:
                    self.client.add_relay(relay)
        
        # Initialize request manager
        self.request_manager = RequestManager()
        
        # State for discovered servers
        self.discovered_servers = {}
        self.active_servers = {}
        
        # Callbacks for progress and payment handling
        self.progress_callbacks = {}
        self.payment_handler = None
        
        logger.info("DVMCP client initialized", 
                    pubkey=self.keys.public_key().to_hex())
    
    async def connect(self) -> None:
        """Connect to relays"""
        await self.client.connect()
        logger.info("Connected to relays")
    
    async def disconnect(self) -> None:
        """Disconnect from relays and cleanup"""
        # Clear all pending requests
        self.request_manager.clear()
        
        # Disconnect from relays
        await self.client.disconnect()
        logger.info("Disconnected from relays")
    
    async def discover_servers(
        self, 
        timeout: float = 5.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Discover servers matching specified filters
        
        Args:
            timeout: Timeout in seconds for discovery
            filters: Optional filters for server discovery (e.g., {"name": "ExampleServer"})
            
        Returns:
            Dictionary of discovered servers, keyed by server_id
        """
        logger.info("Discovering servers", timeout=timeout)
        
        # Create filter for server announcements
        server_filter = Filter().kind(Kind(31316))
        
        # Fetch server announcements
        from datetime import timedelta
        events = await self.client.fetch_events(server_filter, timedelta(seconds=timeout))
        
        discovered = {}
        count = 0
        
        # Process server announcements
        for event in events.to_vec():
            try:
                server_info = DVMCPEventParser.parse_server_announcement(event)
                
                # Apply filters if provided
                if filters:
                    match = True
                    for key, value in filters.items():
                        if key in server_info["metadata"] and server_info["metadata"][key] != value:
                            match = False
                            break
                    
                    if not match:
                        continue
                
                # Store discovered server
                server_id = server_info["server_id"]
                discovered[server_id] = server_info
                count += 1
                
                # Cache for later use
                self.discovered_servers[server_id] = server_info
                
            except ValueError as e:
                logger.warning("Failed to parse server announcement", 
                               event_id=event.id().to_hex(),
                               error=str(e))
        
        logger.info(f"Discovered {count} servers")
        return discovered
    
    async def connect_to_server(
        self, 
        server_id: Optional[str] = None,
        provider_pubkey: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Initialize connection to a specific server
        
        Args:
            server_id: Server identifier (optional if provider_pubkey is provided)
            provider_pubkey: Provider public key (optional if server_id is provided)
            timeout: Timeout in seconds for initialization
            
        Returns:
            Server capabilities and info
            
        Raises:
            ValueError: If neither server_id nor provider_pubkey is provided
            TimeoutError: If initialization times out
        """
        if not server_id and not provider_pubkey:
            raise ValueError("Either server_id or provider_pubkey must be provided")
        
        logger.info("Connecting to server", 
                   server_id=server_id, 
                   provider_pubkey=provider_pubkey)
        
        # Prepare client capabilities
        client_capabilities = {
            "prompts": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "tools": {"listChanged": True}
        }
        
        # Prepare client info
        client_info = {
            "name": "DVMCP Python Client",
            "version": "0.1.0"
        }
        
        # If server_id is provided and we have already discovered it,
        # we can skip initialization for public servers (direct discovery still needed)
        if server_id and server_id in self.discovered_servers:
            server_info = self.discovered_servers[server_id]
            self.active_servers[server_id] = server_info
            logger.info("Using discovered server", server_id=server_id)
            
            # Send initialized notification to complete connection
            await self._send_initialized_notification(server_id, server_info["provider_pubkey"])
            
            return server_info
        
        # For direct discovery or unknown servers, we need to initialize
        future = asyncio.Future()
        
        # Create and send initialization request
        init_params = {
            "protocolVersion": "2025-03-26",
            "capabilities": client_capabilities,
            "clientInfo": client_info
        }
        
        # Create request event
        request_event = DVMCPEventBuilder.create_request(
            client_keys=self.keys,
            method="initialize",
            params=init_params,
            provider_pubkey=provider_pubkey if provider_pubkey else "",
            server_id=server_id
        )
        
        # Register request callback
        async def on_init_response(response):
            if response.get("success", False):
                result = response["result"]
                
                # Extract server_id from response tags
                for tag in response.get("tags", []):
                    if tag[0] == "d":
                        server_id = tag[1]
                        break
                
                # Store server info
                server_info = {
                    "server_id": server_id,
                    "provider_pubkey": response["provider_pubkey"],
                    "protocol_version": result.get("protocolVersion"),
                    "capabilities": result.get("capabilities", {}),
                    "server_info": result.get("serverInfo", {}),
                    "instructions": result.get("instructions")
                }
                
                self.active_servers[server_id] = server_info
                
                # Send initialized notification
                await self._send_initialized_notification(
                    server_id, 
                    response["provider_pubkey"]
                )
                
                # Resolve future with server info
                future.set_result(server_info)
            else:
                error = response.get("error", {"message": "Unknown error"})
                future.set_exception(ValueError(f"Initialization failed: {error.get('message')}"))
        
        # Register request
        await self.request_manager.register_request(
            request_event_id=request_event.id().to_hex(),
            callback=on_init_response,
            timeout=timeout
        )
        
        # Send initialization request
        await self.client.send_event(request_event)
        
        # Setup subscription for responses
        sub_id = await self._subscribe_to_responses()
        
        # Wait for initialization response or timeout
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Initialization timed out after {timeout} seconds")
    
    async def _send_initialized_notification(
        self, 
        server_id: str, 
        provider_pubkey: str
    ) -> None:
        """
        Send initialized notification to server
        
        Args:
            server_id: Server identifier
            provider_pubkey: Provider public key
        """
        logger.debug("Sending initialized notification", 
                    server_id=server_id, 
                    provider_pubkey=provider_pubkey)
        
        # Create and send notification
        notification = DVMCPEventBuilder.create_notification(
            sender_keys=self.keys,
            target_pubkey=provider_pubkey,
            notification_type="notifications/initialized",
            server_id=server_id
        )
        
        await self.client.send_event(notification)
        
        logger.info("Sent initialized notification", 
                   server_id=server_id)
    
    async def _subscribe_to_responses(self) -> str:
        """
        Subscribe to response events
        
        Returns:
            Subscription ID
        """
        client_pubkey = self.keys.public_key().to_hex()
        
        # Create filter for responses (Event target = client's pubkey)
        response_filter = Filter().kind(Kind(26910)).pubkey(client_pubkey)
        
        # Create filter for notifications
        notification_filter = Filter().kind(Kind(21316)).pubkey(client_pubkey)
        
        # Create subscription for handling both
        sub_id = str(uuid.uuid4())
        await self.client.subscribe_with_id(
            id=sub_id,
            filter=[response_filter, notification_filter]
        )
        
        # Setup handler
        await self.client.handle_notifications(self._handle_notification)
        
        logger.debug("Subscribed to responses and notifications", 
                    subscription_id=sub_id)
        
        return sub_id
    
    async def _handle_notification(
        self, 
        relay_url: str, 
        subscription_id: str, 
        event: 'Event'
    ) -> None:
        """
        Handle incoming notifications and responses
        
        Args:
            relay_url: URL of the relay that sent the notification
            subscription_id: ID of the subscription
            event: Nostr event
        """
        try:
            kind = event.kind().as_u16()
            
            if kind == 26910:  # Response
                response = DVMCPEventParser.parse_response(event)
                await self.request_manager.handle_response(response)
            elif kind == 21316:  # Notification
                notification = DVMCPEventParser.parse_notification(event)
                await self._handle_notification_event(notification)
            
        except Exception as e:
            logger.error("Error handling event", 
                         event_id=event.id().to_hex(), 
                         error=str(e))
    
    async def _handle_notification_event(self, notification: Dict[str, Any]) -> None:
        """
        Handle notification events
        
        Args:
            notification: Parsed notification data
        """
        notification_type = notification.get("notification_type")
        if not notification_type:
            logger.warning("Notification without type", 
                          event_id=notification["event_id"])
            return
        
        logger.debug("Handling notification", 
                    notification_type=notification_type,
                    event_id=notification["event_id"])
        
        # Handle different notification types
        if notification_type.startswith("notifications/"):
            # MCP notifications
            if notification_type == "notifications/tools/list_changed":
                logger.info("Tools list changed notification received")
                server_id = notification.get("server_id")
                if server_id:
                    asyncio.create_task(self._refresh_tools_list(server_id))
            elif notification_type == "notifications/resources/list_changed":
                logger.info("Resources list changed notification received")
                server_id = notification.get("server_id")
                if server_id:
                    asyncio.create_task(self._refresh_resources_list(server_id))
            elif notification_type == "notifications/resources/updated":
                uri = notification.get("params", {}).get("uri")
                logger.info("Resource updated notification received", resource_uri=uri)
                server_id = notification.get("server_id")
                if uri and server_id:
                    asyncio.create_task(self._refresh_resource(uri, server_id))
            elif notification_type == "notifications/prompts/list_changed":
                logger.info("Prompts list changed notification received")
                server_id = notification.get("server_id")
                if server_id:
                    asyncio.create_task(self._refresh_prompts_list(server_id))
            elif notification_type == "notifications/progress":
                request_id = notification.get("params", {}).get("id")
                message = notification.get("params", {}).get("message")
                logger.info("Progress notification received",
                           request_id=request_id,
                           progress_message=message)
                # Call progress callback if registered
                if hasattr(self, "progress_callbacks") and request_id in self.progress_callbacks:
                    try:
                        await self.progress_callbacks[request_id](message)
                    except Exception as e:
                        logger.error("Error in progress callback",
                                    request_id=request_id,
                                    error=str(e))
        elif notification_type == "payment-required":
            # Payment required notification
            amount = notification.get("amount")
            bolt11 = notification.get("bolt11")
            request_event_id = notification.get("request_event_id")
            
            logger.info("Payment required notification received", 
                       amount=amount, 
                       request_event_id=request_event_id)
            # Call payment handler if registered
            if hasattr(self, "payment_handler") and self.payment_handler:
                try:
                    await self.payment_handler(amount, bolt11, request_event_id)
                except Exception as e:
                    logger.error("Error in payment handler",
                                request_event_id=request_event_id,
                                error=str(e))
    
    async def list_tools(
        self, 
        server_id: Optional[str] = None,
        cursor: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        List available tools from a server
        
        Args:
            server_id: Server identifier (defaults to first active server)
            cursor: Optional cursor for pagination
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with tools list and optional next cursor
            
        Raises:
            ValueError: If no server is active
            TimeoutError: If request times out
        """
        # Get server info
        server_info = await self._get_server_info(server_id)
        
        logger.info("Listing tools", 
                   server_id=server_info["server_id"])
        
        # Create request params
        params = {}
        if cursor:
            params["cursor"] = cursor
        
        # Create future for result
        future = asyncio.Future()
        
        # Create and send request
        request_event = DVMCPEventBuilder.create_request(
            client_keys=self.keys,
            method="tools/list",
            params=params,
            provider_pubkey=server_info["provider_pubkey"],
            server_id=server_info["server_id"]
        )
        
        # Register request callback
        async def on_list_response(response):
            if response.get("success", False):
                future.set_result(response["result"])
            else:
                error = response.get("error", {"message": "Unknown error"})
                future.set_exception(ValueError(f"Tools list failed: {error.get('message')}"))
        
        # Register request
        await self.request_manager.register_request(
            request_event_id=request_event.id().to_hex(),
            callback=on_list_response,
            timeout=timeout
        )
        
        # Send request
        await self.client.send_event(request_event)
        
        # Wait for response or timeout
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tools list request timed out after {timeout} seconds")
    
    async def call_tool(
        self, 
        name: str, 
        arguments: Dict[str, Any],
        server_id: Optional[str] = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Execute a tool with given arguments
        
        Args:
            name: Tool name
            arguments: Tool arguments
            server_id: Server identifier (defaults to first active server)
            timeout: Timeout in seconds
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If no server is active or tool execution fails
            TimeoutError: If request times out
        """
        # Get server info
        server_info = await self._get_server_info(server_id)
        
        logger.info("Calling tool", 
                   name=name, 
                   server_id=server_info["server_id"])
        
        # Create request params
        params = {
            "name": name,
            "arguments": arguments
        }
        
        # Create future for result
        future = asyncio.Future()
        
        # Create and send request
        request_event = DVMCPEventBuilder.create_request(
            client_keys=self.keys,
            method="tools/call",
            params=params,
            provider_pubkey=server_info["provider_pubkey"],
            server_id=server_info["server_id"]
        )
        
        # Register request callback
        async def on_tool_response(response):
            if response.get("success", False):
                result = response["result"]
                if result.get("isError", False):
                    # Tool executed but returned error
                    error_content = result.get("content", [{"text": "Unknown error"}])
                    error_message = error_content[0].get("text") if isinstance(error_content, list) else "Unknown error"
                    future.set_exception(ValueError(f"Tool execution error: {error_message}"))
                else:
                    future.set_result(result)
            else:
                error = response.get("error", {"message": "Unknown error"})
                future.set_exception(ValueError(f"Tool call failed: {error.get('message')}"))
        
        # Register request
        await self.request_manager.register_request(
            request_event_id=request_event.id().to_hex(),
            callback=on_tool_response,
            timeout=timeout
        )
        
        # Send request
        await self.client.send_event(request_event)
        
        # Wait for response or timeout
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool call timed out after {timeout} seconds")
    
    async def list_resources(
        self, 
        server_id: Optional[str] = None,
        cursor: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        List available resources from a server
        
        Args:
            server_id: Server identifier (defaults to first active server)
            cursor: Optional cursor for pagination
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with resources list and optional next cursor
            
        Raises:
            ValueError: If no server is active
            TimeoutError: If request times out
        """
        # Get server info
        server_info = await self._get_server_info(server_id)
        
        logger.info("Listing resources", 
                   server_id=server_info["server_id"])
        
        # Create request params
        params = {}
        if cursor:
            params["cursor"] = cursor
        
        # Create future for result
        future = asyncio.Future()
        
        # Create and send request
        request_event = DVMCPEventBuilder.create_request(
            client_keys=self.keys,
            method="resources/list",
            params=params,
            provider_pubkey=server_info["provider_pubkey"],
            server_id=server_info["server_id"]
        )
        
        # Register request callback
        async def on_list_response(response):
            if response.get("success", False):
                future.set_result(response["result"])
            else:
                error = response.get("error", {"message": "Unknown error"})
                future.set_exception(ValueError(f"Resources list failed: {error.get('message')}"))
        
        # Register request
        await self.request_manager.register_request(
            request_event_id=request_event.id().to_hex(),
            callback=on_list_response,
            timeout=timeout
        )
        
        # Send request
        await self.client.send_event(request_event)
        
        # Wait for response or timeout
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Resources list request timed out after {timeout} seconds")
    
    async def read_resource(
        self, 
        uri: str,
        server_id: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Read a resource by URI
        
        Args:
            uri: Resource URI
            server_id: Server identifier (defaults to first active server)
            timeout: Timeout in seconds
            
        Returns:
            Resource content
            
        Raises:
            ValueError: If no server is active or resource not found
            TimeoutError: If request times out
        """
        # Get server info
        server_info = await self._get_server_info(server_id)
        
        logger.info("Reading resource", 
                   uri=uri, 
                   server_id=server_info["server_id"])
        
        # Create request params
        params = {
            "uri": uri
        }
        
        # Create future for result
        future = asyncio.Future()
        
        # Create and send request
        request_event = DVMCPEventBuilder.create_request(
            client_keys=self.keys,
            method="resources/read",
            params=params,
            provider_pubkey=server_info["provider_pubkey"],
            server_id=server_info["server_id"]
        )
        
        # Register request callback
        async def on_read_response(response):
            if response.get("success", False):
                future.set_result(response["result"])
            else:
                error = response.get("error", {"message": "Unknown error"})
                future.set_exception(ValueError(f"Resource read failed: {error.get('message')}"))
        
        # Register request
        await self.request_manager.register_request(
            request_event_id=request_event.id().to_hex(),
            callback=on_read_response,
            timeout=timeout
        )
        
        # Send request
        await self.client.send_event(request_event)
        
        # Wait for response or timeout
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Resource read request timed out after {timeout} seconds")
    
    async def list_prompts(
        self, 
        server_id: Optional[str] = None,
        cursor: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        List available prompts from a server
        
        Args:
            server_id: Server identifier (defaults to first active server)
            cursor: Optional cursor for pagination
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with prompts list and optional next cursor
            
        Raises:
            ValueError: If no server is active
            TimeoutError: If request times out
        """
        # Get server info
        server_info = await self._get_server_info(server_id)
        
        logger.info("Listing prompts", 
                   server_id=server_info["server_id"])
        
        # Create request params
        params = {}
        if cursor:
            params["cursor"] = cursor
        
        # Create future for result
        future = asyncio.Future()
        
        # Create and send request
        request_event = DVMCPEventBuilder.create_request(
            client_keys=self.keys,
            method="prompts/list",
            params=params,
            provider_pubkey=server_info["provider_pubkey"],
            server_id=server_info["server_id"]
        )
        
        # Register request callback
        async def on_list_response(response):
            if response.get("success", False):
                future.set_result(response["result"])
            else:
                error = response.get("error", {"message": "Unknown error"})
                future.set_exception(ValueError(f"Prompts list failed: {error.get('message')}"))
        
        # Register request
        await self.request_manager.register_request(
            request_event_id=request_event.id().to_hex(),
            callback=on_list_response,
            timeout=timeout
        )
        
        # Send request
        await self.client.send_event(request_event)
        
        # Wait for response or timeout
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Prompts list request timed out after {timeout} seconds")
    
    async def get_prompt(
        self, 
        name: str,
        arguments: Dict[str, Any],
        server_id: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Get a prompt with given arguments
        
        Args:
            name: Prompt name
            arguments: Prompt arguments
            server_id: Server identifier (defaults to first active server)
            timeout: Timeout in seconds
            
        Returns:
            Prompt content
            
        Raises:
            ValueError: If no server is active or prompt not found
            TimeoutError: If request times out
        """
        # Get server info
        server_info = await self._get_server_info(server_id)
        
        logger.info("Getting prompt", 
                   name=name, 
                   server_id=server_info["server_id"])
        
        # Create request params
        params = {
            "name": name,
            "arguments": arguments
        }
        
        # Create future for result
        future = asyncio.Future()
        
        # Create and send request
        request_event = DVMCPEventBuilder.create_request(
            client_keys=self.keys,
            method="prompts/get",
            params=params,
            provider_pubkey=server_info["provider_pubkey"],
            server_id=server_info["server_id"]
        )
        
        # Register request callback
        async def on_get_response(response):
            if response.get("success", False):
                future.set_result(response["result"])
            else:
                error = response.get("error", {"message": "Unknown error"})
                future.set_exception(ValueError(f"Prompt get failed: {error.get('message')}"))
        
        # Register request
        await self.request_manager.register_request(
            request_event_id=request_event.id().to_hex(),
            callback=on_get_response,
            timeout=timeout
        )
        
        # Send request
        await self.client.send_event(request_event)
        
        # Wait for response or timeout
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Prompt get request timed out after {timeout} seconds")
    
    async def _get_server_info(self, server_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get server info for a specific server or the first active server
        
        Args:
            server_id: Optional server identifier
            
        Returns:
            Server info
            
        Raises:
            ValueError: If no server is active or specified server not found
        """
        if not self.active_servers:
            raise ValueError("No active servers. Call connect_to_server() first.")
        
        if server_id:
            if server_id not in self.active_servers:
                raise ValueError(f"Server {server_id} not found in active servers")
            return self.active_servers[server_id]
        else:
            # Use first active server
            return next(iter(self.active_servers.values()))
    
    def register_progress_callback(self, request_id: str, callback: Callable[[str], Awaitable[None]]) -> None:
        """
        Register a callback for progress notifications
        
        Args:
            request_id: Request ID to receive progress updates for
            callback: Async function that takes a message string
        """
        self.progress_callbacks[request_id] = callback
        logger.debug("Progress callback registered", request_id=request_id)
    
    def unregister_progress_callback(self, request_id: str) -> None:
        """
        Unregister a progress callback
        
        Args:
            request_id: Request ID to stop receiving progress updates for
        """
        if request_id in self.progress_callbacks:
            del self.progress_callbacks[request_id]
            logger.debug("Progress callback unregistered", request_id=request_id)
    
    def register_payment_handler(self, handler: Callable[[int, str, str], Awaitable[None]]) -> None:
        """
        Register a handler for payment required notifications
        
        Args:
            handler: Async function that takes amount, bolt11, and request_event_id
        """
        self.payment_handler = handler
        logger.debug("Payment handler registered")
    
    def unregister_payment_handler(self) -> None:
        """
        Unregister the payment handler
        """
        self.payment_handler = None
        logger.debug("Payment handler unregistered")
    
    async def _refresh_tools_list(self, server_id: str) -> None:
        """
        Refresh tools list for a server
        
        Args:
            server_id: Server identifier
        """
        try:
            logger.info("Refreshing tools list", server_id=server_id)
            tools_list = await self.list_tools(server_id)
            logger.info("Tools list refreshed",
                       server_id=server_id,
                       tools_count=len(tools_list.get("tools", [])))
        except Exception as e:
            logger.error("Failed to refresh tools list",
                        server_id=server_id,
                        error=str(e))
    
    async def _refresh_resources_list(self, server_id: str) -> None:
        """
        Refresh resources list for a server
        
        Args:
            server_id: Server identifier
        """
        try:
            logger.info("Refreshing resources list", server_id=server_id)
            resources_list = await self.list_resources(server_id)
            logger.info("Resources list refreshed",
                       server_id=server_id,
                       resources_count=len(resources_list.get("resources", [])))
        except Exception as e:
            logger.error("Failed to refresh resources list",
                        server_id=server_id,
                        error=str(e))
    
    async def _refresh_resource(self, uri: str, server_id: str) -> None:
        """
        Refresh a specific resource
        
        Args:
            uri: Resource URI
            server_id: Server identifier
        """
        try:
            logger.info("Refreshing resource", uri=uri, server_id=server_id)
            resource = await self.read_resource(uri, server_id)
            logger.info("Resource refreshed", uri=uri, server_id=server_id)
        except Exception as e:
            logger.error("Failed to refresh resource",
                        uri=uri,
                        server_id=server_id,
                        error=str(e))
    
    async def _refresh_prompts_list(self, server_id: str) -> None:
        """
        Refresh prompts list for a server
        
        Args:
            server_id: Server identifier
        """
        try:
            logger.info("Refreshing prompts list", server_id=server_id)
            prompts_list = await self.list_prompts(server_id)
            logger.info("Prompts list refreshed",
                       server_id=server_id,
                       prompts_count=len(prompts_list.get("prompts", [])))
        except Exception as e:
            logger.error("Failed to refresh prompts list",
                        server_id=server_id,
                        error=str(e))