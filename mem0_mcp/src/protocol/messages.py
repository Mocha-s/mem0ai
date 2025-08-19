"""
Message Types for MCP Protocol

Defines the message format for tool results and errors.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class ContentBlock:
    """Base content block for tool results"""
    type: str

@dataclass 
class TextContent(ContentBlock):
    """Text content block"""
    type: str = "text"
    text: str = ""

@dataclass
class ToolResult:
    """Successful tool execution result following MCP 2025-06-18 specification"""
    content: List[ContentBlock]
    structured_content: Optional[Dict[str, Any]] = None
    is_error: bool = False

@dataclass
class ErrorResult:
    """Tool execution error result"""
    error_code: int
    error_message: str
    error_data: Optional[Dict[str, Any]] = None
    is_error: bool = True

# For convenience
RequestMessage = Dict[str, Any]
ResponseMessage = Dict[str, Any] 
NotificationMessage = Dict[str, Any]