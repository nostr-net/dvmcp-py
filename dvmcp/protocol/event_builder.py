# dvmcp/protocol/event_builder.py
import json
from typing import Dict, List, Optional, Any, Union
from nostr_sdk import EventBuilder, Tag, Kind, Keys, Event

from dvmcp.logging import get_logger
from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool, Resource, Prompt

logger = get_logger("protocol.event_builder")

class DVMCPEventBuilder:
    """Creates properly formatted DVMCP events with validation"""
    
    # Event kinds defined in DVMCP spec
    SERVER_ANNOUNCEMENT_KIND = 31316
    TOOLS_LIST_KIND = 31317
    RESOURCES_LIST_KIND = 31318
    PROMPTS_LIST_KIND = 31319
    REQUEST_KIND = 25910
    RESPONSE_KIND = 26910
    NOTIFICATION_KIND = 21316
    
    @staticmethod
    def create_server_announcement(
        provider_keys: 'Keys',
        server_info: Union[ServerInfo, Dict[str, Any]],
        capabilities: Union[ServerCapabilities, Dict[str, Any]],
        server_id: str
    ) -> 'Event':
        """
        Create server announcement event (kind 31316)
        
        Args:
            provider_keys: Provider's keys for signing
            server_info: Server metadata (either ServerInfo object or dict)
            capabilities: Server capabilities (either ServerCapabilities object or dict)
            server_id: Unique server identifier
            
        Returns:
            Signed server announcement event
        """
        logger.debug("Creating server announcement event", 
                    server_id=server_id, 
                    provider=provider_keys.public_key().to_hex())
        
        # Validate inputs
        if not server_id:
            raise ValueError("Server ID is required")
        
        # Convert objects to dicts if needed
        if isinstance(server_info, ServerInfo):
            server_info_dict = server_info.to_dict()
        else:
            server_info_dict = server_info
            
        if isinstance(capabilities, ServerCapabilities):
            capabilities_dict = capabilities.to_dict()
        else:
            capabilities_dict = capabilities
        
        # Create content as JSON-RPC 2.0 response
        content = {
            "jsonrpc": "2.0",
            "id": 1,  # Convention for announcement
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": capabilities_dict,
                "serverInfo": server_info_dict
            }
        }
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["d", server_id]),     # Required: server identifier
            Tag.parse(["k", "25910"]),       # Required: accepted request kind
        ]
        
        # Add optional tags if provided
        if "name" in server_info_dict:
            tags.append(Tag.parse(["name", server_info_dict["name"]]))
        
        if "description" in server_info_dict:
            tags.append(Tag.parse(["about", server_info_dict["description"]]))
            
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.SERVER_ANNOUNCEMENT_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
        
        event = builder.sign_with_keys(provider_keys)
        
        logger.info("Server announcement event created", 
                   event_id=event.id().to_hex(),
                   server_id=server_id)
        
        return event
    
    @staticmethod
    def create_tools_list(
        provider_keys: 'Keys',
        tools: List[Union[Tool, Dict[str, Any]]],
        server_id: str,
        list_id: Optional[str] = None
    ) -> 'Event':
        """
        Create tools list event (kind 31317)
        
        Args:
            provider_keys: Provider's keys for signing
            tools: List of tools (either Tool objects or dicts)
            server_id: Server identifier this list belongs to
            list_id: Unique identifier for this list (defaults to server_id)
            
        Returns:
            Signed tools list event
        """
        logger.debug("Creating tools list event", 
                     server_id=server_id,
                     tools_count=len(tools))
        
        # Use server_id as list_id if not provided
        if not list_id:
            list_id = server_id
        
        # Convert tools to dicts if needed
        tools_dicts = []
        for tool in tools:
            if isinstance(tool, Tool):
                tools_dicts.append(tool.to_dict())
            else:
                tools_dicts.append(tool)
        
        # Create content as JSON-RPC 2.0 response
        content = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": tools_dicts
            }
        }
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["d", list_id]),      # Required: Unique identifier for this list
            Tag.parse(["s", server_id]),    # Required: Server identifier
        ]
        
        # Add cap tags for each tool
        for tool in tools_dicts:
            if "name" in tool:
                tags.append(Tag.parse(["cap", tool["name"]]))
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.TOOLS_LIST_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(provider_keys)
        
        logger.info("Tools list event created", 
                    event_id=event.id().to_hex(),
                    server_id=server_id,
                    tools_count=len(tools))
        
        return event
    
    @staticmethod
    def create_resources_list(
        provider_keys: 'Keys',
        resources: List[Union[Resource, Dict[str, Any]]],
        server_id: str,
        list_id: Optional[str] = None
    ) -> 'Event':
        """
        Create resources list event (kind 31318)
        
        Args:
            provider_keys: Provider's keys for signing
            resources: List of resources (either Resource objects or dicts)
            server_id: Server identifier this list belongs to
            list_id: Unique identifier for this list (defaults to server_id)
            
        Returns:
            Signed resources list event
        """
        logger.debug("Creating resources list event", 
                     server_id=server_id,
                     resources_count=len(resources))
        
        # Use server_id as list_id if not provided
        if not list_id:
            list_id = server_id
        
        # Convert resources to dicts if needed
        resources_dicts = []
        for resource in resources:
            if isinstance(resource, Resource):
                resources_dicts.append(resource.to_dict())
            else:
                resources_dicts.append(resource)
        
        # Create content as JSON-RPC 2.0 response
        content = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "resources": resources_dicts
            }
        }
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["d", list_id]),      # Required: Unique identifier for this list
            Tag.parse(["s", server_id]),    # Required: Server identifier
        ]
        
        # Add cap tags for each resource
        for resource in resources_dicts:
            if "name" in resource:
                tags.append(Tag.parse(["cap", resource["name"]]))
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.RESOURCES_LIST_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(provider_keys)
        
        logger.info("Resources list event created", 
                    event_id=event.id().to_hex(),
                    server_id=server_id,
                    resources_count=len(resources))
        
        return event
    
    @staticmethod
    def create_prompts_list(
        provider_keys: 'Keys',
        prompts: List[Union[Prompt, Dict[str, Any]]],
        server_id: str,
        list_id: Optional[str] = None
    ) -> 'Event':
        """
        Create prompts list event (kind 31319)
        
        Args:
            provider_keys: Provider's keys for signing
            prompts: List of prompts (either Prompt objects or dicts)
            server_id: Server identifier this list belongs to
            list_id: Unique identifier for this list (defaults to server_id)
            
        Returns:
            Signed prompts list event
        """
        logger.debug("Creating prompts list event", 
                     server_id=server_id,
                     prompts_count=len(prompts))
        
        # Use server_id as list_id if not provided
        if not list_id:
            list_id = server_id
        
        # Convert prompts to dicts if needed
        prompts_dicts = []
        for prompt in prompts:
            if isinstance(prompt, Prompt):
                prompts_dicts.append(prompt.to_dict())
            else:
                prompts_dicts.append(prompt)
        
        # Create content as JSON-RPC 2.0 response
        content = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "prompts": prompts_dicts
            }
        }
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["d", list_id]),      # Required: Unique identifier for this list
            Tag.parse(["s", server_id]),    # Required: Server identifier
        ]
        
        # Add cap tags for each prompt
        for prompt in prompts_dicts:
            if "name" in prompt:
                tags.append(Tag.parse(["cap", prompt["name"]]))
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.PROMPTS_LIST_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(provider_keys)
        
        logger.info("Prompts list event created", 
                    event_id=event.id().to_hex(),
                    server_id=server_id,
                    prompts_count=len(prompts))
        
        return event
    
    @staticmethod
    def create_request(
        client_keys: 'Keys',
        method: str,
        params: Dict[str, Any],
        provider_pubkey: str,
        server_id: Optional[str] = None,
        request_id: Optional[int] = None
    ) -> 'Event':
        """
        Create client request event (kind 25910)
        
        Args:
            client_keys: Client's keys for signing
            method: MCP method name
            params: Method parameters
            provider_pubkey: Provider's public key (hex or bech32)
            server_id: Optional server identifier for targeting specific server
            request_id: Optional custom request ID (default: 1)
            
        Returns:
            Signed request event
        """
        logger.debug("Creating request event", 
                     method=method,
                     provider=provider_pubkey)
        
        # Create content as JSON-RPC 2.0 request
        content = {
            "jsonrpc": "2.0",
            "id": request_id or 1,
            "method": method,
            "params": params
        }
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["p", provider_pubkey]),    # Required: Provider public key
            Tag.parse(["method", method]),        # Required: Method name for filtering
        ]
        
        # Add server_id tag if provided
        if server_id:
            tags.append(Tag.parse(["s", server_id]))
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.REQUEST_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(client_keys)
        
        logger.info("Request event created", 
                    event_id=event.id().to_hex(),
                    method=method)
        
        return event
    
    @staticmethod
    def create_response(
        provider_keys: 'Keys',
        request_event_id: str,
        result: Dict[str, Any],
        request_id: Optional[int] = None
    ) -> 'Event':
        """
        Create response event (kind 26910)
        
        Args:
            provider_keys: Provider's keys for signing
            request_event_id: Event ID of the request being responded to
            result: Response result object
            request_id: Request ID from the original request (default: 1)
            
        Returns:
            Signed response event
        """
        logger.debug("Creating response event", 
                     request_event_id=request_event_id)
        
        # Create content as JSON-RPC 2.0 response
        content = {
            "jsonrpc": "2.0",
            "id": request_id or 1,
            "result": result
        }
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["e", request_event_id]),  # Required: Reference to request
        ]
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.RESPONSE_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(provider_keys)
        
        logger.info("Response event created", 
                    event_id=event.id().to_hex(),
                    request_event_id=request_event_id)
        
        return event
    
    @staticmethod
    def create_error_response(
        provider_keys: 'Keys',
        request_event_id: str,
        error_code: int,
        error_message: str,
        request_id: Optional[int] = None
    ) -> 'Event':
        """
        Create error response event (kind 26910)
        
        Args:
            provider_keys: Provider's keys for signing
            request_event_id: Event ID of the request being responded to
            error_code: JSON-RPC error code
            error_message: Error message
            request_id: Request ID from the original request (default: 1)
            
        Returns:
            Signed error response event
        """
        logger.debug("Creating error response event", 
                     request_event_id=request_event_id,
                     error_code=error_code)
        
        # Create content as JSON-RPC 2.0 error response
        content = {
            "jsonrpc": "2.0",
            "id": request_id or 1,
            "error": {
                "code": error_code,
                "message": error_message
            }
        }
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["e", request_event_id]),  # Required: Reference to request
        ]
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.RESPONSE_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(provider_keys)
        
        logger.info("Error response event created", 
                    event_id=event.id().to_hex(),
                    request_event_id=request_event_id,
                    error_code=error_code)
        
        return event
    
    @staticmethod
    def create_notification(
        sender_keys: 'Keys',
        target_pubkey: str,
        notification_type: str,
        params: Optional[Dict[str, Any]] = None,
        server_id: Optional[str] = None,
        request_event_id: Optional[str] = None
    ) -> 'Event':
        """
        Create notification event (kind 21316)
        
        Args:
            sender_keys: Sender's keys for signing (client or provider)
            target_pubkey: Target public key (hex or bech32)
            notification_type: Notification type (e.g., "notifications/initialized")
            params: Optional notification parameters
            server_id: Optional server identifier
            request_event_id: Optional reference to request event
            
        Returns:
            Signed notification event
        """
        logger.debug("Creating notification event", 
                     notification_type=notification_type,
                     target=target_pubkey)
        
        # Create content as JSON-RPC 2.0 notification
        content = {
            "jsonrpc": "2.0",
            "method": notification_type
        }
        
        # Add params if provided
        if params:
            content["params"] = params
        
        # Convert to JSON string
        content_str = json.dumps(content)
        
        # Create tags
        tags = [
            Tag.parse(["p", target_pubkey]),           # Required: Target public key
            Tag.parse(["method", notification_type]),  # Required: Method name for filtering
        ]
        
        # Add optional tags
        if server_id:
            tags.append(Tag.parse(["s", server_id]))
            
        if request_event_id:
            tags.append(Tag.parse(["e", request_event_id]))
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.NOTIFICATION_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(sender_keys)
        
        logger.info("Notification event created", 
                    event_id=event.id().to_hex(),
                    notification_type=notification_type)
        
        return event
    
    @staticmethod
    def create_payment_required_notification(
        provider_keys: 'Keys',
        client_pubkey: str,
        request_event_id: str,
        amount: int,
        bolt11: str
    ) -> 'Event':
        """
        Create payment required notification (kind 21316)
        
        Args:
            provider_keys: Provider's keys for signing
            client_pubkey: Client's public key (hex or bech32)
            request_event_id: Event ID of the request requiring payment
            amount: Payment amount in millisats
            bolt11: Lightning invoice
            
        Returns:
            Signed payment required notification event
        """
        logger.debug("Creating payment required notification", 
                     request_event_id=request_event_id,
                     amount=amount)
        
        # For payment notifications, we use empty content and put everything in tags
        content_str = ""
        
        # Create tags
        tags = [
            Tag.parse(["p", client_pubkey]),          # Required: Client public key
            Tag.parse(["status", "payment-required"]), # Required: Payment status
            Tag.parse(["amount", str(amount), bolt11]), # Required: Amount and invoice
            Tag.parse(["e", request_event_id]),        # Required: Reference to request
        ]
        
        # Create and sign event
        builder = EventBuilder(Kind(DVMCPEventBuilder.NOTIFICATION_KIND), content_str)
        for tag in tags:
            builder = builder.tags([tag])
            
        event = builder.sign_with_keys(provider_keys)
        
        logger.info("Payment required notification created", 
                    event_id=event.id().to_hex(),
                    request_event_id=request_event_id,
                    amount=amount)
        
        return event