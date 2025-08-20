#!/usr/bin/env python3
"""
Production-ready MCP server startup script with optimized logging
"""

import sys
import os
import asyncio
import logging
import argparse
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Import after adding to path
try:
    from server.mcp_server import MCPServerConfig, start_server, stop_server
    from gateway.tool_manager import tool_manager
    from registry.registry_manager import registry
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📍 Current working directory:", os.getcwd())
    print("🔍 Python path:", sys.path)
    sys.exit(1)

# Configure production-level logging
def setup_logging(log_level: str = "INFO", enable_debug: bool = False):
    """Setup logging with production-appropriate levels"""
    
    # Map string levels to logging constants
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = level_map.get(log_level.upper(), logging.INFO)
    
    # If debug mode, override to DEBUG
    if enable_debug:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set specific logger levels for cleaner production logs
    if not enable_debug:
        # Suppress overly verbose aiohttp access logs in production
        logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
        
        # Keep transport layer at INFO for important connection events
        logging.getLogger('src.transport.streamable_http').setLevel(logging.INFO)
        
        # Keep server layer at INFO for tool operations
        logging.getLogger('server.mcp_server').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the Mem0 MCP server"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Mem0 MCP Server - Streamable HTTP Transport",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-host', '--host', 
                       default=os.getenv('MCP_HOST', '127.0.0.1'),
                       help='Server bind address')
    parser.add_argument('-p', '--port', 
                       type=int,
                       default=int(os.getenv('MCP_PORT', '8080')),
                       help='Server port')
    parser.add_argument('--log-level',
                       default=os.getenv('MCP_LOG_LEVEL', 'INFO'),
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Log level')
    parser.add_argument('--debug',
                       action='store_true',
                       help='Enable debug mode (overrides log-level)')
    parser.add_argument('--endpoint-path',
                       default=os.getenv('MCP_ENDPOINT_PATH', '/mcp'),
                       help='MCP endpoint path')
    parser.add_argument('--session-timeout',
                       type=int,
                       default=int(os.getenv('MCP_SESSION_TIMEOUT', '3600')),
                       help='Session timeout in seconds')
    parser.add_argument('--allowed-origins',
                       default=os.getenv('MCP_ALLOWED_ORIGINS', '*'),
                       help='Comma-separated list of allowed CORS origins')

    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.debug)
    
    # Parse allowed origins
    if args.allowed_origins == '*':
        allowed_origins = ['*']
    else:
        allowed_origins = [origin.strip() for origin in args.allowed_origins.split(',')]
    
    # Create server configuration
    config = MCPServerConfig(
        host=args.host,
        port=args.port,
        endpoint_path=args.endpoint_path,
        session_timeout=args.session_timeout,
        allowed_origins=allowed_origins,
        protocol_version="2025-06-18"
    )
    
    logger.info(f"🚀 Starting Mem0 MCP Server")
    logger.info(f"📍 Host: {config.host}:{config.port}")
    logger.info(f"🛣️ Endpoint: {config.endpoint_path}")
    logger.info(f"📊 Log Level: {args.log_level}" + (" (DEBUG mode)" if args.debug else ""))
    
    try:
        # Start the server
        server = await start_server(config)
        
        logger.info("✅ Mem0 MCP Server started successfully")
        logger.info(f"🌐 Server available at: http://{config.host}:{config.port}{config.endpoint_path}")
        
        if args.debug:
            logger.debug("🐛 Debug mode enabled - verbose logging active")
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown signal received")
            
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)
        
    finally:
        try:
            logger.info("🛑 Stopping server...")
            await stop_server(server)
            logger.info("✅ Server stopped gracefully")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

if __name__ == "__main__":
    asyncio.run(main())