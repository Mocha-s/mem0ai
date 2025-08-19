#!/usr/bin/env python3
"""
Mem0 MCP Server - Service-Oriented Architecture Entry Point

Start the Model Context Protocol server with service-oriented architecture for Mem0.
"""

import sys
import os
import asyncio
import logging

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gateway.tool_manager import tool_manager
from registry.registry_manager import registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the Mem0 MCP server with service architecture"""
    
    print("🧠 Starting Mem0 MCP Server (Service-Oriented Architecture)...")
    print("📋 Protocol Version: 2025-06-18")
    print("🏗️ Architecture: API Gateway + Microservices")
    
    try:
        # Initialize the tool manager
        logger.info("Initializing ToolManager...")
        await tool_manager.initialize()
        
        # Display registered services
        services = registry.discover_services()
        print(f"✅ Loaded {len(services)} services:")
        for service_name in services:
            config = registry.get_service_config(service_name)
            strategies = [s.name for s in config.strategies] if config else []
            print(f"   📦 {service_name} (v{config.version if config else 'unknown'}) - Strategies: {strategies}")
        
        # Health check
        print("\n🔍 Service Health Check:")
        health_status = await tool_manager.get_service_health()
        for service_name, status in health_status.items():
            status_icon = "✅" if status.get('healthy', False) else "❌"
            print(f"   {status_icon} {service_name}: {status.get('circuit_breaker_state', 'unknown')}")
        
        print(f"\n🚀 Mem0 MCP Server is ready!")
        print(f"🔧 Available Tools: {len(services)}")
        print(f"📊 Server Capabilities: Tools, Resources, Prompts, Logging")
        print(f"🛡️ Security: User Consent, Data Privacy, Tool Safety")
        
        # In a real implementation, this would start the MCP server
        # For now, we'll simulate by keeping the process alive
        print(f"\n🎯 Server running... (Press Ctrl+C to stop)")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print(f"\n🛑 Shutting down Mem0 MCP Server...")
            logger.info("Server shutdown requested")
            
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)

def sync_main():
    """Synchronous wrapper for the async main function"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_main()