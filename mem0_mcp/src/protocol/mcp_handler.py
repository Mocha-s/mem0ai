"""
MCP protocol handler for processing MCP-specific messages
"""

from typing import Any, Dict, List, Optional, Tuple, Callable
import time
import asyncio
from dataclasses import dataclass, field

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
    UPDATE_MEMORY_SCHEMA,
    BATCH_DELETE_MEMORIES_SCHEMA,
    # Graph Management Schemas have been removed
    SELECTIVE_MEMORY_SCHEMA,
    CRITERIA_RETRIEVAL_SCHEMA
)

logger = get_logger(__name__)


# MCP 2025-06-18 notification support
@dataclass
class NotificationManager:
    """Manages client notifications including listChanged events"""
    
    # Callback for sending notifications to client
    notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    
    # Track last modification time of tool lists
    tools_last_modified: float = field(default_factory=time.time)
    
    async def send_tools_list_changed(self):
        """Send tools/list_changed notification to client if callback is available"""
        if self.notification_callback:
            try:
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/tools/list_changed"
                }
                await self.notification_callback("tools/list_changed", notification)
                logger.debug("Sent tools/list_changed notification")
            except Exception as e:
                logger.warning(f"Failed to send tools/list_changed notification: {e}")
    
    def mark_tools_changed(self):
        """Mark tools as changed and schedule notification if event loop is running"""
        self.tools_last_modified = time.time()
        # Only schedule notification if we have an event loop running
        try:
            loop = asyncio.get_running_loop()
            # Schedule notification in background
            asyncio.create_task(self.send_tools_list_changed())
        except RuntimeError:
            # No event loop running, notification will be sent when needed
            logger.debug("No event loop running, tools changed notification deferred")


class MCPProtocolHandler:
    """
    Handler for MCP protocol messages and lifecycle
    """
    
    def __init__(self, server_name: str = "mem0-mcp-server", server_version: str = "1.0.0", tool_manager=None):
        self.server_name = server_name
        self.server_version = server_version
        self.initialized = False
        self.client_capabilities: Optional[ClientCapabilities] = None
        self.tool_manager = tool_manager
        self.protocol_version = "2025-06-18"  # Default to latest version
        
        # Initialize notification manager for MCP 2025-06-18 features
        self.notification_manager = NotificationManager()

        # Tool definitions are now managed by ToolManager via tools.json
        # No static tool definitions needed in v2 service-oriented architecture
        
        logger.info(f"MCP Protocol Handler initialized for {server_name} v{server_version}")
    
    def set_notification_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback function for sending notifications to client"""
        self.notification_manager.notification_callback = callback
        logger.debug("Notification callback registered")
    
    def negotiate_protocol_version(self, client_version: str) -> str:
        """
        Negotiate protocol version with client using intelligent fallback strategy
        
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
        
        # Intelligent fallback: find the highest compatible version
        # Sort versions in descending order to prioritize newer versions
        sorted_versions = sorted(SUPPORTED_MCP_VERSIONS, reverse=True)
        
        # Try to find a version that's backward compatible
        for version in sorted_versions:
            if self._is_version_compatible(client_version, version):
                logger.info(f"Using compatible version {version} for client {client_version}")
                return version
        
        # Fall back to the default server version
        logger.warning(f"Client protocol version {client_version} not compatible. Using server version {MCP_VERSION}")
        return MCP_VERSION
    
    def _is_version_compatible(self, client_version: str, server_version: str) -> bool:
        """
        Check if client version is compatible with server version
        
        Args:
            client_version: Client's version
            server_version: Server's version
            
        Returns:
            True if compatible, False otherwise
        """
        try:
            # Parse version strings (e.g., "2025-06-18")
            client_parts = client_version.split('-')
            server_parts = server_version.split('-')
            
            if len(client_parts) == 3 and len(server_parts) == 3:
                # Convert to comparable integers
                client_date = int(client_parts[0]) * 10000 + int(client_parts[1]) * 100 + int(client_parts[2])
                server_date = int(server_parts[0]) * 10000 + int(server_parts[1]) * 100 + int(server_parts[2])
                
                # Server can handle clients from the same version or older
                return client_date <= server_date
        except (ValueError, IndexError):
            logger.debug(f"Could not parse version strings: client={client_version}, server={server_version}")
        
        return False
    
    def get_server_capabilities(self) -> ServerCapabilities:
        """Get server capabilities with MCP 2025-06-18 enhancements"""
        capabilities = ServerCapabilities(
            tools={"listChanged": True},      # Support tools with listChanged notifications  
            resources={},                     # Resources capability (future expansion)
            prompts={},                       # Prompts capability (future expansion)
            logging={}                        # Logging callbacks (future expansion)
        )
        
        # Add protocol version-specific capabilities
        if self.protocol_version == "2025-06-18":
            # Enhanced capabilities for 2025-06-18
            capabilities.tools.update({
                "outputSchema": True,         # Support outputSchema in tool definitions
                "annotations": True,          # Support annotations in tool definitions
                "structuredContent": True     # Support structured content in results
            })
        
        return capabilities
    
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

            # Store the agreed protocol version for tool formatting
            self.protocol_version = agreed_version
            logger.info(f"Using client's protocol version: {agreed_version}")

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
        Handle tools/list request with MCP 2025-06-18 support

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
            # Use tool manager for v2 service-oriented architecture
            if self.tool_manager:
                tools_info = self.tool_manager.get_tool_info(self.protocol_version)
                logger.debug(f"Returning {len(tools_info)} tools from ToolManager (protocol: {self.protocol_version})")

                # Return tools directly as dict (MCP 2025-06-18 format)
                return JSONRPCHandler.create_response(
                    result={"tools": tools_info},
                    id=request.id
                )
            else:
                # No tool manager available - return empty tools list
                logger.warning("No tool manager available, returning empty tools list")
                return JSONRPCHandler.create_response(
                    result={"tools": []},
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
            
            # Handle special case: Cherry Studio might send tool parameters directly in params
            # without the standard MCP "name" and "arguments" structure
            if not tool_name and "query" in request.params:
                # This looks like a direct tool call, try to infer the tool name
                # Could be search_memories or other search tools
                tool_name = "search_memories"  # Default to memory search
                arguments = request.params.copy()
                logger.info(f"Detected direct tool call format, inferred tool: {tool_name}")
            
            # Extract identity parameters from top-level params (Cherry Studio format)
            # and merge them into arguments for tool execution
            identity_params = ["user_id", "agent_id", "run_id", "session_id"]
            extracted_identity = {}
            
            # First, extract from top-level params (Cherry Studio format)
            for param in identity_params:
                if param in request.params and param not in arguments:
                    arguments[param] = request.params[param]
                    extracted_identity[param] = request.params[param]
            
            # Then, check if identity parameters exist in arguments and should be overridden by context
            # This handles the case where frontend sends identity in arguments but URL path has different identity
            context_identity = None
            try:
                from ..identity.context_manager import IdentityManager
                context_identity = IdentityManager.get_current_identity()
                if context_identity.is_valid():
                    logger.info(f"Context identity found: {context_identity}")
                    # Override arguments with context identity if context is valid
                    if context_identity.user_id and context_identity.user_id != arguments.get('user_id'):
                        logger.info(f"Overriding user_id from '{arguments.get('user_id')}' to '{context_identity.user_id}'")
                        arguments['user_id'] = context_identity.user_id
                    if context_identity.agent_id and context_identity.agent_id != arguments.get('agent_id'):
                        logger.info(f"Overriding agent_id from '{arguments.get('agent_id')}' to '{context_identity.agent_id}'")
                        arguments['agent_id'] = context_identity.agent_id
                    if context_identity.run_id and context_identity.run_id != arguments.get('run_id'):
                        logger.info(f"Overriding run_id from '{arguments.get('run_id')}' to '{context_identity.run_id}'")
                        arguments['run_id'] = context_identity.run_id
            except Exception as e:
                logger.debug(f"Could not get context identity: {e}")
            
            logger.info(f"Tool call: {tool_name}")
            logger.info(f"Original params: {request.params}")
            logger.info(f"Extracted identity: {extracted_identity}")
            logger.info(f"Final arguments: {arguments}")
            
            if not tool_name:
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["INVALID_PARAMS"],
                    "Tool name is required",
                    id=request.id
                )
            
            # Check if tool exists using tool manager (v2 service-oriented architecture)
            if self.tool_manager:
                available_tools = self.tool_manager.get_tool_names()
                if tool_name not in available_tools:
                    return JSONRPCHandler.create_error_response(
                        ERROR_CODES["METHOD_NOT_FOUND"],
                        f"Tool '{tool_name}' not found. Available tools: {', '.join(available_tools)}",
                        id=request.id
                    )

                logger.debug(f"Executing tool: {tool_name} with arguments: {arguments}")

                # Execute tool using service-oriented architecture
                try:
                    result = await self.tool_manager.execute_tool(tool_name, arguments)
                    return JSONRPCHandler.create_response(
                        result=result.to_dict(),
                        id=request.id
                    )
                except Exception as e:
                    logger.error(f"Tool manager execution error: {str(e)}")
                    return JSONRPCHandler.create_error_response(
                        ERROR_CODES["INTERNAL_ERROR"],
                        f"Tool execution failed: {str(e)}",
                        id=request.id
                    )
            else:
                # No tool manager available
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["INTERNAL_ERROR"],
                    "Tool manager not available",
                    id=request.id
                )
            
        except Exception as e:
            logger.error(f"Error handling tools/call: {str(e)}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal error executing tool: {str(e)}",
                id=request.id
            )
    
    def handle_ping(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """
        Handle ping request - simple health check

        Args:
            request: Ping request

        Returns:
            Ping response
        """
        try:
            logger.debug("Handling ping request")
            return JSONRPCHandler.create_response(
                result={"status": "ok", "message": "Mem0 MCP Server is running"},
                id=request.id
            )
        except Exception as e:
            logger.error(f"Error handling ping: {str(e)}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal error handling ping: {str(e)}",
                id=request.id
            )

    def handle_prompts_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """
        Handle prompts/list request - return empty list as we don't support prompts

        Args:
            request: Prompts list request

        Returns:
            Empty prompts list response
        """
        try:
            logger.debug("Handling prompts/list request - returning empty list")
            return JSONRPCHandler.create_response(
                result={"prompts": []},
                id=request.id
            )
        except Exception as e:
            logger.error(f"Error handling prompts/list: {str(e)}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal error handling prompts/list: {str(e)}",
                id=request.id
            )





    def handle_resources_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """
        Handle resources/list request - return empty list as we don't support resources

        Args:
            request: Resources list request

        Returns:
            Empty resources list response
        """
        try:
            logger.debug("Handling resources/list request - returning empty list")
            return JSONRPCHandler.create_response(
                result={"resources": []},
                id=request.id
            )
        except Exception as e:
            logger.error(f"Error handling resources/list: {str(e)}")
            return JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal error handling resources/list: {str(e)}",
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

        # Handle additional MCP methods for better client compatibility
        elif method == "ping":
            return self.handle_ping(request)

        elif method == MCPMessageType.PROMPTS_LIST.value:
            return self.handle_prompts_list(request)



        elif method == MCPMessageType.RESOURCES_LIST.value:
            return self.handle_resources_list(request)



        else:
            # Check if this is a standard MCP method that we just don't implement yet
            standard_mcp_methods = [
                "resources/unsubscribe", "logging/setLevel",
                "completion/complete", "sampling/createMessage"
            ]
            
            if method in standard_mcp_methods:
                logger.debug(f"Standard MCP method not implemented: {method}")
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["METHOD_NOT_FOUND"],
                    f"Method '{method}' not implemented",
                    id=request.id
                )
            else:
                logger.warning(f"Unknown method: {method}")
                return JSONRPCHandler.create_error_response(
                    ERROR_CODES["METHOD_NOT_FOUND"],
                    f"Method '{method}' not found",
                    id=request.id
                )