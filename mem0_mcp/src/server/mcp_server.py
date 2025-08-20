"""
MCP Server Implementation

Main MCP server coordinating between clients and Mem0 services.
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Use absolute imports since we're adding src to path
from src.transport.streamable_http import StreamableHTTPTransport, MCPSession
from src.gateway.tool_manager import tool_manager
from src.registry.registry_manager import registry
from src.protocol.messages import ToolResult, ErrorResult, TextContent

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """MCP Server configuration"""
    host: str = "127.0.0.1"
    port: int = 8080
    endpoint_path: str = "/mcp"
    session_timeout: int = 3600
    allowed_origins: List[str] = None
    protocol_version: str = "2025-06-18"

class MCPServer:
    """
    Model Context Protocol Server
    
    Coordinates between MCP clients and Mem0 memory services.
    Implements MCP 2025-06-18 specification with Streamable HTTP transport.
    """
    
    def __init__(self, config: MCPServerConfig = None):
        self.config = config or MCPServerConfig()
        if self.config.allowed_origins is None:
            self.config.allowed_origins = [
                "http://localhost",
                "http://127.0.0.1", 
                "vscode-file://vscode-app"  # VS Code extension
            ]
        
        # Initialize transport
        self.transport = StreamableHTTPTransport(
            host=self.config.host,
            port=self.config.port,
            endpoint_path=self.config.endpoint_path,
            session_timeout=self.config.session_timeout,
            allowed_origins=self.config.allowed_origins
        )
        
        # Initialize tool manager and registry
        self.tool_manager = None
        self.registry = None
        
        # Server state
        self.running = False
        self.server_info = {
            "name": "mem0-mcp-server",
            "version": "1.0.0"
        }
    
    async def start(self):
        """Start the MCP server"""
        try:
            logger.info("Starting Mem0 MCP Server...")
            
            # Initialize components
            await self._initialize_components()
            
            # Register handlers
            self._register_handlers()
            
            # Start transport
            await self.transport.start()
            
            self.running = True
            logger.info(f"MCP Server started on {self.config.host}:{self.config.port}{self.config.endpoint_path}")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server"""
        try:
            logger.info("Stopping Mem0 MCP Server...")
            
            self.running = False
            
            # Stop transport
            await self.transport.stop()
            
            logger.info("MCP Server stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop MCP server: {e}")
            raise
    
    async def _initialize_components(self):
        """Initialize tool manager and registry"""
        global tool_manager, registry
        
        # Initialize tool manager
        await tool_manager.initialize()
        self.tool_manager = tool_manager
        
        # Get registry
        self.registry = registry
        
        logger.info("MCP server components initialized")
    
    def _register_handlers(self):
        """Register JSON-RPC method handlers"""
        
        # Core MCP methods
        self.transport.register_handler("initialize", self._handle_initialize)
        self.transport.register_handler("notifications/initialized", self._handle_initialized)
        # Also register a fallback for clients that send 'initialized' directly
        self.transport.register_handler("initialized", self._handle_initialized)
        
        # Capability discovery
        self.transport.register_handler("tools/list", self._handle_tools_list)
        self.transport.register_handler("tools/call", self._handle_tools_call)
        
        # Resource methods (if needed)
        self.transport.register_handler("resources/list", self._handle_resources_list)
        self.transport.register_handler("resources/read", self._handle_resources_read)
        
        # Prompt methods (if needed)
        self.transport.register_handler("prompts/list", self._handle_prompts_list)
        self.transport.register_handler("prompts/get", self._handle_prompts_get)
        
        # Logging
        self.transport.register_handler("logging/setLevel", self._handle_logging_set_level)
        
        logger.info("MCP handlers registered")
    
    async def _handle_initialize(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle initialize request"""
        try:
            client_info = params.get("clientInfo", {})
            protocol_version = params.get("protocolVersion", "2025-06-18")
            capabilities = params.get("capabilities", {})
            
            logger.info(f"Initialize from client: {client_info.get('name', 'unknown')} v{client_info.get('version', 'unknown')}")
            
            # Store client info in session
            session.client_info = client_info
            
            # Multi-protocol support for Dify compatibility
            client_version = protocol_version
            client_name = client_info.get("name", "").lower()
            negotiated_version = self.config.protocol_version  # Default: "2025-06-18"
            
            # Dify compatibility: Support multiple protocol versions
            supported_versions = ["2025-06-18", "2025-03-26", "2024-11-05", "2024-10-07"]
            
            if client_version in supported_versions:
                negotiated_version = client_version
                logger.info(f"🎯 CLIENT COMPAT: Using requested protocol version {negotiated_version}")
            elif "dify" in client_name:
                # Dify may work better with slightly older versions
                negotiated_version = "2025-03-26"
                logger.info(f"🎯 DIFY COMPAT: Using fallback protocol version {negotiated_version}")
            
            # Build capabilities - some older clients may not support all features
            capabilities = {
                "tools": {
                    "listChanged": True
                }
            }
            
            # Add optional capabilities based on protocol version
            if negotiated_version >= "2025-01-01":  # Modern versions
                capabilities.update({
                    "resources": {
                        "subscribe": False,
                        "listChanged": False
                    },
                    "prompts": {
                        "listChanged": False
                    },
                    "logging": {}
                })
            
            # Return server capabilities
            response = {
                "protocolVersion": negotiated_version,
                "serverInfo": self.server_info,
                "capabilities": capabilities
            }
            
            # Instructions field - some clients may not expect this
            if not ("dify" in client_name and client_info.get("version", "").startswith("v1.7")):
                response["instructions"] = "This is a Mem0 MCP server providing intelligent memory operations. Use the available tools to add, search, update, and delete memories."
            
            logger.debug(f"✅ INIT SUCCESS: protocol={negotiated_version}, client={client_name}")
            return response
            
        except Exception as e:
            logger.error(f"Initialize error: {e}")
            raise Exception(f"Failed to initialize: {str(e)}")
    
    async def _handle_initialized(self, params: Dict[str, Any], session: MCPSession) -> None:
        """Handle initialized notification - confirm session is ready"""
        logger.info(f"📋 Client confirmed initialization: {session.session_id}")
        session.initialized = True
        
        # Log client info if available
        if hasattr(session, 'client_info') and session.client_info:
            client_name = session.client_info.get('name', 'unknown')
            client_version = session.client_info.get('version', 'unknown')
            logger.info(f"🔗 Session fully activated for {client_name} v{client_version}")
        
        # No response required for notifications
    
    async def _handle_tools_list(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle tools/list request - MCP 2025-06-18 compliant"""
        logger.debug(f"🔧 Tools list request for session {session.session_id}")
        try:
            # Support pagination as per MCP specification
            cursor = params.get("cursor")
            # For simplicity, we don't implement complex pagination since we have a small number of tools
            # In a production system with many tools, proper pagination would be implemented
            
            # 动态获取所有注册的工具
            tools = await self.tool_manager.list_tools()
            
            # 转换为MCP格式 - 符合MCP 2025-06-18规范
            mcp_tools = []
            for tool_config in tools:
                mcp_tool = {
                    "name": tool_config["name"],
                    "description": tool_config["description"],
                    "inputSchema": tool_config["inputSchema"]
                }
                
                # Add optional fields if present
                if "title" in tool_config:
                    mcp_tool["title"] = tool_config["title"]
                
                # Add outputSchema if defined (MCP 2025-06-18 feature)
                if "outputSchema" in tool_config:
                    mcp_tool["outputSchema"] = tool_config["outputSchema"]
                
                # Add annotations if present (for trust & safety)
                if "annotations" in tool_config:
                    mcp_tool["annotations"] = tool_config["annotations"]
                
                mcp_tools.append(mcp_tool)
            
            logger.debug(f"🔧 Returning {len(mcp_tools)} tools for session {session.session_id}")
            
            # Return result with optional nextCursor for pagination
            result = {"tools": mcp_tools}
            # Since we're not implementing pagination, we don't include nextCursor
            # In a real implementation: if has_more_tools: result["nextCursor"] = "next-page-cursor"
            
            return result
            
        except Exception as e:
            logger.error(f"Tools list error: {e}")
            # 作为fallback，返回基础工具 - 符合MCP规范格式
            fallback_tools = [
                {
                    "name": "add_memory",
                    "title": "Memory Addition Tool",  # MCP 2025-06-18: Optional title field
                    "description": "Add new memory to Mem0 with intelligent extraction and conflict resolution",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "messages": {
                                "type": "array",
                                "description": "Conversation messages to extract memory from",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string", "enum": ["user", "assistant"]},
                                        "content": {"type": "string"}
                                    }
                                }
                            },
                            "user_id": {"type": "string", "description": "Unique user identifier"}
                        },
                        "required": ["messages", "user_id"]
                    }
                },
                {
                    "name": "search_memories",
                    "title": "Memory Search Tool",  # MCP 2025-06-18: Optional title field
                    "description": "Search memories with advanced retrieval strategies and filtering",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Natural language search query"},
                            "user_id": {"type": "string", "description": "User identifier for scoped search"}
                        },
                        "required": ["query", "user_id"]
                    }
                }
            ]
            logger.warning(f"Using fallback tools due to error: {e}")
            return {"tools": fallback_tools}
    
    async def _handle_tools_call(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle tools/call request - MCP 2025-06-18 compliant"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            # Validate required parameters according to MCP specification
            if not tool_name:
                # Return protocol error for missing tool name - raise to get proper JSON-RPC error
                raise ValueError("Tool name parameter is required")
            
            logger.info(f"Calling tool: {tool_name}")
            
            # Call tool through tool manager
            result = await self.tool_manager.call_tool(tool_name, arguments)
            
            # Convert result to MCP format - distinguish between protocol errors and tool execution errors
            if isinstance(result, ErrorResult) or (hasattr(result, 'is_error') and result.is_error):
                # Tool execution error (not protocol error)
                if isinstance(result, ErrorResult):
                    error_msg = result.error_message
                else:
                    error_msg = getattr(result, 'error_message', str(result))
                
                # MCP 2025-06-18: Use isError flag for tool execution errors
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Tool execution failed: {error_msg}"
                        }
                    ],
                    "isError": True  # Indicates tool execution error, not protocol error
                }
            else:
                # Success result - format according to MCP tools specification
                # Check if it's a ToolResult by class name as fallback (handles import edge cases)
                is_tool_result = isinstance(result, ToolResult) or result.__class__.__name__ == 'ToolResult'
                
                if is_tool_result:
                    # Convert ToolResult to JSON-serializable format
                    response = {
                        "isError": getattr(result, 'is_error', False)
                    }
                    
                    # Handle content blocks - convert to JSON-serializable format
                    if hasattr(result, 'content') and result.content:
                        content_list = []
                        for content_block in result.content:
                            if hasattr(content_block, 'type') and hasattr(content_block, 'text'):
                                content_list.append({
                                    "type": content_block.type,
                                    "text": content_block.text
                                })
                            elif isinstance(content_block, dict):
                                content_list.append(content_block)
                            else:
                                # Fallback for string content
                                content_list.append({
                                    "type": "text",
                                    "text": str(content_block)
                                })
                        response["content"] = content_list
                    
                    # Handle structured content
                    if hasattr(result, 'structured_content') and result.structured_content:
                        response["structuredContent"] = result.structured_content
                    
                    return response
                else:
                    # Simple result - wrap in text content
                    # Handle case where result might be a ToolResult but not detected properly
                    if hasattr(result, 'content') and hasattr(result, 'is_error'):
                        # This is actually a ToolResult-like object
                        content_list = []
                        if hasattr(result, 'content') and result.content:
                            for content_block in result.content:
                                if hasattr(content_block, 'type') and hasattr(content_block, 'text'):
                                    content_list.append({
                                        "type": content_block.type,
                                        "text": content_block.text
                                    })
                                elif isinstance(content_block, dict):
                                    content_list.append(content_block)
                                else:
                                    # Fallback for string content
                                    content_list.append({
                                        "type": "text",
                                        "text": str(content_block)
                                    })
                        
                        response = {
                            "content": content_list,
                            "isError": getattr(result, 'is_error', False)
                        }
                        
                        # Add structured content if available
                        if hasattr(result, 'structured_content') and result.structured_content:
                            response["structuredContent"] = result.structured_content
                            
                        return response
                    else:
                        # Truly simple result
                        return {
                            "content": [
                                {
                                    "type": "text", 
                                    "text": str(result)
                                }
                            ],
                            "isError": False
                        }
            
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            # MCP 2025-06-18: Distinguish between protocol errors and tool execution errors
            if "Tool name parameter is required" in str(e) or "missing" in str(e).lower():
                # This is a protocol error, should raise exception to return proper JSON-RPC error
                raise e
            else:
                # This is a tool execution error, return with isError flag
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Tool execution failed: {str(e)}"
                        }
                    ],
                    "isError": True
                }
    
    async def _handle_resources_list(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle resources/list request"""
        # No resources provided by this server
        return {"resources": []}
    
    async def _handle_resources_read(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle resources/read request"""
        raise Exception("No resources available")
    
    async def _handle_prompts_list(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle prompts/list request"""
        # No prompts provided by this server
        return {"prompts": []}
    
    async def _handle_prompts_get(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle prompts/get request"""
        raise Exception("No prompts available")
    
    async def _handle_logging_set_level(self, params: Dict[str, Any], session: MCPSession) -> None:
        """Handle logging/setLevel notification"""
        level = params.get("level", "info")
        logger.info(f"Setting log level to: {level}")
        
        # Convert MCP log level to Python log level
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR
        }
        
        if level.lower() in level_map:
            logging.getLogger().setLevel(level_map[level.lower()])
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        transport_stats = self.transport.get_session_stats()
        
        # Get tool manager stats
        tool_stats = {}
        if self.tool_manager:
            tool_stats = {
                "registered_tools": len(self.registry.discover_services()) if self.registry else 0,
                "health_status": "unknown"  # Could implement health check
            }
        
        return {
            "server_info": self.server_info,
            "running": self.running,
            "protocol_version": self.config.protocol_version,
            "transport": transport_stats,
            "tools": tool_stats
        }

# Global server instance
mcp_server: Optional[MCPServer] = None

async def create_server(config: MCPServerConfig = None) -> MCPServer:
    """Create and initialize MCP server"""
    global mcp_server
    
    if mcp_server is None:
        mcp_server = MCPServer(config)
    
    return mcp_server

async def start_server(config: MCPServerConfig = None) -> MCPServer:
    """Start MCP server"""
    server = await create_server(config)
    await server.start()
    return server

async def stop_server():
    """Stop MCP server"""
    global mcp_server
    
    if mcp_server:
        await mcp_server.stop()
        mcp_server = None