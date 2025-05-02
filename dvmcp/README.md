# DVMCP Python Bridge

A Python implementation of the Distributed Virtual Machine Context Protocol (DVMCP) for Nostr.

## Overview

DVMCP is a protocol for exposing Model Context Protocol (MCP) services via Nostr. This library provides a Python bridge for both providers (servers) and clients, allowing seamless integration with Nostr relays.

## Features

- **Provider Implementation**: Create and manage MCP servers over Nostr
- **Client Implementation**: Discover and connect to MCP servers
- **Tools, Resources, and Prompts**: Full support for all MCP capabilities
- **Comprehensive Logging**: Structured logging with context support
- **Testability**: Extensive test suite with mocks and fixtures

## Installation

```bash
pip install dvmcp
```

## Usage

### Provider Example

```python
import asyncio
from nostr_sdk import Keys
from dvmcp import DVMCPProvider, configure_logging
from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool

# Configure logging
configure_logging(level="INFO")

async def main():
    # Generate or load provider keys
    provider_keys = Keys.generate()
    
    # Create provider with relays
    provider = DVMCPProvider(
        provider_keys=provider_keys,
        relays=["wss://relay.nostr.net"]
    )
    
    # Connect to relays
    await provider.connect()
    
    # Create server info and capabilities
    server_info = ServerInfo(
        name="Example DVMCP Server",
        version="1.0.0",
        description="Example server for DVMCP"
    )
    
    capabilities = ServerCapabilities()
    
    # Announce server
    server_id = "example-server-1"
    await provider.announce_server(server_id, server_info, capabilities)
    
    # Define tools
    tools = [
        Tool(
            name="echo",
            description="Echo back the input",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }
        )
    ]
    
    # Publish tools list
    await provider.publish_tools_list(tools, server_id)
    
    # Handle requests
    async def handle_request(request):
        if request["method"] == "tools/call" and request["params"]["name"] == "echo":
            message = request["params"]["arguments"]["message"]
            return {"result": message}
        else:
            return {"error": "Method not supported"}
    
    await provider.handle_requests(server_id, handle_request)
    
    # Keep the provider running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await provider.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Client Example

```python
import asyncio
from nostr_sdk import Keys
from dvmcp import DVMCPClient, configure_logging

# Configure logging
configure_logging(level="INFO")

async def main():
    # Generate or load client keys
    client_keys = Keys.generate()
    
    # Create client with relays
    client = DVMCPClient(
        client_keys=client_keys,
        relays=["wss://relay.example.com"]
    )
    
    # Connect to relays
    await client.connect()
    
    # Discover servers
    servers = await client.discover_servers(timeout=5.0)
    
    if not servers:
        print("No servers found")
        await client.disconnect()
        return
    
    # Connect to the first server
    server_id = next(iter(servers.keys()))
    server = await client.connect_to_server(server_id=server_id)
    
    print(f"Connected to server: {server['server_info'].get('name')}")
    
    # List available tools
    tools_list = await client.list_tools(server_id)
    
    for tool in tools_list.get("tools", []):
        print(f"Tool: {tool['name']} - {tool['description']}")
    
    # Call a tool
    if any(tool["name"] == "echo" for tool in tools_list.get("tools", [])):
        result = await client.call_tool(
            name="echo",
            arguments={"message": "Hello, DVMCP!"},
            server_id=server_id
        )
        
        print(f"Echo result: {result.get('result')}")
    
    # Disconnect
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Architecture

The library is organized into the following components:

```
dvmcp/
├── client/               # Client consuming MCP services
├── provider/             # Provider exposing MCP services
├── protocol/             # Event builders, parsers, request management
├── capabilities/         # Tools, resources, prompts implementations
├── models/               # Data models for all DVMCP objects
├── utils/                # Helper utilities
├── logging/              # Configurable logging system
└── tests/                # Comprehensive test suite
```

## Testing

Run the test suite with pytest:

```bash
pytest
```

## License

MIT