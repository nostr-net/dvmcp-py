from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class ServerInfo:
    """Information about an MCP server"""
    name: str
    version: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert server info to dictionary for JSON serialization"""
        result = {
            "name": self.name,
            "version": self.version
        }
        if self.description:
            result["description"] = self.description
        return result

@dataclass
class ServerCapabilities:
    """Capabilities supported by an MCP server"""
    prompts: Dict[str, Any] = field(default_factory=lambda: {"listChanged": True})
    resources: Dict[str, Any] = field(default_factory=lambda: {"subscribe": True, "listChanged": True})
    tools: Dict[str, Any] = field(default_factory=lambda: {"listChanged": True})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary for JSON serialization"""
        return {
            "prompts": self.prompts,
            "resources": self.resources,
            "tools": self.tools
        }