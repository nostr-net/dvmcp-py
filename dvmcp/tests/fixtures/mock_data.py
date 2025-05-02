import json
from nostr_sdk import Keys, EventBuilder, Tag, Kind

from dvmcp.models.server import ServerInfo, ServerCapabilities
from dvmcp.models.capabilities import Tool, Resource, Prompt, PromptArgument

# Test keys
def generate_test_keys():
    """Generate test keys"""
    return Keys.generate()

# Server data
def create_test_server_info():
    """Create test server info"""
    return ServerInfo(
        name="Test DVMCP Server",
        version="1.0.0",
        description="Test server for DVMCP testing"
    )

def create_test_capabilities():
    """Create test server capabilities"""
    return ServerCapabilities(
        prompts={"listChanged": True},
        resources={"subscribe": True, "listChanged": True},
        tools={"listChanged": True}
    )

# Tool data
def create_test_tools():
    """Create test tools"""
    return [
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
        ),
        Tool(
            name="add",
            description="Add two numbers",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="weather",
            description="Get weather information",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        )
    ]

# Resource data
def create_test_resources():
    """Create test resources"""
    return [
        Resource(
            uri="weather://current",
            name="Current Weather",
            description="Current weather information",
            mime_type="application/json"
        ),
        Resource(
            uri="weather://forecast",
            name="Weather Forecast",
            description="5-day weather forecast",
            mime_type="application/json"
        ),
        Resource(
            uri="system://info",
            name="System Information",
            description="System information and status",
            mime_type="application/json"
        )
    ]

# Prompt data
def create_test_prompts():
    """Create test prompts"""
    return [
        Prompt(
            name="weather-report",
            description="Generate a weather report",
            arguments=[
                PromptArgument(
                    name="location",
                    description="Location for the weather report",
                    required=True
                ),
                PromptArgument(
                    name="days",
                    description="Number of days for the forecast",
                    required=False
                )
            ]
        ),
        Prompt(
            name="code-review",
            description="Review code for issues",
            arguments=[
                PromptArgument(
                    name="code",
                    description="Code to review",
                    required=True
                ),
                PromptArgument(
                    name="language",
                    description="Programming language",
                    required=True
                )
            ]
        )
    ]

# Event creation helpers
def create_server_announcement_event(provider_keys, server_id):
    """Create a server announcement event"""
    server_info = create_test_server_info()
    capabilities = create_test_capabilities()
    
    # Create content
    content = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-03-26",
            "capabilities": capabilities.to_dict(),
            "serverInfo": server_info.to_dict()
        }
    }
    
    # Create tags
    tags = [
        Tag.parse(["d", server_id]),
        Tag.parse(["k", "25910"])
    ]
    
    # Create event
    builder = EventBuilder.new(Kind.new(31316), json.dumps(content))
    for tag in tags:
        builder = builder.tags([tag])
    
    return builder.sign_with_keys(provider_keys)

def create_tools_list_event(provider_keys, server_id, list_id=None):
    """Create a tools list event"""
    tools = create_test_tools()
    
    # Use server_id as list_id if not provided
    if not list_id:
        list_id = server_id
    
    # Create content
    content = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [tool.to_dict() for tool in tools]
        }
    }
    
    # Create tags
    tags = [
        Tag.parse(["d", list_id]),
        Tag.parse(["s", server_id])
    ]
    
    # Add cap tags
    for tool in tools:
        tags.append(Tag.parse(["cap", tool.name]))
    
    # Create event
    builder = EventBuilder.new(Kind.new(31317), json.dumps(content))
    for tag in tags:
        builder = builder.tags([tag])
    
    return builder.sign_with_keys(provider_keys)

def create_resources_list_event(provider_keys, server_id, list_id=None):
    """Create a resources list event"""
    resources = create_test_resources()
    
    # Use server_id as list_id if not provided
    if not list_id:
        list_id = server_id
    
    # Create content
    content = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "resources": [resource.to_dict() for resource in resources]
        }
    }
    
    # Create tags
    tags = [
        Tag.parse(["d", list_id]),
        Tag.parse(["s", server_id])
    ]
    
    # Add cap tags
    for resource in resources:
        tags.append(Tag.parse(["cap", resource.name]))
    
    # Create event
    builder = EventBuilder.new(Kind.new(31318), json.dumps(content))
    for tag in tags:
        builder = builder.tags([tag])
    
    return builder.sign_with_keys(provider_keys)

def create_prompts_list_event(provider_keys, server_id, list_id=None):
    """Create a prompts list event"""
    prompts = create_test_prompts()
    
    # Use server_id as list_id if not provided
    if not list_id:
        list_id = server_id
    
    # Create content
    content = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "prompts": [prompt.to_dict() for prompt in prompts]
        }
    }
    
    # Create tags
    tags = [
        Tag.parse(["d", list_id]),
        Tag.parse(["s", server_id])
    ]
    
    # Add cap tags
    for prompt in prompts:
        tags.append(Tag.parse(["cap", prompt.name]))
    
    # Create event
    builder = EventBuilder.new(Kind.new(31319), json.dumps(content))
    for tag in tags:
        builder = builder.tags([tag])
    
    return builder.sign_with_keys(provider_keys)