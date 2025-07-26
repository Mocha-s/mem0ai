"""
JSON-RPC 2.0 implementation for MCP protocol
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from ..utils.errors import ProtocolError
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request message"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method
        }
        
        if self.params is not None:
            result["params"] = self.params
        
        if self.id is not None:
            result["id"] = self.id
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JSONRPCRequest':
        """Create from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id")
        )


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response message"""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        
        if self.error is not None:
            result["error"] = self.error
        else:
            result["result"] = self.result
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JSONRPCResponse':
        """Create from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            result=data.get("result"),
            error=data.get("error"),
            id=data.get("id")
        )


@dataclass
class JSONRPCError:
    """JSON-RPC 2.0 error object"""
    code: int
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "code": self.code,
            "message": self.message
        }
        
        if self.data is not None:
            result["data"] = self.data
            
        return result


class JSONRPCHandler:
    """
    JSON-RPC 2.0 protocol handler for MCP messages
    """
    
    @staticmethod
    def create_request(
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        id: Optional[Union[str, int]] = None
    ) -> JSONRPCRequest:
        """
        Create a JSON-RPC request
        
        Args:
            method: RPC method name
            params: Method parameters
            id: Request ID (if None, creates notification)
            
        Returns:
            JSONRPCRequest instance
        """
        if id is None and method not in ["initialized"]:  # initialized is a notification by spec
            id = str(uuid.uuid4())
        
        return JSONRPCRequest(
            method=method,
            params=params,
            id=id
        )
    
    @staticmethod
    def create_response(
        result: Any = None,
        error: Optional[JSONRPCError] = None,
        id: Optional[Union[str, int]] = None
    ) -> JSONRPCResponse:
        """
        Create a JSON-RPC response
        
        Args:
            result: Success result (mutually exclusive with error)
            error: Error object (mutually exclusive with result)
            id: Request ID this response corresponds to
            
        Returns:
            JSONRPCResponse instance
        """
        error_dict = error.to_dict() if error else None
        
        return JSONRPCResponse(
            result=result,
            error=error_dict,
            id=id
        )
    
    @staticmethod
    def create_success_response(
        result: Any,
        id: Optional[Union[str, int]] = None
    ) -> JSONRPCResponse:
        """
        Create a success response
        
        Args:
            result: Success result
            id: Request ID this response corresponds to
            
        Returns:
            JSONRPCResponse instance with result
        """
        return JSONRPCHandler.create_response(result=result, id=id)
    
    @staticmethod
    def create_error_response(
        code: int,
        message: str,
        data: Optional[Any] = None,
        id: Optional[Union[str, int]] = None
    ) -> JSONRPCResponse:
        """
        Create an error response
        
        Args:
            code: Error code
            message: Error message
            data: Additional error data
            id: Request ID this response corresponds to
            
        Returns:
            JSONRPCResponse instance with error
        """
        error = JSONRPCError(code=code, message=message, data=data)
        return JSONRPCHandler.create_response(error=error, id=id)
    
    @staticmethod
    def parse_message(message_str: str) -> Union[JSONRPCRequest, JSONRPCResponse]:
        """
        Parse JSON-RPC message from string
        
        Args:
            message_str: JSON string containing the message
            
        Returns:
            JSONRPCRequest or JSONRPCResponse instance
            
        Raises:
            ProtocolError: If message is invalid
        """
        try:
            data = json.loads(message_str)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"Invalid JSON: {str(e)}", code=-32700)
        
        if not isinstance(data, dict):
            raise ProtocolError("JSON-RPC message must be an object", code=-32600)
        
        # Check JSON-RPC version
        if data.get("jsonrpc") != "2.0":
            raise ProtocolError("Invalid JSON-RPC version", code=-32600)
        
        # Determine if it's a request or response
        if "method" in data:
            # It's a request
            if not isinstance(data["method"], str):
                raise ProtocolError("Method must be a string", code=-32600)
            
            return JSONRPCRequest.from_dict(data)
        
        elif "result" in data or "error" in data:
            # It's a response
            return JSONRPCResponse.from_dict(data)
        
        else:
            raise ProtocolError("Invalid JSON-RPC message format", code=-32600)
    
    @staticmethod
    def validate_request(request: JSONRPCRequest) -> None:
        """
        Validate JSON-RPC request
        
        Args:
            request: Request to validate
            
        Raises:
            ProtocolError: If request is invalid
        """
        if not request.method:
            raise ProtocolError("Method is required", code=-32600)
        
        if request.params is not None:
            if not isinstance(request.params, (dict, list)):
                raise ProtocolError("Params must be object or array", code=-32602)
    
    @staticmethod
    def is_notification(request: JSONRPCRequest) -> bool:
        """
        Check if request is a notification (no response expected)
        
        Args:
            request: Request to check
            
        Returns:
            True if notification, False if regular request
        """
        return request.id is None