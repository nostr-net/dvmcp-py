"""
Validation utilities for DVMCP

This module provides helper functions for validating data.
"""

import json
from typing import Dict, Any, Optional, List, Union, Tuple

from dvmcp.logging import get_logger

logger = get_logger("utils.validation")

def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate data against a JSON Schema
    
    Args:
        data: Data to validate
        schema: JSON Schema to validate against
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        import jsonschema
        
        jsonschema.validate(instance=data, schema=schema)
        return True, None
    except jsonschema.exceptions.ValidationError as e:
        return False, str(e)
    except Exception as e:
        logger.error(f"Schema validation error: {str(e)}")
        return False, f"Schema validation error: {str(e)}"

def validate_server_id(server_id: str) -> bool:
    """
    Validate server ID format
    
    Args:
        server_id: Server ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Server ID should be a non-empty string with no spaces
    if not server_id or not isinstance(server_id, str):
        return False
    
    if ' ' in server_id:
        return False
    
    # Server ID should be at most 64 characters
    if len(server_id) > 64:
        return False
    
    return True

def validate_event_id(event_id: str) -> bool:
    """
    Validate event ID format
    
    Args:
        event_id: Event ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Event ID should be a 64-character hex string
    if not event_id or not isinstance(event_id, str):
        return False
    
    if len(event_id) != 64:
        return False
    
    # Check if it's a valid hex string
    try:
        int(event_id, 16)
        return True
    except ValueError:
        return False

def validate_pubkey(pubkey: str) -> bool:
    """
    Validate public key format
    
    Args:
        pubkey: Public key to validate (hex or bech32)
        
    Returns:
        True if valid, False otherwise
    """
    # Check if it's a bech32 encoded key
    if pubkey.startswith("npub1"):
        try:
            from nostr_sdk import PublicKey
            PublicKey.from_bech32(pubkey)
            return True
        except Exception:
            return False
    
    # Check if it's a hex encoded key
    if len(pubkey) != 64:
        return False
    
    try:
        int(pubkey, 16)
        return True
    except ValueError:
        return False

def validate_request_params(method: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate request parameters for a specific method
    
    Args:
        method: Method name
        params: Parameters to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Define schemas for different methods
    schemas = {
        "initialize": {
            "type": "object",
            "properties": {
                "protocolVersion": {"type": "string"},
                "capabilities": {
                    "type": "object",
                    "properties": {
                        "prompts": {"type": "object"},
                        "resources": {"type": "object"},
                        "tools": {"type": "object"}
                    }
                },
                "clientInfo": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"}
                    },
                    "required": ["name"]
                }
            },
            "required": ["protocolVersion", "capabilities"]
        },
        "tools/list": {
            "type": "object",
            "properties": {
                "cursor": {"type": "string"}
            }
        },
        "tools/call": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object"}
            },
            "required": ["name", "arguments"]
        },
        "resources/list": {
            "type": "object",
            "properties": {
                "cursor": {"type": "string"}
            }
        },
        "resources/read": {
            "type": "object",
            "properties": {
                "uri": {"type": "string"}
            },
            "required": ["uri"]
        },
        "resources/subscribe": {
            "type": "object",
            "properties": {
                "uri": {"type": "string"}
            },
            "required": ["uri"]
        },
        "resources/unsubscribe": {
            "type": "object",
            "properties": {
                "uri": {"type": "string"},
                "subscriptionId": {"type": "string"}
            },
            "required": ["uri", "subscriptionId"]
        },
        "prompts/list": {
            "type": "object",
            "properties": {
                "cursor": {"type": "string"}
            }
        },
        "prompts/get": {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        },
        "prompts/execute": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object"}
            },
            "required": ["name", "arguments"]
        }
    }
    
    # Get schema for method
    schema = schemas.get(method)
    if not schema:
        return True, None  # No schema defined for this method
    
    # Validate params against schema
    return validate_json_schema(params, schema)