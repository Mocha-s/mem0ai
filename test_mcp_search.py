#!/usr/bin/env python3
"""测试MCP服务器的搜索响应（支持异步处理）"""

import requests
import json
import time

def test_mcp_search():
    """测试MCP服务器的搜索功能"""
    print("🧪 Testing MCP Server Search (Async)")
    
    # MCP tool call format
    payload = {
        "method": "tools/call",
        "params": {
            "name": "search_memories",
            "arguments": {
                "query": "小红",
                "filters": {"user_id": "root"},
                "top_k": 5,
                "strategy": "semantic"
            }
        }
    }
    
    try:
        print("📤 Sending search request...")
        response = requests.post(
            "http://127.0.0.1:8081/mcp",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"🔄 Response Status: {response.status_code}")
        
        if response.status_code == 202:
            print("⏳ Request accepted, processing asynchronously...")
            # For async processing, we may need to check response headers
            response_text = response.text
            print(f"Response: {response_text}")
            
        elif response.status_code == 200:
            result = response.json()
            print("✅ Immediate Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        return True
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def test_simple_mcp_call():
    """测试简单的MCP调用"""
    print("\n🧪 Testing Simple MCP Call")
    
    payload = {
        "method": "tools/list"
    }
    
    try:
        response = requests.post(
            "http://127.0.0.1:8081/mcp",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("Available tools:")
            tools = result.get("result", {}).get("tools", [])
            for tool in tools:
                print(f"  - {tool.get('name')}: {tool.get('description')}")
            return True
        else:
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing MCP Server Connectivity")
    
    # Test basic connectivity first
    basic_test = test_simple_mcp_call()
    
    if basic_test:
        print("\n" + "="*50)
        # Test search functionality
        search_test = test_mcp_search()
        print(f"\n🎯 Final Result: {'PASS' if search_test else 'FAIL'}")
    else:
        print("\n❌ Basic connectivity test failed")