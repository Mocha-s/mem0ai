"""
MCP protocol handler for processing MCP-specific messages
"""

from typing import Any, Dict, List, Optional, Tuple
from ..config.constants import MCP_VERSION, ERROR_CODES, SUPPORTED_MCP_VERSIONS
from ..utils.errors import ProtocolError
from ..utils.logger import get_logger
from .jsonrpc import JSONRPCRequest, JSONRPCResponse, JSONRPCHandler, JSONRPCError
from .message_types import (
    MCPMessageType,
    InitializeRequest,
    InitializeResponse,
    ServerInfo,
    ServerCapabilities,
    ClientCapabilities,
    ToolsListRequest,
    ToolsListResponse,
    ToolInfo,
    ToolsCallRequest,
    ToolsCallResponse,
    ADD_MEMORY_SCHEMA,
    SEARCH_MEMORIES_SCHEMA,
    GET_MEMORIES_SCHEMA,
    GET_MEMORY_BY_ID_SCHEMA,
    DELETE_MEMORY_SCHEMA,
    BATCH_DELETE_MEMORIES_SCHEMA
)

logger = get_logger(__name__)


class MCPProtocolHandler:
    """
    Handler for MCP protocol messages and lifecycle
    """
    
    def __init__(self, server_name: str = "mem0-mcp-server", server_version: str = "1.0.0"):
        self.server_name = server_name
        self.server_version = server_version
        self.initialized = False
        self.client_capabilities: Optional[ClientCapabilities] = None
        
        # Define available tools
        self.tools = [
            ToolInfo(
                name="add_memory",
                description="Add new memories from messages",
                inputSchema=ADD_MEMORY_SCHEMA
            ),
            ToolInfo(
                name="search_memories",
                description="Search memories using natural language query",
                inputSchema=SEARCH_MEMORIES_SCHEMA
            ),
            ToolInfo(
                name="get_memories",
                description="Get memories for a user, agent, or run",
                inputSchema=GET_MEMORIES_SCHEMA
            ),
            ToolInfo(
                name="get_memory_by_id",
                description="Get a specific memory by its ID",
                inputSchema=GET_MEMORY_BY_ID_SCHEMA
            ),
            ToolInfo(
                name="delete_memory",
                description="Delete a specific memory by its ID",
                inputSchema=DELETE_MEMORY_SCHEMA
            ),
            ToolInfo(
                name="batch_delete_memories",
                description="Delete all memories for a user, agent, or run",
                inputSchema=BATCH_DELETE_MEMORIES_SCHEMA
            )
        ]
        
        logger.info(f"MCP Protocol Handler initialized for {server_name} v{server_version}")
    
    def negotiate_protocol_version(self, client_version: str) -> str:
        """
        Negotiate protocol version with client
        
        Args:
            client_version: Client's requested protocol version
            
        Returns:
            Agreed protocol version
        """
        logger.debug(f"Negotiating protocol version. Client: {client_version}, Supported: {SUPPORTED_MCP_VERSIONS}")
        
        # If client version is supported, use it
        if client_version in SUPPORTED_MCP_VERSIONS:
            logger.info(f"Using client's protocol version: {client_version}")
            return client_version
        
        # Otherwise, use server's default and warn
        logger.warning(f"Client protocol version {client_version} not supported. Using server version {MCP_VERSION}")
        return MCP_VERSION
    
    def get_server_capabilities(self) -> ServerCapabilities:
        """Get server capabilities"""
        return ServerCapabilities(
            tools={},      # Empty dict indicates tools are supported
            resources={},  # Empty dict indicates no resources supported
            prompts={},    # Empty dict indicates no prompts supported
            logging={}     # Empty dict indicates no logging callbacks supported
        )
    
    def handle_initialize(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """
        Handle initialize request
        
        Args:
            request: Initialize request
            
        Returns:
            Initialize response
        """
        try:
            if not request.params or not isinstance(request.params, dict):
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["INVALID_PARAMS"],
                    "Initialize request must have params object",
                    id=request.id
                )
            
            # Parse client info and capabilities
            protocol_version = request.params.get("protocolVersion")
            if not protocol_version:
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["INVALID_PARAMS"],
                    "protocolVersion is required",
                    id=request.id
                )
            
            # Negotiate protocol version
            agreed_version = self.negotiate_protocol_version(protocol_version)
            
            client_info = request.params.get("clientInfo", {})
            client_capabilities = request.params.get("capabilities", {})
            
            # Store client capabilities
            self.client_capabilities = ClientCapabilities(
                sampling=client_capabilities.get("sampling"),
                experimental=client_capabilities.get("experimental")
            )
            
            # Create response
            response = InitializeResponse(
                protocolVersion=agreed_version,
                capabilities=self.get_server_capabilities(),
                serverInfo=ServerInfo(
                    name=self.server_name,
                    version=self.server_version
                )
            )
            
            self.initialized = True
            logger.info(f"Initialized session with client: {client_info.get('name', 'unknown')}")
            
            return JSONRPCHandler.create_response(
                result=response.to_dict(),
                id=request.id
            )
            
        except Exception as e:
            logger.error(f"Error handling initialize: {str(e)}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal error during initialization: {str(e)}",
                id=request.id
            )
    
    def handle_tools_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """
        Handle tools/list request
        
        Args:
            request: Tools list request
            
        Returns:
            Tools list response
        """
        if not self.initialized:
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INVALID_REQUEST"],
                "Session not initialized",
                id=request.id
            )
        
        try:
            response = ToolsListResponse(tools=self.tools)
            
            logger.debug(f"Returning {len(self.tools)} available tools")
            
            return JSONRPCHandler.create_response(
                result=response.to_dict(),
                id=request.id
            )
            
        except Exception as e:
            logger.error(f"Error handling tools/list: {str(e)}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal error listing tools: {str(e)}",
                id=request.id
            )
    
    async def handle_tools_call(self, request: JSONRPCRequest, tool_executor) -> JSONRPCResponse:
        """
        Handle tools/call request
        
        Args:
            request: Tools call request
            tool_executor: Tool executor instance
            
        Returns:
            Tools call response
        """
        if not self.initialized:
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INVALID_REQUEST"],
                "Session not initialized",
                id=request.id
            )
        
        try:
            if not request.params or not isinstance(request.params, dict):
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["INVALID_PARAMS"],
                    "Tools call request must have params object",
                    id=request.id
                )
            
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            if not tool_name:
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["INVALID_PARAMS"],
                    "Tool name is required",
                    id=request.id
                )
            
            # Check if tool exists
            tool_names = [tool.name for tool in self.tools]
            if tool_name not in tool_names:
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["METHOD_NOT_FOUND"],
                    f"Tool '{tool_name}' not found. Available tools: {', '.join(tool_names)}",
                    id=request.id
                )
            
            logger.debug(f"Executing tool: {tool_name} with arguments: {arguments}")
            
            # Execute tool asynchronously
            return await tool_executor.execute_tool(tool_name, arguments, request.id)
            
        except Exception as e:
            logger.error(f"Error handling tools/call: {str(e)}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal error executing tool: {str(e)}",
                id=request.id
            )
    
    async def handle_message(self, request: JSONRPCRequest, tool_executor=None) -> Optional[JSONRPCResponse]:
        """
        Route MCP message to appropriate handler
        
        Args:
            request: JSON-RPC request
            tool_executor: Tool executor for handling tool calls
            
        Returns:
            JSON-RPC response (None for notifications)
        """
        method = request.method
        
        # Handle notifications (no response expected)
        if JSONRPCHandler.is_notification(request):
            if method == MCPMessageType.INITIALIZED.value:
                logger.info("Client sent initialized notification")
                return None
            elif method == "notifications/initialized":
                logger.info("Client sent notifications/initialized")
                return None
            else:
                logger.debug(f"Unhandled notification method: {method}")
                return None
        
        # Handle requests (response expected)
        if method == MCPMessageType.INITIALIZE.value:
            return self.handle_initialize(request)
        
        elif method == MCPMessageType.TOOLS_LIST.value:
            return self.handle_tools_list(request)
        
        elif method == MCPMessageType.TOOLS_CALL.value:
            if tool_executor is None:
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["INTERNAL_ERROR"],
                    "Tool executor not available",
                    id=request.id
                )
            return await self.handle_tools_call(request, tool_executor)
        
        else:
            logger.warning(f"Unknown method: {method}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["METHOD_NOT_FOUND"],
                f"Method '{method}' not found",
                id=request.id
            )