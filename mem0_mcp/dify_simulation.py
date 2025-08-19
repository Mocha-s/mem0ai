#!/usr/bin/env python3
"""
Dify Client Simulation Test
Tests MCP server with Dify-like client behavior patterns
"""

import asyncio
import aiohttp
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dify_client_pattern():
    """Simulate Dify client connection and usage patterns"""
    
    server_url = "http://localhost:8080/mcp"
    
    # Use headers similar to Dify's python-httpx client
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'MCP-Protocol-Version': '2025-06-18',
        'User-Agent': 'python-httpx/0.27.2'  # Match Dify's user agent
    }
    
    session_id = None
    
    async with aiohttp.ClientSession() as session:
        try:
            print("🎭 Simulating Dify Client Behavior...")
            
            # Step 1: Initialize (like Dify does)
            print("\n1️⃣ Initialize (Dify style)...")
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {
                        "roots": {"listChanged": False},
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "Dify v1.7.2",
                        "version": "1.7.2"
                    }
                }
            }
            
            async with session.post(server_url, json=init_payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    session_id = resp.headers.get('Mcp-Session-Id')
                    if session_id:
                        headers['Mcp-Session-Id'] = session_id
                    print(f"   ✅ Initialize successful, session: {session_id}")
                else:
                    print(f"   ❌ Initialize failed: {resp.status}")
                    return False
            
            # Step 2: Get tools/list (to get manifest)
            print("\n2️⃣ Get manifest (tools/list)...")
            tools_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            async with session.post(server_url, json=tools_payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    tools = result.get('result', {}).get('tools', [])
                    print(f"   ✅ Got manifest with {len(tools)} tools")
                else:
                    text = await resp.text()
                    print(f"   ❌ Manifest failed: {resp.status} - {text}")
                    return False
            
            # Step 3: Try various tool calls (what Dify might do)
            print("\n3️⃣ Testing various tool calls...")
            
            # Test different tools that Dify might call
            test_calls = [
                {
                    "name": "search_memories",
                    "arguments": {"query": "test", "user_id": "dify_user"}
                },
                {
                    "name": "add_memory", 
                    "arguments": {
                        "messages": [{"role": "user", "content": "This is a test memory"}],
                        "user_id": "dify_user"
                    }
                }
            ]
            
            for i, test_call in enumerate(test_calls, 3):
                print(f"\n   {i}️⃣ Testing {test_call['name']}...")
                
                call_payload = {
                    "jsonrpc": "2.0",
                    "id": i,
                    "method": "tools/call",
                    "params": test_call
                }
                
                async with session.post(server_url, json=call_payload, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if 'error' in result:
                            print(f"      ⚠️  Tool returned error: {result['error']['message']}")
                        else:
                            print(f"      ✅ {test_call['name']} successful")
                    else:
                        text = await resp.text()
                        print(f"      ❌ {test_call['name']} failed: {resp.status} - {text}")
                        if resp.status >= 500:
                            print(f"      💥 This is likely the Internal Server Error Dify sees!")
                            return False
            
            # Step 4: Proper session termination (like Dify)
            print("\n4️⃣ Session termination...")
            terminate_headers = headers.copy()
            
            async with session.delete(server_url, headers=terminate_headers) as resp:
                if resp.status == 200:
                    print(f"   ✅ Session terminated successfully")
                else:
                    print(f"   ⚠️  Termination returned: {resp.status}")
            
            return True
            
        except Exception as e:
            print(f"❌ Dify simulation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main test runner"""
    print("🎭 Dify Client Simulation Test")
    print("=" * 50)
    
    success = await test_dify_client_pattern()
    
    print(f"\n🎯 Dify Simulation Result:")
    if success:
        print("   ✅ All Dify-like operations successful")
        print("   🤔 If Dify still reports errors, check:")
        print("      - Dify's internal caching/retry logic")
        print("      - Network connectivity between Dify and MCP server")
        print("      - Dify's timeout configuration")
    else:
        print("   ❌ Found issues that explain Dify's Internal Server Error")
        print("   🔧 Need to fix these issues for Dify compatibility")

if __name__ == "__main__":
    asyncio.run(main())