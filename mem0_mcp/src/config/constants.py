"""
MCP Server constants and configuration values
"""

# Server defaults
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8001
DEFAULT_MEM0_BASE_URL = "http://localhost:8000"
DEFAULT_API_VERSION = "v1"
# MCP Protocol versions (prioritized from newest to oldest)
SUPPORTED_MCP_VERSIONS = ["2025-03-26", "2024-11-05", "2024-10-07"]
MCP_VERSION = SUPPORTED_MCP_VERSIONS[0]  # Default to newest

# Supported transport types
SUPPORTED_TRANSPORTS = ["http", "stdio"]

# MCP Protocol error codes (following JSON-RPC 2.0 spec)
ERROR_CODES = {
    "PARSE_ERROR": -32700,
    "INVALID_REQUEST": -32600,
    "METHOD_NOT_FOUND": -32601,
    "INVALID_PARAMS": -32602,
    "INTERNAL_ERROR": -32603,
    
    # MCP-specific error codes
    "RESOURCE_NOT_FOUND": -32001,
    "TOOL_EXECUTION_ERROR": -32002,
    "CONFIGURATION_ERROR": -32003,
    "AUTHENTICATION_ERROR": -32004,
    "RATE_LIMIT_ERROR": -32005,
}

# Tool definitions
AVAILABLE_TOOLS = [
    "add_memory",
    "search_memories", 
    "get_memories",
    "get_memory_by_id",
    "delete_memory",
    "batch_delete_memories"
]

# HTTP client settings
HTTP_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"