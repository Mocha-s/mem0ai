"""
Main MCP server implementation for Mem0
"""

import asyncio
import signal
import sys
from typing import Optional

from .config.settings import get_mcp_config, MCPConfig
from .transport.http_transport import HTTPTransport
from .protocol.mcp_handler import MCPProtocolHandler
from .protocol.jsonrpc import JSONRPCHandler, JSONRPCRequest
from .tools.memory_tools import MemoryToolsExecutor
from .utils.logger import setup_logging, get_logger
from .utils.errors import MCPError, ProtocolError

logger = get_logger(__name__)


class MCPServer:
    """
    Main MCP server class that coordinates all components
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or get_mcp_config()
        self.transport: Optional[HTTPTransport] = None
        self.protocol_handler: Optional[MCPProtocolHandler] = None
        self.tool_executor: Optional[MemoryToolsExecutor] = None
        self.running = False
        
        # Setup logging
        setup_logging(
            level=self.config.log_level,
            log_to_file=self.config.log_to_file,
            log_file_path=self.config.log_file_path
        )
        
        logger.info(f"MCP Server initialized with config: {self.config}")
    
    async def initialize(self) -> None:
        """Initialize server components"""
        try:
            # Initialize protocol handler
            self.protocol_handler = MCPProtocolHandler(
                server_name="mem0-mcp-server",
                server_version="1.0.0"
            )
            
            # Initialize tool executor
            self.tool_executor = MemoryToolsExecutor(self.config)
            await self.tool_executor.initialize()
            
            # Initialize transport
            if self.config.transport == "http":
                self.transport = HTTPTransport(self.config, self._handle_message)
            else:
                raise ValueError(f"Unsupported transport: {self.config.transport}")
            
            logger.info("All server components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {str(e)}")
            raise
    
    async def _handle_message(self, message: str, session_id: Optional[str] = None) -> Optional[str]:
        """
        Handle incoming MCP messages
        
        Args:
            message: Raw message string
            session_id: Session ID for the message
            
        Returns:
            Response message (if any)
        """
        try:
            logger.debug(f"Processing message from session {session_id}: {message[:100]}...")
            
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
            
            # Handle message through protocol handler
            response = await self.protocol_handler.handle_message(request, self.tool_executor)
            
            if response:
                response_json = response.to_json()
                logger.debug(f"Sending response: {response_json[:100]}...")
                return response_json
            else:
                # No response needed (notification)
                logger.debug("No response needed for notification")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error handling message: {str(e)}")
            # Return generic error response
            error_response = JSONRPCHandler.create_error_response(
                -32603,  # Internal error
                f"Internal server error: {str(e)}",
                id=getattr(request, 'id', None) if 'request' in locals() else None
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
        
        # Cleanup tool executor
        if self.tool_executor:
            await self.tool_executor.cleanup()
        
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