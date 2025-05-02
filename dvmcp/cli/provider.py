#!/usr/bin/env python3
"""
DVMCP Provider CLI

Command-line interface for running a DVMCP provider.
"""

import os
import sys
import json
import asyncio
import argparse
from typing import Dict, Any, Optional

from nostr_sdk import Keys

from dvmcp import DVMCPProvider, configure_logging
from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool, Resource, Prompt
from dvmcp.capabilities import tool_registry, resource_registry, prompt_registry
from dvmcp.utils import load_keys_from_file, generate_keys, save_keys_to_file

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="DVMCP Provider CLI")
    
    # Server configuration
    parser.add_argument("--name", type=str, default="DVMCP Provider",
                        help="Server name")
    parser.add_argument("--version", type=str, default="1.0.0",
                        help="Server version")
    parser.add_argument("--description", type=str, default="DVMCP Provider Server",
                        help="Server description")
    parser.add_argument("--server-id", type=str, default="dvmcp-provider",
                        help="Server ID")
    
    # Relay configuration
    parser.add_argument("--relays", type=str, nargs="+",
                        default=["wss://relay.damus.io", "wss://relay.nostr.band"],
                        help="Relay URLs")
    
    # Key configuration
    parser.add_argument("--key-file", type=str, default="~/.dvmcp/provider_keys.json",
                        help="Path to key file")
    parser.add_argument("--generate-keys", action="store_true",
                        help="Generate new keys")
    
    # Logging configuration
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level")
    
    # Capabilities configuration
    parser.add_argument("--config-file", type=str, default=None,
                        help="Path to capabilities configuration file")
    
    return parser.parse_args()

def load_config(config_file: Optional[str]) -> Dict[str, Any]:
    """Load configuration from file"""
    if not config_file:
        return {}
    
    config_file = os.path.expanduser(config_file)
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        return {}
    
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load config file: {e}")
        return {}

def setup_keys(args) -> Keys:
    """Setup provider keys"""
    key_file = os.path.expanduser(args.key_file)
    
    if args.generate_keys:
        keys = generate_keys()
        save_keys_to_file(keys, key_file, include_nsec=True)
        print(f"Generated new keys and saved to {key_file}")
        print(f"Public key: {keys.public_key().to_hex()}")
        return keys
    
    keys = load_keys_from_file(key_file)
    if keys:
        print(f"Loaded keys from {key_file}")
        print(f"Public key: {keys.public_key().to_hex()}")
        return keys
    
    # No keys found, generate new ones
    keys = generate_keys()
    save_keys_to_file(keys, key_file, include_nsec=True)
    print(f"No keys found, generated new keys and saved to {key_file}")
    print(f"Public key: {keys.public_key().to_hex()}")
    return keys

async def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle client requests"""
    method = request.get("method")
    params = request.get("params", {})
    
    print(f"Received request: {method}")
    
    if method == "tools/list":
        return {"tools": [tool.to_dict() for tool in tool_registry.list_tools()]}
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        tool_impl = tool_registry.get(tool_name)
        if not tool_impl:
            return {"error": {"code": -32601, "message": f"Tool not found: {tool_name}"}}
        
        try:
            result = await tool_impl.execute(arguments)
            return result
        except Exception as e:
            return {"error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"}}
    
    elif method == "resources/list":
        return {"resources": [resource.to_dict() for resource in resource_registry.list_resources()]}
    
    elif method == "resources/read":
        uri = params.get("uri")
        
        resource_impl = resource_registry.get(uri)
        if not resource_impl:
            return {"error": {"code": -32601, "message": f"Resource not found: {uri}"}}
        
        try:
            result = await resource_impl.read(params)
            return result
        except Exception as e:
            return {"error": {"code": -32603, "message": f"Resource reading failed: {str(e)}"}}
    
    elif method == "prompts/list":
        return {"prompts": [prompt.to_dict() for prompt in prompt_registry.list_prompts()]}
    
    elif method == "prompts/get":
        name = params.get("name")
        
        prompt_impl = prompt_registry.get(name)
        if not prompt_impl:
            return {"error": {"code": -32601, "message": f"Prompt not found: {name}"}}
        
        return {"prompt": prompt_impl.prompt.to_dict()}
    
    elif method == "prompts/execute":
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        prompt_impl = prompt_registry.get(name)
        if not prompt_impl:
            return {"error": {"code": -32601, "message": f"Prompt not found: {name}"}}
        
        try:
            result = await prompt_impl.execute(arguments)
            return result
        except Exception as e:
            return {"error": {"code": -32603, "message": f"Prompt execution failed: {str(e)}"}}
    
    return {"error": {"code": -32601, "message": f"Method not found: {method}"}}

async def main_async():
    """Main async function"""
    args = parse_args()
    
    # Configure logging
    configure_logging(level=args.log_level)
    
    # Setup keys
    keys = setup_keys(args)
    
    # Create server info
    server_info = ServerInfo(
        name=args.name,
        version=args.version,
        description=args.description
    )
    
    # Create capabilities
    capabilities = ServerCapabilities()
    
    # Create provider
    provider = DVMCPProvider(
        provider_keys=keys,
        relays=args.relays
    )
    
    # Connect to relays
    await provider.connect()
    print(f"Connected to relays: {', '.join(args.relays)}")
    
    # Announce server
    await provider.announce_server(args.server_id, server_info, capabilities)
    print(f"Announced server: {args.server_id}")
    
    # Publish capabilities
    await provider.publish_tools_list(tool_registry.list_tools(), args.server_id)
    print(f"Published tools list: {len(tool_registry.list_tools())} tools")
    
    await provider.publish_resources_list(resource_registry.list_resources(), args.server_id)
    print(f"Published resources list: {len(resource_registry.list_resources())} resources")
    
    await provider.publish_prompts_list(prompt_registry.list_prompts(), args.server_id)
    print(f"Published prompts list: {len(prompt_registry.list_prompts())} prompts")
    
    # Handle requests
    await provider.handle_requests(args.server_id, handle_request)
    print("Ready to handle requests")
    
    # Keep the provider running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        await provider.disconnect()
        print("Disconnected from relays")

def main():
    """Main entry point"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()