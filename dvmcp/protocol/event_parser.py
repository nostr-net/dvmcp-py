import json
from typing import Dict, List, Any, Optional, Tuple, Union
from nostr_sdk import Event, PublicKey

from dvmcp.logging import get_logger

logger = get_logger("protocol.event_parser")

class DVMCPEventParser:
    """Parses DVMCP events into structured objects"""
    
    @staticmethod
    def parse_request(event: Event) -> Dict[str, Any]:
        """
        Parse client request event into a structured object
        
        Args:
            event: Nostr event of kind 25910
            
        Returns:
            Dictionary with parsed request data
            
        Raises:
            ValueError: If event is not a valid request
        """
        logger.debug("Parsing request event", event_id=event.id().to_hex())
        
        # Validate event kind
        if event.kind().as_u16() != 25910:
            raise ValueError(f"Invalid event kind: {event.kind().as_u16()}, expected 25910")
        
        # Extract required tags
        provider_pubkey = None
        server_id = None
        method = None
        
        tags = event.tags().to_vec()
        for tag in tags:
            if tag.kind_str() == "p":
                provider_pubkey = tag.content()
            elif tag.kind_str() == "s":
                server_id = tag.content()
            elif tag.kind_str() == "method":
                method = tag.content()
        
        if not provider_pubkey:
            raise ValueError("Missing required 'p' tag in request event")
            
        if not method:
            # Try to extract method from content
            try:
                content = json.loads(event.content())
                if "method" in content:
                    method = content["method"]
            except (json.JSONDecodeError, KeyError):
                pass
                
        if not method:
            raise ValueError("Missing required 'method' tag in request event")
        
        # Parse JSON-RPC content
        try:
            content = json.loads(event.content())
            if not isinstance(content, dict):
                raise ValueError("Invalid JSON-RPC format: content must be an object")
                
            if "jsonrpc" not in content or content["jsonrpc"] != "2.0":
                raise ValueError("Invalid JSON-RPC format: missing or invalid jsonrpc version")
                
            if "id" not in content:
                raise ValueError("Invalid JSON-RPC format: missing id")
                
            if "method" not in content:
                raise ValueError("Invalid JSON-RPC format: missing method")
                
            if content["method"] != method:
                logger.warning("Method mismatch between tag and content", 
                              tag_method=method, 
                              content_method=content["method"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON-RPC content: {str(e)}")
        
        # Build result
        result = {
            "event_id": event.id().to_hex(),
            "client_pubkey": event.author().to_hex(),
            "provider_pubkey": provider_pubkey,
            "server_id": server_id,
            "method": method,
            "request_id": content["id"],
            "params": content.get("params", {})
        }
        
        logger.info("Request event parsed", 
                    event_id=event.id().to_hex(),
                    method=method)
        
        return result
    
    @staticmethod
    def parse_response(event: Event) -> Dict[str, Any]:
        """
        Parse server response event into a structured object
        
        Args:
            event: Nostr event of kind 26910
            
        Returns:
            Dictionary with parsed response data
            
        Raises:
            ValueError: If event is not a valid response
        """
        logger.debug("Parsing response event", event_id=event.id().to_hex())
        
        # Validate event kind
        if event.kind().as_u16() != 26910:
            raise ValueError(f"Invalid event kind: {event.kind().as_u16()}, expected 26910")
        
        # Extract required tags
        request_event_id = None
        
        tags = event.tags().to_vec()
        for tag in tags:
            if tag.kind_str() == "e":
                request_event_id = tag.content()
                break
        
        if not request_event_id:
            raise ValueError("Missing required 'e' tag in response event")
        
        # Parse JSON-RPC content
        try:
            content = json.loads(event.content())
            if not isinstance(content, dict):
                raise ValueError("Invalid JSON-RPC format: content must be an object")
                
            if "jsonrpc" not in content or content["jsonrpc"] != "2.0":
                raise ValueError("Invalid JSON-RPC format: missing or invalid jsonrpc version")
                
            if "id" not in content:
                raise ValueError("Invalid JSON-RPC format: missing id")
                
            # Check if it's a success or error response
            has_result = "result" in content
            has_error = "error" in content
            
            if not has_result and not has_error:
                raise ValueError("Invalid JSON-RPC format: missing result or error")
                
            if has_result and has_error:
                raise ValueError("Invalid JSON-RPC format: cannot have both result and error")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON-RPC content: {str(e)}")
        
        # Build result
        result = {
            "event_id": event.id().to_hex(),
            "provider_pubkey": event.author().to_hex(),
            "request_event_id": request_event_id,
            "request_id": content["id"],
            "success": has_result,
        }
        
        if has_result:
            result["result"] = content["result"]
        else:
            result["error"] = content["error"]
        
        logger.info("Response event parsed", 
                    event_id=event.id().to_hex(),
                    success=has_result)
        
        return result
    
    @staticmethod
    def parse_notification(event: Event) -> Dict[str, Any]:
        """
        Parse notification event into a structured object
        
        Args:
            event: Nostr event of kind 21316
            
        Returns:
            Dictionary with parsed notification data
            
        Raises:
            ValueError: If event is not a valid notification
        """
        logger.debug("Parsing notification event", event_id=event.id().to_hex())
        
        # Validate event kind
        if event.kind().as_u16() != 21316:
            raise ValueError(f"Invalid event kind: {event.kind().as_u16()}, expected 21316")
        
        # Extract required tags
        target_pubkey = None
        method = None
        server_id = None
        request_event_id = None
        
        tags = event.tags().to_vec()
        tag_dict = {}
        
        for tag in tags:
            tag_name = tag.kind_str()
            tag_parts = tag.as_vec()
            
            if tag_name == "p":
                target_pubkey = tag.content()
            elif tag_name == "method":
                method = tag.content()
            elif tag_name == "s":
                server_id = tag.content()
            elif tag_name == "e":
                request_event_id = tag.content()
            
            # Store all tag values for special notifications
            tag_dict[tag_name] = tag_parts[1:] if len(tag_parts) > 1 else []
        
        if not target_pubkey:
            raise ValueError("Missing required 'p' tag in notification event")
        
        # Check if it's a MCP notification or Nostr-specific notification
        if event.content():
            # Parse JSON-RPC content for MCP notification
            try:
                content = json.loads(event.content())
                if not isinstance(content, dict):
                    raise ValueError("Invalid JSON-RPC format: content must be an object")
                    
                if "jsonrpc" not in content or content["jsonrpc"] != "2.0":
                    raise ValueError("Invalid JSON-RPC format: missing or invalid jsonrpc version")
                    
                if "method" not in content:
                    raise ValueError("Invalid JSON-RPC format: missing method")
                
                if not method:
                    # Use method from content if not in tags
                    method = content["method"]
                elif content["method"] != method:
                    logger.warning("Method mismatch between tag and content", 
                                  tag_method=method, 
                                  content_method=content["method"])
                
                # Build result for MCP notification
                result = {
                    "event_id": event.id().to_hex(),
                    "sender_pubkey": event.author().to_hex(),
                    "target_pubkey": target_pubkey,
                    "notification_type": method,
                    "params": content.get("params", {}),
                    "server_id": server_id,
                    "request_event_id": request_event_id,
                    "is_mcp": True
                }
            except json.JSONDecodeError:
                # If content is not valid JSON, treat as Nostr-specific notification
                result = {
                    "event_id": event.id().to_hex(),
                    "sender_pubkey": event.author().to_hex(),
                    "target_pubkey": target_pubkey,
                    "tags": tag_dict,
                    "server_id": server_id,
                    "request_event_id": request_event_id,
                    "is_mcp": False
                }
                
                # Handle special Nostr notifications
                if "status" in tag_dict and tag_dict["status"] and tag_dict["status"][0] == "payment-required":
                    result["notification_type"] = "payment-required"
                    if "amount" in tag_dict and len(tag_dict["amount"]) >= 2:
                        result["amount"] = int(tag_dict["amount"][0])
                        result["bolt11"] = tag_dict["amount"][1]
        else:
            # Empty content means Nostr-specific notification
            result = {
                "event_id": event.id().to_hex(),
                "sender_pubkey": event.author().to_hex(),
                "target_pubkey": target_pubkey,
                "tags": tag_dict,
                "server_id": server_id,
                "request_event_id": request_event_id,
                "is_mcp": False
            }
            
            # Handle special Nostr notifications
            if "status" in tag_dict and tag_dict["status"] and tag_dict["status"][0] == "payment-required":
                result["notification_type"] = "payment-required"
                if "amount" in tag_dict and len(tag_dict["amount"]) >= 2:
                    result["amount"] = int(tag_dict["amount"][0])
                    result["bolt11"] = tag_dict["amount"][1]
        
        logger.info("Notification event parsed", 
                    event_id=event.id().to_hex(),
                    notification_type=result.get("notification_type", "unknown"))
        
        return result
    
    @staticmethod
    def parse_server_announcement(event: Event) -> Dict[str, Any]:
        """
        Parse server announcement event into a structured object
        
        Args:
            event: Nostr event of kind 31316
            
        Returns:
            Dictionary with parsed server info
            
        Raises:
            ValueError: If event is not a valid server announcement
        """
        logger.debug("Parsing server announcement event", event_id=event.id().to_hex())
        
        # Validate event kind
        if event.kind().as_u16() != 31316:
            raise ValueError(f"Invalid event kind: {event.kind().as_u16()}, expected 31316")
        
        # Extract required tags
        server_id = None
        accepted_kinds = []
        metadata = {}
        
        tags = event.tags().to_vec()
        for tag in tags:
            tag_name = tag.kind_str()
            if tag_name == "d":
                server_id = tag.content()
            elif tag_name == "k":
                accepted_kinds.append(tag.content())
            elif tag_name == "name":
                metadata["name"] = tag.content()
            elif tag_name == "about":
                metadata["description"] = tag.content()
            elif tag_name == "picture":
                metadata["picture"] = tag.content()
            elif tag_name == "website":
                metadata["website"] = tag.content()
            elif tag_name == "support_encryption":
                metadata["support_encryption"] = tag.content().lower() == "true"
        
        if not server_id:
            raise ValueError("Missing required 'd' tag in server announcement")
        
        # Parse JSON-RPC content
        try:
            content = json.loads(event.content())
            if not isinstance(content, dict):
                raise ValueError("Invalid JSON-RPC format: content must be an object")
                
            if "jsonrpc" not in content or content["jsonrpc"] != "2.0":
                raise ValueError("Invalid JSON-RPC format: missing or invalid jsonrpc version")
                
            if "id" not in content:
                raise ValueError("Invalid JSON-RPC format: missing id")
                
            if "result" not in content:
                raise ValueError("Invalid JSON-RPC format: missing result")
                
            result = content["result"]
            if not isinstance(result, dict):
                raise ValueError("Invalid JSON-RPC format: result must be an object")
                
            if "protocolVersion" not in result:
                raise ValueError("Invalid JSON-RPC format: missing protocolVersion")
                
            if "capabilities" not in result:
                raise ValueError("Invalid JSON-RPC format: missing capabilities")
                
            if "serverInfo" not in result:
                raise ValueError("Invalid JSON-RPC format: missing serverInfo")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON-RPC content: {str(e)}")
        
        # Build result
        server_info = {
            "event_id": event.id().to_hex(),
            "provider_pubkey": event.author().to_hex(),
            "server_id": server_id,
            "protocol_version": result["protocolVersion"],
            "capabilities": result["capabilities"],
            "server_info": result["serverInfo"],
            "accepted_kinds": accepted_kinds,
            "metadata": metadata
        }
        
        # Include instructions if present
        if "instructions" in result:
            server_info["instructions"] = result["instructions"]
        
        logger.info("Server announcement event parsed", 
                    event_id=event.id().to_hex(),
                    server_id=server_id)
        
        return server_info
    
    @staticmethod
    def parse_capability_list(event: Event) -> Dict[str, Any]:
        """
        Parse capability list event into a structured object
        
        Args:
            event: Nostr event of kind 31317, 31318, or 31319
            
        Returns:
            Dictionary with parsed capability info
            
        Raises:
            ValueError: If event is not a valid capability list
        """
        logger.debug("Parsing capability list event", 
                     event_id=event.id().to_hex(), 
                     kind=event.kind().as_u16())
        
        kind = event.kind().as_u16()
        if kind not in [31317, 31318, 31319]:
            raise ValueError(f"Invalid event kind: {kind}, expected 31317, 31318, or 31319")
        
        # Map kind to capability type
        capability_types = {
            31317: "tools",
            31318: "resources",
            31319: "prompts"
        }
        capability_type = capability_types[kind]
        
        # Extract required tags
        list_id = None
        server_id = None
        cap_tags = []
        
        tags = event.tags().to_vec()
        for tag in tags:
            tag_name = tag.kind_str()
            if tag_name == "d":
                list_id = tag.content()
            elif tag_name == "s":
                server_id = tag.content()
            elif tag_name == "cap":
                cap_tags.append(tag.content())
        
        if not list_id:
            raise ValueError("Missing required 'd' tag in capability list")
            
        if not server_id:
            raise ValueError("Missing required 's' tag in capability list")
        
        # Parse JSON-RPC content
        try:
            content = json.loads(event.content())
            if not isinstance(content, dict):
                raise ValueError("Invalid JSON-RPC format: content must be an object")
                
            if "jsonrpc" not in content or content["jsonrpc"] != "2.0":
                raise ValueError("Invalid JSON-RPC format: missing or invalid jsonrpc version")
                
            if "id" not in content:
                raise ValueError("Invalid JSON-RPC format: missing id")
                
            if "result" not in content:
                raise ValueError("Invalid JSON-RPC format: missing result")
                
            result = content["result"]
            if not isinstance(result, dict):
                raise ValueError("Invalid JSON-RPC format: result must be an object")
                
            if capability_type not in result:
                raise ValueError(f"Invalid JSON-RPC format: missing {capability_type}")
                
            capabilities = result[capability_type]
            if not isinstance(capabilities, list):
                raise ValueError(f"Invalid JSON-RPC format: {capability_type} must be an array")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON-RPC content: {str(e)}")
        
        # Build result
        capability_info = {
            "event_id": event.id().to_hex(),
            "provider_pubkey": event.author().to_hex(),
            "list_id": list_id,
            "server_id": server_id,
            "capability_type": capability_type,
            "capabilities": capabilities,
            "cap_tags": cap_tags
        }
        
        # Include nextCursor if present
        if "nextCursor" in result:
            capability_info["next_cursor"] = result["nextCursor"]
        
        logger.info("Capability list event parsed", 
                    event_id=event.id().to_hex(),
                    capability_type=capability_type,
                    count=len(capabilities))
        
        return capability_info