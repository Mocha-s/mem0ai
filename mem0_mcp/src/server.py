"""
Main MCP server implementation for Mem0
"""

import asyncio
import json
import signal
import sys
from typing import Optional

from .config.settings import get_mcp_config, MCPConfig
from .transport.http_transport import HTTPTransport
from .protocol.mcp_handler import MCPProtocolHandler
from .protocol.jsonrpc import JSONRPCHandler, JSONRPCRequest
from .tools.tool_loader import ToolLoader
from .tools.tool_manager import ToolManager
from .client.adapters import HybridAdapter
from .client.mem0_client import Mem0HTTPClient
from .utils.logger import setup_logging, get_logger
from .utils.errors import MCPError, ProtocolError
from .config.constants import ERROR_CODES

logger = get_logger(__name__)


class MCPServer:
    """
    Main MCP server class that coordinates all components
    Enhanced with hybrid architecture design
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or get_mcp_config()
        self.transport: Optional[HTTPTransport] = None
        self.tool_loader = ToolLoader()
        self.tool_manager: Optional[ToolManager] = None
        self.running = False
        
        # Setup logging
        setup_logging(
            level=self.config.log_level,
            log_to_file=self.config.log_to_file,
            log_file_path=self.config.log_file_path
        )
        
        logger.info(f"MCP Server initialized with enhanced architecture config: {self.config}")
    
    async def initialize(self) -> None:
        """Initialize server components with enhanced architecture"""
        try:
            # Initialize tool loader and load tool definitions
            self.tool_loader.load_tools()

            # Initialize Mem0 client and adapter for direct tool execution (MCP coordination pattern)
            mem0_client = Mem0HTTPClient(self.config)
            adapter = HybridAdapter(mem0_client)
            
            # Initialize tool manager with adapter for direct tool execution
            server_base_url = f"http://{self.config.host}:{self.config.port}"
            self.tool_manager = ToolManager(
                adapter=adapter,  # Enable direct tool execution with MCP coordination
                server_base_url=server_base_url
            )
            self.tool_manager.load_tools_from_definitions(self.tool_loader.tools)

            # Initialize protocol handler with tool manager
            self.protocol_handler = MCPProtocolHandler(
                server_name="mem0-mcp-server",
                server_version="2.0.0",
                tool_manager=self.tool_manager
            )
            
            # Initialize transport
            if self.config.transport == "http":
                self.transport = HTTPTransport(self.config, self._handle_message)
                # Register tool services with the FastAPI app instance from the transport
                self.tool_loader.register_tool_services(self.transport.app)
            else:
                raise ValueError(f"Unsupported transport: {self.config.transport}")
            
            logger.info(f"V2 architecture initialized successfully with {len(self.tool_manager.get_tool_names())} tools and MCP coordination adapter.")
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {str(e)}")
            raise
    
    async def _handle_message(self, message: str, session_id: Optional[str] = None) -> Optional[str]:
        """
        Handle incoming MCP messages (supports both single and batch requests per MCP 2025-03-26)

        Args:
            message: Raw message string (single JSON-RPC message or array for batch)
            session_id: Session ID for the message

        Returns:
            Response message (if any)
        """
        try:
            logger.debug(f"Processing message from session {session_id}: {message[:100]}...")

            # Parse JSON to check if it's a batch request
            try:
                parsed_data = json.loads(message)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {str(e)}")
                error_response = JSONRPCHandler.create_error_response(
                    ERROR_CODES["PARSE_ERROR"], "Parse error: Invalid JSON"
                )
                return error_response.to_json()

            # Handle JSON-RPC batch requests (MCP 2025-03-26 feature)
            if isinstance(parsed_data, list):
                return await self._handle_batch_message(parsed_data, session_id)

            # Handle single JSON-RPC message
            return await self._handle_single_message(message, session_id)
                
        except Exception as e:
            logger.error(f"Unexpected error handling message: {str(e)}")
            # Return generic error response
            error_response = JSONRPCHandler.create_error_response(
                -32603,  # Internal error
                f"Internal server error: {str(e)}",
                id=getattr(request, 'id', None) if 'request' in locals() else None
            )
            return error_response.to_json()

    async def _handle_batch_message(self, batch_data: list, session_id: Optional[str] = None) -> Optional[str]:
        """
        Handle JSON-RPC batch requests (MCP 2025-03-26 feature)

        Args:
            batch_data: List of JSON-RPC messages
            session_id: Session ID for the batch

        Returns:
            Batch response (if any responses needed)
        """
        if not batch_data:
            # Empty batch is invalid per JSON-RPC spec
            error_response = JSONRPCHandler.create_error_response(
                ERROR_CODES["INVALID_REQUEST"], "Invalid request: Empty batch"
            )
            return error_response.to_json()

        logger.debug(f"Processing batch of {len(batch_data)} messages")
        responses = []

        for item in batch_data:
            try:
                # Convert each item back to JSON string for individual processing
                item_message = json.dumps(item)
                response_str = await self._handle_single_message(item_message, session_id)

                if response_str:
                    # Parse response and add to batch
                    response_data = json.loads(response_str)
                    responses.append(response_data)

            except Exception as e:
                logger.error(f"Error processing batch item: {str(e)}")
                # Add error response for this item
                error_response = JSONRPCHandler.create_error_response(
                    ERROR_CODES["INTERNAL_ERROR"],
                    f"Error processing batch item: {str(e)}"
                )
                responses.append(error_response.to_dict())

        # Return batch response if there are any responses
        if responses:
            return json.dumps(responses)
        else:
            # All were notifications, return None (will result in 202 Accepted per MCP spec)
            return None

    async def _handle_single_message(self, message: str, session_id: Optional[str] = None) -> Optional[str]:
        """
        Handle a single JSON-RPC message

        Args:
            message: Raw message string
            session_id: Session ID for the message

        Returns:
            Response message (if any)
        """
        try:
            # Parse JSON-RPC message
            try:
                request = JSONRPCHandler.parse_message(message)
            except ProtocolError as e:
                logger.error(f"Protocol error parsing message: {str(e)}")
                error_response = JSONRPCHandler.create_error_response(
                    e.code, e.message, data=e.data
                )
                return error_response.to_json()

            # Ensure it's a request (not a response from client)
            if not isinstance(request, JSONRPCRequest):
                logger.warning("Received response instead of request, ignoring")
                return None

            # Validate request
            try:
                JSONRPCHandler.validate_request(request)
            except ProtocolError as e:
                logger.error(f"Request validation failed: {str(e)}")
                error_response = JSONRPCHandler.create_error_response(
                    e.code, e.message, data=e.data, id=request.id
                )
                return error_response.to_json()

            # Ensure tool manager is available before delegating to protocol handler
            if self.tool_manager is None:
                # Lazily initialize server components to ensure tool execution is available
                await self.initialize()

            # Handle message through protocol handler (pass tool executor)
            response = await self.protocol_handler.handle_message(request, tool_executor=self.tool_manager)

            if response:
                response_json = response.to_json()
                logger.debug(f"Sending response: {response_json[:100]}...")
                return response_json
            else:
                # No response needed (notification)
                logger.debug("No response needed for notification")
                return None

        except Exception as e:
            logger.error(f"Unexpected error handling single message: {str(e)}")
            error_response = JSONRPCHandler.create_error_response(
                ERROR_CODES["INTERNAL_ERROR"],
                f"Internal server error: {str(e)}"
            )
            return error_response.to_json()

    async def start(self) -> None:
        """Start the MCP server"""
        if self.running:
            logger.warning("Server is already running")
            return
        
        try:
            logger.info("Starting Mem0 MCP server...")
            
            # Initialize if not already done
            if not self.transport:
                await self.initialize()
            
            # Start transport
            self.running = True
            logger.info(f"Server starting on {self.config.host}:{self.config.port}")
            
            await self.transport.start()
            
        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}")
            self.running = False
            raise
    
    async def stop(self) -> None:
        """Stop the MCP server"""
        if not self.running:
            logger.warning("Server is not running")
            return
        
        logger.info("Stopping Mem0 MCP server...")
        
        self.running = False
        
        # Stop transport
        if self.transport:
            await self.transport.stop()
        
        # Cleanup tool manager
        if self.tool_manager and hasattr(self.tool_manager.http_client, 'aclose'):
            await self.tool_manager.http_client.aclose()
        
        logger.info("Mem0 MCP server stopped")
    
    async def health_check(self) -> dict:
        """Get server health status"""
        health_data = {
            "status": "healthy" if self.running else "stopped",
            "transport": self.config.transport,
            "mem0_url": self.config.mem0_base_url,
            "api_version": self.config.mem0_api_version,
            "sessions": 0
        }
        
        if self.transport and hasattr(self.transport, 'get_session_count'):
            health_data["sessions"] = self.transport.get_session_count()
        
        return health_data
    
    def __repr__(self) -> str:
        return f"MCPServer(running={self.running}, transport={self.config.transport})"


async def run_server(config: Optional[MCPConfig] = None) -> None:
    """
    Run the MCP server with proper signal handling
    
    Args:
        config: Optional configuration (uses default if not provided)
    """
    server = MCPServer(config)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(server.stop())
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
    finally:
        await server.stop()


def main():
    """Main entry point"""
    try:
        config = get_mcp_config()
        logger.info(f"Starting Mem0 MCP Server with config: {config}")
        
        # Run server
        asyncio.run(run_server(config))
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()