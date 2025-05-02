#!/usr/bin/env python3
"""
DVMCP Client CLI

Command-line interface for interacting with DVMCP providers.
"""

import os
import sys
import json
import asyncio
import argparse
from typing import Dict, Any, Optional, List

from nostr_sdk import Keys

from dvmcp import DVMCPClient, configure_logging
from dvmcp.utils import load_keys_from_file, generate_keys, save_keys_to_file

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="DVMCP Client CLI")
    
    # Command selection
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover servers")
    discover_parser.add_argument("--timeout", type=float, default=5.0,
                                help="Discovery timeout in seconds")
    discover_parser.add_argument("--filter-name", type=str, default=None,
                                help="Filter servers by name")
    
    # Connect command
    connect_parser = subparsers.add_parser("connect", help="Connect to a server")
    connect_parser.add_argument("--server-id", type=str, required=True,
                               help="Server ID to connect to")
    connect_parser.add_argument("--timeout", type=float, default=30.0,
                               help="Connection timeout in seconds")
    
    # List tools command
    list_tools_parser = subparsers.add_parser("list-tools", help="List available tools")
    list_tools_parser.add_argument("--server-id", type=str, required=True,
                                  help="Server ID")
    
    # Call tool command
    call_tool_parser = subparsers.add_parser("call-tool", help="Call a tool")
    call_tool_parser.add_argument("--server-id", type=str, required=True,
                                 help="Server ID")
    call_tool_parser.add_argument("--name", type=str, required=True,
                                 help="Tool name")
    call_tool_parser.add_argument("--arguments", type=str, required=True,
                                 help="Tool arguments as JSON string")
    
    # List resources command
    list_resources_parser = subparsers.add_parser("list-resources", help="List available resources")
    list_resources_parser.add_argument("--server-id", type=str, required=True,
                                      help="Server ID")
    
    # Read resource command
    read_resource_parser = subparsers.add_parser("read-resource", help="Read a resource")
    read_resource_parser.add_argument("--server-id", type=str, required=True,
                                     help="Server ID")
    read_resource_parser.add_argument("--uri", type=str, required=True,
                                     help="Resource URI")
    
    # List prompts command
    list_prompts_parser = subparsers.add_parser("list-prompts", help="List available prompts")
    list_prompts_parser.add_argument("--server-id", type=str, required=True,
                                    help="Server ID")
    
    # Get prompt command
    get_prompt_parser = subparsers.add_parser("get-prompt", help="Get a prompt")
    get_prompt_parser.add_argument("--server-id", type=str, required=True,
                                  help="Server ID")
    get_prompt_parser.add_argument("--name", type=str, required=True,
                                  help="Prompt name")
    
    # Execute prompt command
    execute_prompt_parser = subparsers.add_parser("execute-prompt", help="Execute a prompt")
    execute_prompt_parser.add_argument("--server-id", type=str, required=True,
                                      help="Server ID")
    execute_prompt_parser.add_argument("--name", type=str, required=True,
                                      help="Prompt name")
    execute_prompt_parser.add_argument("--arguments", type=str, required=True,
                                      help="Prompt arguments as JSON string")
    
    # Relay configuration
    parser.add_argument("--relays", type=str, nargs="+",
                        default=["wss://relay.damus.io", "wss://relay.nostr.band"],
                        help="Relay URLs")
    
    # Key configuration
    parser.add_argument("--key-file", type=str, default="~/.dvmcp/client_keys.json",
                        help="Path to key file")
    parser.add_argument("--generate-keys", action="store_true",
                        help="Generate new keys")
    
    # Logging configuration
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level")
    
    # Output format
    parser.add_argument("--output", type=str, default="pretty",
                        choices=["pretty", "json"],
                        help="Output format")
    
    return parser.parse_args()

def setup_keys(args) -> Keys:
    """Setup client keys"""
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

def print_output(data: Any, format: str):
    """Print output in specified format"""
    if format == "json":
        print(json.dumps(data, indent=2))
    else:
        # Pretty print based on data type
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    print(f"{key}:")
                    print_output(value, format)
                else:
                    print(f"{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    print(f"[{i}]:")
                    print_output(item, format)
                else:
                    print(f"[{i}] {item}")
        else:
            print(data)

async def discover_servers(client: DVMCPClient, args):
    """Discover servers"""
    print("Discovering servers...")
    
    filters = {}
    if args.filter_name:
        filters["name"] = args.filter_name
    
    servers = await client.discover_servers(timeout=args.timeout, filters=filters)
    
    if not servers:
        print("No servers found")
        return
    
    print(f"Found {len(servers)} servers:")
    
    for server_id, server in servers.items():
        server_info = server.get("server_info", {})
        print(f"Server ID: {server_id}")
        print(f"  Name: {server_info.get('name', 'Unknown')}")
        print(f"  Version: {server_info.get('version', 'Unknown')}")
        print(f"  Description: {server_info.get('description', 'No description')}")
        print(f"  Provider: {server.get('provider_pubkey', 'Unknown')}")
        print()

async def connect_to_server(client: DVMCPClient, args):
    """Connect to a server"""
    print(f"Connecting to server: {args.server_id}")
    
    try:
        server = await client.connect_to_server(
            server_id=args.server_id,
            timeout=args.timeout
        )
        
        print("Connected to server:")
        print(f"  Name: {server.get('server_info', {}).get('name', 'Unknown')}")
        print(f"  Version: {server.get('server_info', {}).get('version', 'Unknown')}")
        print(f"  Description: {server.get('server_info', {}).get('description', 'No description')}")
        print(f"  Provider: {server.get('provider_pubkey', 'Unknown')}")
        
        return True
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        return False

async def list_tools(client: DVMCPClient, args):
    """List available tools"""
    print(f"Listing tools for server: {args.server_id}")
    
    try:
        result = await client.list_tools(server_id=args.server_id)
        
        tools = result.get("tools", [])
        if not tools:
            print("No tools available")
            return
        
        print(f"Found {len(tools)} tools:")
        print_output(tools, args.output)
        
    except Exception as e:
        print(f"Failed to list tools: {e}")

async def call_tool(client: DVMCPClient, args):
    """Call a tool"""
    print(f"Calling tool: {args.name}")
    
    try:
        # Parse arguments
        arguments = json.loads(args.arguments)
        
        result = await client.call_tool(
            name=args.name,
            arguments=arguments,
            server_id=args.server_id
        )
        
        print("Tool execution result:")
        print_output(result, args.output)
        
    except Exception as e:
        print(f"Failed to call tool: {e}")

async def list_resources(client: DVMCPClient, args):
    """List available resources"""
    print(f"Listing resources for server: {args.server_id}")
    
    try:
        result = await client.list_resources(server_id=args.server_id)
        
        resources = result.get("resources", [])
        if not resources:
            print("No resources available")
            return
        
        print(f"Found {len(resources)} resources:")
        print_output(resources, args.output)
        
    except Exception as e:
        print(f"Failed to list resources: {e}")

async def read_resource(client: DVMCPClient, args):
    """Read a resource"""
    print(f"Reading resource: {args.uri}")
    
    try:
        result = await client.read_resource(
            uri=args.uri,
            server_id=args.server_id
        )
        
        print("Resource content:")
        print_output(result, args.output)
        
    except Exception as e:
        print(f"Failed to read resource: {e}")

async def list_prompts(client: DVMCPClient, args):
    """List available prompts"""
    print(f"Listing prompts for server: {args.server_id}")
    
    try:
        result = await client.list_prompts(server_id=args.server_id)
        
        prompts = result.get("prompts", [])
        if not prompts:
            print("No prompts available")
            return
        
        print(f"Found {len(prompts)} prompts:")
        print_output(prompts, args.output)
        
    except Exception as e:
        print(f"Failed to list prompts: {e}")

async def get_prompt(client: DVMCPClient, args):
    """Get a prompt"""
    print(f"Getting prompt: {args.name}")
    
    try:
        result = await client.get_prompt(
            name=args.name,
            server_id=args.server_id
        )
        
        print("Prompt details:")
        print_output(result, args.output)
        
    except Exception as e:
        print(f"Failed to get prompt: {e}")

async def main_async():
    """Main async function"""
    args = parse_args()
    
    if not args.command:
        print("No command specified. Use --help for usage information.")
        return
    
    # Configure logging
    configure_logging(level=args.log_level)
    
    # Setup keys
    keys = setup_keys(args)
    
    # Create client
    client = DVMCPClient(
        client_keys=keys,
        relays=args.relays
    )
    
    # Connect to relays
    await client.connect()
    print(f"Connected to relays: {', '.join(args.relays)}")
    
    try:
        # Execute command
        if args.command == "discover":
            await discover_servers(client, args)
        
        elif args.command == "connect":
            await connect_to_server(client, args)
        
        elif args.command == "list-tools":
            await list_tools(client, args)
        
        elif args.command == "call-tool":
            await call_tool(client, args)
        
        elif args.command == "list-resources":
            await list_resources(client, args)
        
        elif args.command == "read-resource":
            await read_resource(client, args)
        
        elif args.command == "list-prompts":
            await list_prompts(client, args)
        
        elif args.command == "get-prompt":
            await get_prompt(client, args)
        
        elif args.command == "execute-prompt":
            # Not implemented yet
            print("Execute prompt command not implemented yet")
    
    finally:
        # Disconnect from relays
        await client.disconnect()
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