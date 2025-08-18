"""
Configuration settings for Mem0 MCP Server
"""

import os
import sys
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

# Add parent directory to path to import Mem0 config
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../server"))

try:
    from config.env_config import app_config as mem0_config
    MEM0_CONFIG_AVAILABLE = True
except ImportError:
    MEM0_CONFIG_AVAILABLE = False
    mem0_config = None

from .constants import DEFAULT_HOST, DEFAULT_PORT


@dataclass
class MCPConfig:
    """MCP Server configuration"""
    
    # Server settings
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    debug: bool = False
    
    # Mem0 service settings
    mem0_base_url: str = "http://localhost:8000"
    mem0_api_version: str = "v1"  # v1 or v2 - keep v1 as default for backward compatibility
    
    # Mem0 client settings (for API key and base URL compatibility)
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Transport settings
    transport: str = "http"  # http or stdio
    enable_streaming: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_to_file: bool = False
    log_file_path: str = "/tmp/mem0_mcp.log"
    
    # Performance
    max_concurrent_requests: int = 100
    request_timeout: int = 30
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.transport not in ["http", "stdio"]:
            raise ValueError(f"Unsupported transport: {self.transport}")
            
        if self.mem0_api_version not in ["v1", "v2"]:
            raise ValueError(f"Unsupported API version: {self.mem0_api_version}")
            
        # Validate Mem0 base URL
        parsed_url = urlparse(self.mem0_base_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid Mem0 base URL: {self.mem0_base_url}")
        
        # Set base_url from mem0_base_url if not explicitly set
        if self.base_url is None:
            self.base_url = self.mem0_base_url


def get_mcp_config() -> MCPConfig:
    """
    Get MCP configuration, trying to reuse Mem0 config when available
    """
    config = MCPConfig()
    
    # Try to use Mem0 configuration if available
    if MEM0_CONFIG_AVAILABLE and mem0_config:
        # Reuse Mem0 server settings
        config.mem0_base_url = f"http://{mem0_config.api.host}:{mem0_config.api.port}"
        config.debug = mem0_config.api.debug
        config.log_level = mem0_config.logging.level.upper()
        config.log_to_file = mem0_config.logging.to_file
        config.log_file_path = mem0_config.logging.file_path.replace('.log', '_mcp.log')
    
    # Override with environment variables
    config.host = os.getenv("MCP_HOST", config.host)
    try:
        config.port = int(os.getenv("MCP_PORT", str(config.port)))
    except ValueError:
        # Fall back to default port if invalid value provided
        config.port = DEFAULT_PORT
    config.debug = os.getenv("MCP_DEBUG", str(config.debug)).lower() == "true"
    
    config.mem0_base_url = os.getenv("MEM0_BASE_URL", config.mem0_base_url)
    config.mem0_api_version = os.getenv("MEM0_API_VERSION", config.mem0_api_version)
    
    # Set API key and base URL for Mem0 client compatibility
    config.api_key = os.getenv("MEM0_API_KEY", config.api_key)
    config.base_url = os.getenv("MEM0_BASE_URL", config.mem0_base_url)  # Use mem0_base_url as fallback
    
    config.transport = os.getenv("MCP_TRANSPORT", config.transport)
    config.enable_streaming = os.getenv("MCP_ENABLE_STREAMING", str(config.enable_streaming)).lower() == "true"
    
    config.log_level = os.getenv("MCP_LOG_LEVEL", config.log_level)
    config.log_to_file = os.getenv("MCP_LOG_TO_FILE", str(config.log_to_file)).lower() == "true"
    config.log_file_path = os.getenv("MCP_LOG_FILE_PATH", config.log_file_path)
    
    config.max_concurrent_requests = int(os.getenv("MCP_MAX_CONCURRENT_REQUESTS", str(config.max_concurrent_requests)))
    config.request_timeout = int(os.getenv("MCP_REQUEST_TIMEOUT", str(config.request_timeout)))
    
    return config