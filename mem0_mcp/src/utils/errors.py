"""
Custom exceptions for Mem0 MCP Server
"""

from typing import Any, Dict, Optional


class MCPError(Exception):
    """Base exception for MCP-related errors"""
    
    def __init__(self, message: str, code: int = -32603, data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to JSON-RPC error format"""
        error_dict = {
            "code": self.code,
            "message": self.message
        }
        if self.data:
            error_dict["data"] = self.data
        return error_dict


class ProtocolError(MCPError):
    """Protocol-level errors (malformed requests, etc.)"""
    
    def __init__(self, message: str, code: int = -32600, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, data)


class ToolExecutionError(MCPError):
    """Tool execution errors"""
    
    def __init__(self, message: str, tool_name: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, -32002, data)
        self.tool_name = tool_name


class ConfigurationError(MCPError):
    """Configuration-related errors"""
    
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, -32003, data)


class TransportError(MCPError):
    """Transport layer errors"""
    
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, -32004, data)


class ValidationError(MCPError):
    """Parameter validation errors"""
    
    def __init__(self, message: str, field: str = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, -32602, data)
        self.field = field


class ToolError(MCPError):
    """Tool operation errors (alias for ToolExecutionError)"""
    
    def __init__(self, message: str, tool_name: str = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, -32002, data)
        self.tool_name = tool_name


class NetworkError(MCPError):
    """Network connectivity errors"""
    
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, -32001, data)


class APIError(MCPError):
    """API-related errors (HTTP errors, etc.)"""
    
    def __init__(self, message: str, status_code: int = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, -32001, data)
        self.status_code = status_code