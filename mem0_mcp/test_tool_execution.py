#!/usr/bin/env python3

import asyncio
import json
import httpx
from src.config.settings import MCPConfig
from src.client.mem0_client import Mem0HTTPClient
from src.tools.memory_tools import MemoryToolsExecutor

async def test_tool_execution():
    """Test MCP tool execution without server"""
    
    print("🧪 Testing MCP Tool Execution")
    
    try:
        # Initialize components
        config = MCPConfig()
        executor = MemoryToolsExecutor(config)
        
        # Initialize executor
        await executor.initialize()
        
        print(f"✅ Initialized {len(executor.tools)} tools")
        
        # Test add_memory tool
        arguments = {
            "messages": [
                {"role": "user", "content": "Test memory from direct execution"}
            ],
            "user_id": "test_user"
        }
        
        print("🔧 Testing add_memory tool...")
        response = await executor.execute_tool("add_memory", arguments, "test-1")
        
        result = response.to_dict()
        print(f"📋 Response: {json.dumps(result, indent=2)}")
        
        # Check if it's an error
        if result.get("error"):
            print(f"❌ Tool execution failed: {result['error']}")
        elif result.get("result", {}).get("isError"):
            print(f"❌ Tool returned error: {result['result']['content']}")
        else:
            print("✅ Tool executed successfully")
        
        # Test search_memories tool
        print("🔧 Testing search_memories tool...")
        search_response = await executor.execute_tool("search_memories", {
            "query": "Test memory",
            "user_id": "test_user"
        }, "test-2")
        
        print(f"📋 Search Response: {search_response.to_dict()}")
        
        # Test get_memories tool
        print("🔧 Testing get_memories tool...")
        get_response = await executor.execute_tool("get_memories", {
            "user_id": "test_user"
        }, "test-3")
        
        print(f"📋 Get Response: {get_response.to_dict()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_tool_execution())