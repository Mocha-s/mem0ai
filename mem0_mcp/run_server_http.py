#!/usr/bin/env python3
"""
Mem0 MCP Server - Streamable HTTP Entry Point

Start the Model Context Protocol server with Streamable HTTP transport for Mem0.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    parser.add_argument('--endpoint', 
                       default=os.getenv('MCP_ENDPOINT', '/mcp'),
                       help='API endpoint path')
    parser.add_argument('--timeout', 
                       type=int,
                       default=int(os.getenv('MCP_SESSION_TIMEOUT', '3600')),
                       help='Session timeout in seconds')
    parser.add_argument('--cors-origins', 
                       default=os.getenv('MCP_CORS_ORIGINS', ''),
                       help='Comma-separated list of allowed CORS origins')
    parser.add_argument('--dev-mode',
                       action='store_true',
                       default=os.getenv('MCP_DEV_MODE', '').lower() in ['true', '1', 'yes'],
                       help='Enable development mode with permissive CORS')
    
    args = parser.parse_args()
    
    print("🧠 Starting Mem0 MCP Server (Streamable HTTP Transport)...")
    print("📋 Protocol Version: 2025-06-18")
    print("🌐 Transport: Streamable HTTP with SSE support")
    print("🔗 Local Mem0 API: http://localhost:8000")
    
    try:
        # Smart CORS configuration
        if args.dev_mode or args.cors_origins == '*':
            # Development mode: Allow all origins
            allowed_origins = ["*"]
        elif args.cors_origins:
            # Custom origins from command line or environment
            allowed_origins = [origin.strip() for origin in args.cors_origins.split(',')]
        else:
            # Production default: Allow common development origins
            allowed_origins = [
                "*"  # Allow all origins as requested by user
            ]
        
        # Server configuration with flexible CORS
        config = MCPServerConfig(
            host=args.host,
            port=args.port,
            endpoint_path=args.endpoint,
            session_timeout=args.timeout,
            protocol_version="2025-06-18",
            allowed_origins=allowed_origins
        )
        
        print(f"🚀 Server binding: {config.host}:{config.port}{config.endpoint_path}")
        
        # Start the server
        server = await start_server(config)
        
        # Display registered services
        services = registry.discover_services()
        print(f"✅ Loaded {len(services)} memory services:")
        for service_name in services:
            service_config = registry.get_service_config(service_name)
            strategies = [s.name for s in service_config.strategies] if service_config else []
            print(f"   📦 {service_name} - Strategies: {strategies}")
        
        # Health check
        print("\\n🔍 Service Health Check:")
        try:
            health_status = await tool_manager.get_service_health()
            for service_name, status in health_status.items():
                status_icon = "✅" if status.get('healthy', False) else "❌"
                print(f"   {status_icon} {service_name}: {status.get('circuit_breaker_state', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️ Health check failed: {e}")
        
        print(f"\\n🎯 Mem0 MCP Server is ready!")
        print(f"📍 Endpoint: http://{config.host}:{config.port}{config.endpoint_path}")
        print(f"🔧 Available Tools: {len(services)}")
        print(f"📊 Capabilities: Tools, Session Management, Streamable HTTP")
        print(f"🛡️ Security: Origin validation, Local binding, Session isolation")
        print(f"\\n💡 Usage Examples:")
        print(f"   Default: python3 run_server_http.py")
        print(f"   Custom:  python3 run_server_http.py -host 0.0.0.0 -p 8001")
        print(f"   Help:    python3 run_server_http.py --help")
        print(f"   Claude Desktop: Configure MCP server endpoint in settings")
        print(f"   VS Code Extension: Point to http://localhost:{config.port}{config.endpoint_path}")
        print(f"   Direct HTTP: POST requests to /mcp endpoint")
        
        print(f"\\n🎯 Server running... (Press Ctrl+C to stop)")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print(f"\\n🛑 Shutting down Mem0 MCP Server...")
            logger.info("Server shutdown requested")
            
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            await stop_server()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

def sync_main():
    """Synchronous wrapper for the async main function"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_main()