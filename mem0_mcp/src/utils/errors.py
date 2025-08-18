"""
Enhanced error handling system for Mem0 MCP Server

Provides comprehensive error types with user-friendly messages, 
debugging information, and proper JSON-RPC error code mapping.
"""

import traceback
from typing import Any, Dict, Optional, Union
from datetime import datetime


class MCPError(Exception):
    """
    Enhanced base exception for MCP-related errors
    
    Features:
    - JSON-RPC 2.0 compliant error codes
    - User-friendly error messages
    - Developer debugging information
    - Contextual error data
    - Error severity levels
    """
    
    def __init__(
        self, 
        message: str, 
        code: int = -32603, 
        data: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        severity: str = "error",
        recoverable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}
        self.user_message = user_message or self._generate_user_message()
        self.severity = severity  # "info", "warning", "error", "critical"
        self.recoverable = recoverable
        self.timestamp = datetime.now().isoformat()
        self.traceback = traceback.format_exc() if self.severity in ["error", "critical"] else None
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message based on error code"""
        error_messages = {
            -32700: "请求格式有误。请检查您的输入是否为有效的JSON格式。",
            -32600: "请求无效。请检查请求的结构和格式。", 
            -32601: "请求的方法不存在。请检查方法名称是否正确。",
            -32602: "参数无效。请检查提供的参数是否正确。",
            -32603: "服务器内部错误。请稍后重试或联系支持团队。",
            -32000: "服务器错误。操作无法完成，请稍后重试。",
            -32001: "网络连接错误。请检查网络连接状态。",
            -32002: "工具执行失败。请检查输入参数并重试。",
            -32003: "配置错误。请检查系统配置。",
            -32004: "传输层错误。连接出现问题，请重试。"
        }
        return error_messages.get(self.code, "发生未知错误。请联系支持团队获得帮助。")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to enhanced JSON-RPC error format"""
        error_dict = {
            "code": self.code,
            "message": self.message,
            "data": {
                **self.data,
                "user_message": self.user_message,
                "severity": self.severity,
                "recoverable": self.recoverable,
                "timestamp": self.timestamp
            }
        }
        
        # Add traceback for development/debugging
        if self.traceback and self.severity in ["error", "critical"]:
            error_dict["data"]["debug_info"] = {
                "traceback": self.traceback,
                "error_type": self.__class__.__name__
            }
        
        return error_dict
    
    def to_user_dict(self) -> Dict[str, Any]:
        """Convert to user-facing error format (without debug info)"""
        return {
            "code": self.code,
            "message": self.user_message,
            "severity": self.severity,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
            "help": self._get_help_message()
        }
    
    def _get_help_message(self) -> str:
        """Get contextual help message for the user"""
        help_messages = {
            -32700: "确保发送的JSON格式正确，所有引号和括号都正确配对。",
            -32600: "检查请求是否包含必需的字段：jsonrpc, method, id。",
            -32601: "查看支持的方法列表，确保方法名拼写正确。",
            -32602: "验证所有参数类型和值是否符合API文档要求。",
            -32603: "如果问题持续出现，请报告此错误给技术支持。",
            -32002: "检查工具名称和参数是否正确，参考工具文档。"
        }
        return help_messages.get(self.code, "查看API文档了解更多信息，或联系技术支持。")


class ProtocolError(MCPError):
    """Protocol-level errors (malformed requests, etc.)"""
    
    def __init__(
        self, 
        message: str, 
        code: int = -32600, 
        data: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message, 
            code, 
            data, 
            user_message or "协议格式错误。请检查请求格式是否符合JSON-RPC 2.0规范。",
            severity="error",
            recoverable=True
        )


class ToolExecutionError(MCPError):
    """Tool execution errors with enhanced context"""
    
    def __init__(
        self, 
        message: str, 
        tool_name: str, 
        data: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        recoverable: bool = True
    ):
        enhanced_data = data or {}
        enhanced_data["tool_name"] = tool_name
        enhanced_data["execution_context"] = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat()
        }
        
        super().__init__(
            message, 
            -32002, 
            enhanced_data,
            user_message or f"工具 '{tool_name}' 执行失败。请检查参数是否正确。",
            severity="error",
            recoverable=recoverable
        )
        self.tool_name = tool_name


class ConfigurationError(MCPError):
    """Configuration-related errors"""
    
    def __init__(
        self, 
        message: str, 
        data: Optional[Dict[str, Any]] = None,
        config_key: Optional[str] = None,
        user_message: Optional[str] = None
    ):
        enhanced_data = data or {}
        if config_key:
            enhanced_data["config_key"] = config_key
        
        super().__init__(
            message, 
            -32003, 
            enhanced_data,
            user_message or "系统配置错误。请联系管理员检查配置设置。",
            severity="error",
            recoverable=False
        )


class TransportError(MCPError):
    """Transport layer errors"""
    
    def __init__(
        self, 
        message: str, 
        data: Optional[Dict[str, Any]] = None,
        transport_type: Optional[str] = None,
        user_message: Optional[str] = None
    ):
        enhanced_data = data or {}
        if transport_type:
            enhanced_data["transport_type"] = transport_type
        
        super().__init__(
            message, 
            -32004, 
            enhanced_data,
            user_message or "连接错误。请检查网络连接并重试。",
            severity="error",
            recoverable=True
        )


class ValidationError(MCPError):
    """Parameter validation errors with detailed field information"""
    
    def __init__(
        self, 
        message: str, 
        field: str = None, 
        data: Optional[Dict[str, Any]] = None,
        expected_type: Optional[str] = None,
        received_value: Any = None,
        user_message: Optional[str] = None
    ):
        enhanced_data = data or {}
        if field:
            enhanced_data["field"] = field
            enhanced_data["validation_context"] = {
                "field": field,
                "expected_type": expected_type,
                "received_value": str(received_value) if received_value is not None else None
            }
        
        field_msg = f"参数 '{field}'" if field else "参数"
        user_msg = user_message or f"{field_msg} 验证失败。请检查参数格式和类型。"
        
        super().__init__(
            message, 
            -32602, 
            enhanced_data,
            user_msg,
            severity="warning",
            recoverable=True
        )
        self.field = field


class NetworkError(MCPError):
    """Network connectivity errors"""
    
    def __init__(
        self, 
        message: str, 
        data: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        user_message: Optional[str] = None
    ):
        enhanced_data = data or {}
        if endpoint:
            enhanced_data["endpoint"] = endpoint
        if status_code:
            enhanced_data["status_code"] = status_code
        
        super().__init__(
            message, 
            -32001, 
            enhanced_data,
            user_message or "网络连接失败。请检查网络状况并稍后重试。",
            severity="error",
            recoverable=True
        )


class APIError(MCPError):
    """API-related errors (HTTP errors, etc.)"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = None, 
        data: Optional[Dict[str, Any]] = None,
        api_endpoint: Optional[str] = None,
        user_message: Optional[str] = None
    ):
        enhanced_data = data or {}
        if status_code:
            enhanced_data["status_code"] = status_code
        if api_endpoint:
            enhanced_data["api_endpoint"] = api_endpoint
        
        super().__init__(
            message, 
            -32001, 
            enhanced_data,
            user_message or f"API调用失败 (状态码: {status_code})。请稍后重试。",
            severity="error",
            recoverable=True
        )
        self.status_code = status_code


# Legacy alias for backward compatibility
class ToolError(ToolExecutionError):
    """Tool operation errors (alias for ToolExecutionError)"""
    pass


class AuthenticationError(MCPError):
    """Authentication and authorization errors"""
    
    def __init__(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message,
            -32005,  # Custom error code for auth
            data,
            user_message or "身份验证失败。请检查您的访问权限。",
            severity="error",
            recoverable=False
        )


class RateLimitError(MCPError):
    """Rate limiting errors"""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        enhanced_data = data or {}
        if retry_after:
            enhanced_data["retry_after"] = retry_after
        
        retry_msg = f"，请在 {retry_after} 秒后重试" if retry_after else ""
        
        super().__init__(
            message,
            -32006,  # Custom error code for rate limiting
            enhanced_data,
            user_message or f"请求频率过高{retry_msg}。",
            severity="warning",
            recoverable=True
        )


class TimeoutError(MCPError):
    """Timeout errors"""
    
    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        enhanced_data = data or {}
        if timeout_duration:
            enhanced_data["timeout_duration"] = timeout_duration
        if operation:
            enhanced_data["operation"] = operation
        
        super().__init__(
            message,
            -32007,  # Custom error code for timeout
            enhanced_data,
            user_message or "操作超时。请稍后重试或联系支持团队。",
            severity="error",
            recoverable=True
        )


# Error handling utilities
class ErrorHandler:
    """
    Comprehensive error handling utilities
    
    Provides consistent error formatting, logging, and user-friendly responses
    """
    
    @staticmethod
    def format_error_for_client(
        error: Exception, 
        request_id: Optional[Union[str, int]] = None,
        include_debug: bool = False
    ) -> Dict[str, Any]:
        """
        Format error for client response
        
        Args:
            error: Exception to format
            request_id: JSON-RPC request ID
            include_debug: Whether to include debug information
            
        Returns:
            Formatted error response dictionary
        """
        from ..protocol.jsonrpc import JSONRPCHandler, JSONRPCError
        
        if isinstance(error, MCPError):
            # Use enhanced MCP error
            error_data = error.to_dict() if include_debug else error.to_user_dict()
            return JSONRPCHandler.create_error_response(
                code=error.code,
                message=error.message,
                data=error_data,
                id=request_id
            ).to_dict()
        else:
            # Handle non-MCP exceptions
            mcp_error = MCPError(
                message=str(error),
                code=-32603,
                user_message="服务器内部错误，请稍后重试。",
                severity="error"
            )
            error_data = mcp_error.to_dict() if include_debug else mcp_error.to_user_dict()
            return JSONRPCHandler.create_error_response(
                code=-32603,
                message="Internal server error",
                data=error_data,
                id=request_id
            ).to_dict()
    
    @staticmethod
    def create_validation_error(
        field: str,
        expected: str,
        received: Any,
        custom_message: Optional[str] = None
    ) -> ValidationError:
        """
        Create a detailed validation error
        
        Args:
            field: Field name that failed validation
            expected: Expected type or format
            received: Actual received value
            custom_message: Custom error message
            
        Returns:
            ValidationError instance
        """
        message = custom_message or f"Invalid value for field '{field}': expected {expected}, got {type(received).__name__}"
        
        return ValidationError(
            message=message,
            field=field,
            expected_type=expected,
            received_value=received,
            user_message=f"参数 '{field}' 格式不正确。期望: {expected}，实际: {type(received).__name__}"
        )
    
    @staticmethod
    def create_tool_error(
        tool_name: str,
        operation: str,
        details: str,
        recoverable: bool = True
    ) -> ToolExecutionError:
        """
        Create a detailed tool execution error
        
        Args:
            tool_name: Name of the tool that failed
            operation: Operation that was being performed
            details: Detailed error information
            recoverable: Whether the error is recoverable
            
        Returns:
            ToolExecutionError instance
        """
        return ToolExecutionError(
            message=f"Tool '{tool_name}' failed during '{operation}': {details}",
            tool_name=tool_name,
            data={"operation": operation, "details": details},
            user_message=f"工具 '{tool_name}' 执行 '{operation}' 操作时失败。{details}",
            recoverable=recoverable
        )
    
    @staticmethod
    def handle_timeout(
        operation: str,
        timeout_duration: float,
        details: Optional[str] = None
    ) -> TimeoutError:
        """
        Create a timeout error with context
        
        Args:
            operation: Operation that timed out
            timeout_duration: How long the timeout was
            details: Additional details about the timeout
            
        Returns:
            TimeoutError instance
        """
        message = f"Operation '{operation}' timed out after {timeout_duration}s"
        if details:
            message += f": {details}"
        
        return TimeoutError(
            message=message,
            timeout_duration=timeout_duration,
            operation=operation,
            user_message=f"操作 '{operation}' 超时（{timeout_duration}秒）。请稍后重试。"
        )
    
    @staticmethod
    def wrap_api_error(
        original_error: Exception,
        endpoint: str,
        status_code: Optional[int] = None
    ) -> APIError:
        """
        Wrap an API error with additional context
        
        Args:
            original_error: Original exception
            endpoint: API endpoint that failed
            status_code: HTTP status code if applicable
            
        Returns:
            APIError instance
        """
        return APIError(
            message=f"API call to '{endpoint}' failed: {str(original_error)}",
            status_code=status_code,
            api_endpoint=endpoint,
            data={"original_error": str(original_error)},
            user_message=f"与服务器通信失败。端点: {endpoint}"
        )


def handle_errors(include_debug: bool = False):
    """
    Decorator for handling errors in MCP handlers
    
    Args:
        include_debug: Whether to include debug information in responses
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                from ..utils.logger import get_logger
                logger = get_logger(func.__module__)
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                
                # Return formatted error response
                return ErrorHandler.format_error_for_client(
                    error=e,
                    include_debug=include_debug
                )
        
        return wrapper
    return decorator


# Standard JSON-RPC error codes for reference
JSON_RPC_ERRORS = {
    -32700: "Parse error",
    -32600: "Invalid Request", 
    -32601: "Method not found",
    -32602: "Invalid params",
    -32603: "Internal error",
    -32000: "Server error",
    -32099: "Server error (range end)",
    # Custom MCP error codes
    -32001: "Network error",
    -32002: "Tool execution error",
    -32003: "Configuration error", 
    -32004: "Transport error",
    -32005: "Authentication error",
    -32006: "Rate limit error",
    -32007: "Timeout error"
}