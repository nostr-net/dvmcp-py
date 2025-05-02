"""
DVMCP Capabilities Implementation

This module provides implementations for MCP capabilities (tools, resources, prompts).
"""

from .tools import registry as tool_registry
from .resources import registry as resource_registry
from .prompts import registry as prompt_registry

__all__ = ['tool_registry', 'resource_registry', 'prompt_registry']