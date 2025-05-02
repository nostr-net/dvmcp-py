from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class Tool:
    """Tool capability in MCP"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }

@dataclass
class Resource:
    """Resource capability in MCP"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to dictionary for JSON serialization"""
        result = {
            "uri": self.uri,
            "name": self.name
        }
        if self.description:
            result["description"] = self.description
        if self.mime_type:
            result["mimeType"] = self.mime_type
        return result

@dataclass
class PromptArgument:
    """Argument for a prompt capability"""
    name: str
    description: str
    required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt argument to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required
        }

@dataclass
class Prompt:
    """Prompt capability in MCP"""
    name: str
    description: str
    arguments: List[PromptArgument] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [arg.to_dict() for arg in self.arguments]
        }