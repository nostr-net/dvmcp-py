import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple, Callable, Awaitable
from nostr_sdk import Keys, Client, Filter, Event, Kind, NostrSigner, SingleLetterTag, Alphabet

from dvmcp.logging import get_logger
from dvmcp.protocol.event_builder import DVMCPEventBuilder
from dvmcp.protocol.event_parser import DVMCPEventParser
from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool, Resource, Prompt

logger = get_logger("provider.dvmcp_provider")

class DVMCPProvider:
    """Main provider for exposing MCP services via Nostr"""
    
    def __init__(
        self, 
        provider_keys: 'Keys',
        client: Optional['Client'] = None,
        relays: Optional[List[str]] = None
    ):
        """
        Initialize DVMCP provider
        
        Args:
            provider_keys: Provider keys for signing events
            client: Optional existing Nostr client
            relays: List of relay URLs to connect to (if client not provided)
        """
        self.keys = provider_keys
        
        # Initialize Nostr client if not provided
        if client:
            self.client = client
        else:
            self.client = Client(NostrSigner.keys(self.keys))
            
            # Add relays if provided
            if relays:
                for relay in relays:
                    self.client.add_relay(relay)
        
        # State for announced servers
        self.announced_servers = {}
        self.request_handlers = {}
        
        logger.info("DVMCP provider initialized", 
                    pubkey=self.keys.public_key().to_hex())
    
    async def connect(self) -> None:
        """Connect to relays"""
        await self.client.connect()
        logger.info("Connected to relays")
    
    async def disconnect(self) -> None:
        """Disconnect from relays and cleanup"""
        await self.client.disconnect()
        logger.info("Disconnected from relays")
    
    async def announce_server(
        self, 
        server_id: str,
        server_info: Union[ServerInfo, Dict[str, Any]],
        capabilities: Union[ServerCapabilities, Dict[str, Any]]
    ) -> str:
        """
        Publish server announcement to relays
        
        Args:
            server_id: Unique server identifier
            server_info: Server metadata
            capabilities: Server capabilities
            
        Returns:
            Event ID of the announcement
        """
        logger.info("Announcing server", 
                   server_id=server_id)
        
        # Create announcement event
        event = DVMCPEventBuilder.create_server_announcement(
            provider_keys=self.keys,
            server_info=server_info,
            capabilities=capabilities,
            server_id=server_id
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        # Store announced server
        self.announced_servers[server_id] = {
            "event_id": event.id().to_hex(),
            "server_id": server_id,
            "server_info": server_info,
            "capabilities": capabilities
        }
        
        logger.info("Server announced", 
                   server_id=server_id,
                   event_id=event.id().to_hex())
        
        return event.id().to_hex()
    
    async def publish_tools_list(
        self, 
        tools: List[Union[Tool, Dict[str, Any]]],
        server_id: str,
        list_id: Optional[str] = None
    ) -> str:
        """
        Publish list of available tools
        
        Args:
            tools: List of tools
            server_id: Server identifier
            list_id: Optional unique identifier for the list
            
        Returns:
            Event ID of the published list
        """
        logger.info("Publishing tools list", 
                   server_id=server_id,
                   tools_count=len(tools))
        
        # Create tools list event
        event = DVMCPEventBuilder.create_tools_list(
            provider_keys=self.keys,
            tools=tools,
            server_id=server_id,
            list_id=list_id
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        logger.info("Tools list published", 
                   server_id=server_id,
                   event_id=event.id().to_hex(),
                   tools_count=len(tools))
        
        return event.id().to_hex()
    
    async def publish_resources_list(
        self, 
        resources: List[Union[Resource, Dict[str, Any]]],
        server_id: str,
        list_id: Optional[str] = None
    ) -> str:
        """
        Publish list of available resources
        
        Args:
            resources: List of resources
            server_id: Server identifier
            list_id: Optional unique identifier for the list
            
        Returns:
            Event ID of the published list
        """
        logger.info("Publishing resources list", 
                   server_id=server_id,
                   resources_count=len(resources))
        
        # Create resources list event
        event = DVMCPEventBuilder.create_resources_list(
            provider_keys=self.keys,
            resources=resources,
            server_id=server_id,
            list_id=list_id
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        logger.info("Resources list published", 
                   server_id=server_id,
                   event_id=event.id().to_hex(),
                   resources_count=len(resources))
        
        return event.id().to_hex()
    
    async def publish_prompts_list(
        self, 
        prompts: List[Union[Prompt, Dict[str, Any]]],
        server_id: str,
        list_id: Optional[str] = None
    ) -> str:
        """
        Publish list of available prompts
        
        Args:
            prompts: List of prompts
            server_id: Server identifier
            list_id: Optional unique identifier for the list
            
        Returns:
            Event ID of the published list
        """
        logger.info("Publishing prompts list", 
                   server_id=server_id,
                   prompts_count=len(prompts))
        
        # Create prompts list event
        event = DVMCPEventBuilder.create_prompts_list(
            provider_keys=self.keys,
            prompts=prompts,
            server_id=server_id,
            list_id=list_id
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        logger.info("Prompts list published", 
                   server_id=server_id,
                   event_id=event.id().to_hex(),
                   prompts_count=len(prompts))
        
        return event.id().to_hex()
    
    async def handle_requests(
        self, 
        server_id: str,
        callback: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> None:
        """
        Register callback for handling client requests
        
        Args:
            server_id: Server identifier
            callback: Async function that takes request object and returns response object
        """
        logger.info("Setting up request handler", server_id=server_id)
        
        # Store callback
        self.request_handlers[server_id] = callback
        
        # Create filter for requests targeting this server or provider
        provider_pubkey = self.keys.public_key().to_hex()
        
        # Create filter for direct server requests
        server_filter = Filter().kind(Kind(25910)).custom_tag(SingleLetterTag.lowercase(Alphabet.S), server_id)
        
        # Create filter for provider requests (without server_id)
        provider_filter = Filter().kind(Kind(25910)).custom_tag(SingleLetterTag.lowercase(Alphabet.P), provider_pubkey)
        
        # Create filter for client notifications
        notification_filter = Filter().kind(Kind(21316)).custom_tag(SingleLetterTag.lowercase(Alphabet.S), server_id)
        
        # Create subscription ID for each
        server_sub_id = f"server-{server_id}"
        provider_sub_id = f"provider-{provider_pubkey}"
        notification_sub_id = f"notifications-{server_id}"
        
        # Subscribe to requests and notifications
        await self.client.subscribe_with_id(id=server_sub_id, filter=server_filter)
        await self.client.subscribe_with_id(id=provider_sub_id, filter=provider_filter)
        await self.client.subscribe_with_id(id=notification_sub_id, filter=notification_filter)
        
        # Setup handler
        await self.client.handle_notifications(self._handle_notification)
        
        logger.info("Request handler set up", 
                   server_id=server_id,
                   subscriptions=[server_sub_id, provider_sub_id, notification_sub_id])
    
    async def _handle_notification(
        self, 
        relay_url: str, 
        subscription_id: str, 
        event: 'Event'
    ) -> None:
        """
        Handle incoming requests and notifications
        
        Args:
            relay_url: URL of the relay that sent the notification
            subscription_id: ID of the subscription
            event: Nostr event
        """
        try:
            kind = event.kind().as_u16()
            
            if kind == 25910:  # Request
                request = DVMCPEventParser.parse_request(event)
                await self._handle_request_event(request)
            elif kind == 21316:  # Notification
                notification = DVMCPEventParser.parse_notification(event)
                await self._handle_notification_event(notification)
            
        except Exception as e:
            logger.error("Error handling event", 
                         event_id=event.id().to_hex(), 
                         error=str(e))
    
    async def _handle_request_event(self, request: Dict[str, Any]) -> None:
        """
        Handle request events
        
        Args:
            request: Parsed request data
        """
        server_id = request.get("server_id")
        method = request.get("method")
        
        logger.debug("Handling request", 
                    method=method,
                    server_id=server_id,
                    request_id=request.get("request_id"),
                    event_id=request.get("event_id"))
        
        # Handle initialization requests specially
        if method == "initialize":
            await self._handle_initialization(request)
            return
        
        # Find appropriate handler
        handler = None
        if server_id and server_id in self.request_handlers:
            handler = self.request_handlers[server_id]
        elif not server_id:
            # Request to provider without server_id
            # Use the first handler if available
            if self.request_handlers:
                handler = next(iter(self.request_handlers.values()))
                
                # Update request with server_id from first server
                first_server_id = next(iter(self.request_handlers.keys()))
                request["server_id"] = first_server_id
        
        if not handler:
            logger.warning("No handler for request", 
                          method=method,
                          server_id=server_id)
            
            # Send error response
            await self.send_error_response(
                request_event_id=request["event_id"],
                error_code=-32601,
                error_message=f"Server not found: {server_id}",
                request_id=request["request_id"]
            )
            return
        
        try:
            # Call handler
            response = await handler(request)
            
            # Send response
            await self.send_response(
                request_event=request,
                result=response
            )
            
            logger.info("Request handled successfully", 
                       method=method,
                       request_id=request.get("request_id"))
        except Exception as e:
            logger.error("Error handling request", 
                        method=method,
                        request_id=request.get("request_id"),
                        error=str(e))
            
            # Send error response
            await self.send_error_response(
                request_event_id=request["event_id"],
                error_code=-32603,
                error_message=f"Internal error: {str(e)}",
                request_id=request["request_id"]
            )
    
    async def _handle_initialization(self, request: Dict[str, Any]) -> None:
        """
        Handle initialization requests
        
        Args:
            request: Parsed initialization request
        """
        logger.info("Handling initialization request", 
                   client_pubkey=request.get("client_pubkey"))
        
        # Get server_id from request or use the first server
        server_id = request.get("server_id")
        if not server_id and self.announced_servers:
            server_id = next(iter(self.announced_servers.keys()))
            
        if not server_id:
            logger.warning("No server available for initialization")
            
            # Send error response
            await self.send_error_response(
                request_event_id=request["event_id"],
                error_code=-32603,
                error_message="No server available",
                request_id=request["request_id"]
            )
            return
        
        # Get server info
        server_info = self.announced_servers.get(server_id)
        if not server_info:
            logger.warning("Server not found", server_id=server_id)
            
            # Send error response
            await self.send_error_response(
                request_event_id=request["event_id"],
                error_code=-32601,
                error_message=f"Server not found: {server_id}",
                request_id=request["request_id"]
            )
            return
        
        # Send initialization response
        await self.send_response(
            request_event=request,
            result={
                "status": "ok",
                "server_id": server_id,
                "server_info": server_info["server_info"],
                "capabilities": server_info["capabilities"]
            }
        )
        
        logger.info("Initialization request handled",
                   client_pubkey=request.get("client_pubkey"),
                   server_id=server_id)
    
    async def _handle_notification_event(self, notification: Dict[str, Any]) -> None:
        """
        Handle notification events
        
        Args:
            notification: Parsed notification data
        """
        notification_type = notification.get("notification_type")
        server_id = notification.get("server_id")
        
        logger.debug("Handling notification",
                    notification_type=notification_type,
                    server_id=server_id,
                    event_id=notification.get("event_id"))
        
        # Handle different notification types
        if notification_type == "payment-received" and "request_event_id" in notification:
            # Payment received notification
            await self._handle_payment_received(notification)
        elif notification_type == "client/disconnect":
            # Client disconnect notification
            logger.info("Client disconnected",
                       client_pubkey=notification.get("sender_pubkey"))
        else:
            # Forward notification to appropriate handler if available
            if server_id and server_id in self.request_handlers:
                try:
                    await self.request_handlers[server_id](notification)
                except Exception as e:
                    logger.error("Error handling notification",
                                notification_type=notification_type,
                                error=str(e))
    
    async def _handle_payment_received(self, notification: Dict[str, Any]) -> None:
        """
        Handle payment received notification
        
        Args:
            notification: Parsed payment notification data
        """
        request_event_id = notification.get("request_event_id")
        
        logger.info("Payment received",
                   request_event_id=request_event_id,
                   amount=notification.get("params", {}).get("amount"))
        
        # Additional payment processing logic can be added here
    
    async def send_response(self, request_event: Dict[str, Any], result: Dict[str, Any]) -> str:
        """
        Send response to a client request
        
        Args:
            request_event: Parsed request event
            result: Response result object
            
        Returns:
            Event ID of the response
        """
        logger.debug("Sending response",
                    request_id=request_event.get("request_id"),
                    request_event_id=request_event.get("event_id"))
        
        # Create response event
        event = DVMCPEventBuilder.create_response(
            provider_keys=self.keys,
            request_event_id=request_event["event_id"],
            result=result,
            request_id=request_event["request_id"]
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        logger.info("Response sent",
                   request_id=request_event.get("request_id"),
                   response_event_id=event.id().to_hex())
        
        return event.id().to_hex()
    
    async def send_error_response(
        self,
        request_event_id: str,
        error_code: int,
        error_message: str,
        request_id: Optional[int] = None
    ) -> str:
        """
        Send error response to a client request
        
        Args:
            request_event_id: Event ID of the request
            error_code: JSON-RPC error code
            error_message: Error message
            request_id: Request ID from the original request
            
        Returns:
            Event ID of the error response
        """
        logger.debug("Sending error response",
                    request_event_id=request_event_id,
                    error_code=error_code)
        
        # Create error response event
        event = DVMCPEventBuilder.create_error_response(
            provider_keys=self.keys,
            request_event_id=request_event_id,
            error_code=error_code,
            error_message=error_message,
            request_id=request_id
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        logger.info("Error response sent",
                   request_event_id=request_event_id,
                   error_code=error_code,
                   response_event_id=event.id().to_hex())
        
        return event.id().to_hex()
    
    async def send_notification(
        self,
        target_pubkey: str,
        notification_type: str,
        params: Optional[Dict[str, Any]] = None,
        server_id: Optional[str] = None,
        request_event_id: Optional[str] = None
    ) -> str:
        """
        Send notification to a client
        
        Args:
            target_pubkey: Target client's public key
            notification_type: Notification type
            params: Optional notification parameters
            server_id: Optional server identifier
            request_event_id: Optional reference to request event
            
        Returns:
            Event ID of the notification
        """
        logger.debug("Sending notification",
                    notification_type=notification_type,
                    target=target_pubkey)
        
        # Create notification event
        event = DVMCPEventBuilder.create_notification(
            sender_keys=self.keys,
            target_pubkey=target_pubkey,
            notification_type=notification_type,
            params=params,
            server_id=server_id,
            request_event_id=request_event_id
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        logger.info("Notification sent",
                   notification_type=notification_type,
                   target=target_pubkey,
                   notification_event_id=event.id().to_hex())
        
        return event.id().to_hex()
    
    async def send_payment_required_notification(
        self,
        client_pubkey: str,
        request_event_id: str,
        amount: int,
        bolt11: str
    ) -> str:
        """
        Send payment required notification to a client
        
        Args:
            client_pubkey: Client's public key
            request_event_id: Event ID of the request requiring payment
            amount: Payment amount in millisats
            bolt11: Lightning invoice
            
        Returns:
            Event ID of the notification
        """
        logger.debug("Sending payment required notification",
                    request_event_id=request_event_id,
                    amount=amount)
        
        # Create payment required notification event
        event = DVMCPEventBuilder.create_payment_required_notification(
            provider_keys=self.keys,
            client_pubkey=client_pubkey,
            request_event_id=request_event_id,
            amount=amount,
            bolt11=bolt11
        )
        
        # Send event to relays
        await self.client.send_event(event)
        
        logger.info("Payment required notification sent",
                   request_event_id=request_event_id,
                   amount=amount,
                   notification_event_id=event.id().to_hex())
        
        return event.id().to_hex()