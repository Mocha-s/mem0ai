#!/usr/bin/env python3
"""
测试Mem0 API的categories功能
验证添加记忆时是否自动生成categories，搜索时是否返回categories字段
"""

import json
import requests
import uuid
import time
from typing import Dict, List, Any

# API配置
API_BASE_URL = "http://localhost:8000"
MCP_BASE_URL = "http://localhost:8080"

def test_api_health():
    """测试API健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"✅ API Health Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Health Data: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ API Health Check Failed: {e}")
        return False

def test_mcp_health():
    """测试MCP健康状态"""
    try:
        response = requests.get(f"{MCP_BASE_URL}/health")
        print(f"✅ MCP Health Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Health Data: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ MCP Health Check Failed: {e}")
        return False

def add_memory_with_categories_test(user_id: str) -> Dict[str, Any]:
    """测试添加记忆并检查categories"""
    print("\n=== 测试添加记忆功能 ===")
    
    # 测试数据 - 包含不同类型的内容来触发categories生成
    test_messages = [
        {
            "role": "user",
            "content": "我喜欢喝咖啡，特别是拿铁。我每天早上都会喝一杯咖啡来开始我的一天。"
        },
        {
            "role": "assistant", 
            "content": "我知道了，你有喝咖啡的习惯，特别偏爱拿铁，这是你每日早晨的仪式。"
        },
        {
            "role": "user",
            "content": "对的，而且我最喜欢的咖啡店是星巴克，他们的拿铁很香醇。"
        }
    ]
    
    payload = {
        "messages": test_messages,
        "user_id": user_id,
        "metadata": {"test_type": "categories_test", "timestamp": time.time()}
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/v1/memories/", json=payload)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 记忆添加成功")
            print(f"Response Data: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查是否有categories字段
            if isinstance(result, list):
                for i, memory in enumerate(result):
                    if "categories" in memory:
                        print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                    else:
                        print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            elif "categories" in result:
                print(f"✅ 响应包含categories: {result['categories']}")
            else:
                print("⚠️ 响应不包含categories字段")
                
            return result
        else:
            print(f"❌ 记忆添加失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {}

def search_memories_with_categories_test(user_id: str) -> Dict[str, Any]:
    """测试搜索记忆并检查categories"""
    print("\n=== 测试搜索记忆功能 ===")
    
    search_query = "咖啡喜好"
    
    payload = {
        "query": search_query,
        "user_id": user_id
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/v1/memories/search/", json=payload)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 记忆搜索成功")
            print(f"Search Results: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查搜索结果中是否有categories字段
            if isinstance(result, list):
                for i, memory in enumerate(result):
                    if "categories" in memory:
                        print(f"✅ 搜索结果 {i+1} 包含categories: {memory['categories']}")
                    else:
                        print(f"⚠️ 搜索结果 {i+1} 不包含categories字段")
            else:
                print("⚠️ 搜索结果格式不是列表")
                
            return result
        else:
            print(f"❌ 记忆搜索失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {}

def get_all_memories_test(user_id: str) -> Dict[str, Any]:
    """测试获取所有记忆并检查categories"""
    print("\n=== 测试获取所有记忆功能 ===")
    
    try:
        response = requests.get(f"{API_BASE_URL}/v1/memories/?user_id={user_id}&limit=10")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取记忆成功")
            print(f"All Memories: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查获取的记忆中是否有categories字段
            if isinstance(result, list):
                for i, memory in enumerate(result):
                    if "categories" in memory:
                        print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                    else:
                        print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            else:
                print("⚠️ 记忆结果格式不是列表")
                
            return result
        else:
            print(f"❌ 获取记忆失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {}

def test_mcp_add_memory(user_id: str) -> Dict[str, Any]:
    """通过MCP接口测试添加记忆"""
    print("\n=== 测试MCP添加记忆功能 ===")
    
    # MCP请求格式
    mcp_request = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": "add_memory",
            "arguments": {
                "messages": [
                    {
                        "role": "user",
                        "content": "我喜欢阅读科幻小说，最喜欢的作者是刘慈欣。我读过三体系列，觉得非常精彩。"
                    }
                ],
                "user_id": user_id,
                "metadata": {"source": "mcp_test", "timestamp": time.time()}
            }
        }
    }
    
    try:
        response = requests.post(
            f"{MCP_BASE_URL}/mcp",
            json=mcp_request,
            headers={"Content-Type": "application/json"}
        )
        print(f"MCP Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ MCP记忆添加成功")
            print(f"MCP Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查MCP响应中的categories
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            try:
                                text_data = json.loads(item["text"])
                                if isinstance(text_data, list):
                                    for memory in text_data:
                                        if "categories" in memory:
                                            print(f"✅ MCP记忆包含categories: {memory['categories']}")
                                        else:
                                            print(f"⚠️ MCP记忆不包含categories字段")
                            except json.JSONDecodeError:
                                print("⚠️ 无法解析MCP响应文本")
            
            return result
        else:
            print(f"❌ MCP记忆添加失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ MCP请求异常: {e}")
        return {}

def main():
    """主测试函数"""
    print("🚀 开始测试Mem0 categories功能")
    print("=" * 50)
    
    # 生成唯一用户ID用于测试
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    print(f"测试用户ID: {test_user_id}")
    
    # 1. 测试健康状态
    api_healthy = test_api_health()
    mcp_healthy = test_mcp_health()
    
    if not api_healthy:
        print("❌ API服务不可用，退出测试")
        return
    
    # 2. 测试API添加记忆
    add_result = add_memory_with_categories_test(test_user_id)
    
    # 等待一小段时间确保记忆被处理
    time.sleep(2)
    
    # 3. 测试搜索记忆
    search_result = search_memories_with_categories_test(test_user_id)
    
    # 4. 测试获取所有记忆
    all_memories_result = get_all_memories_test(test_user_id)
    
    # 5. 如果MCP可用，测试MCP接口
    if mcp_healthy:
        mcp_result = test_mcp_add_memory(test_user_id)
    
    print("\n" + "=" * 50)
    print("🎯 测试总结:")
    print(f"   API健康状态: {'✅' if api_healthy else '❌'}")
    print(f"   MCP健康状态: {'✅' if mcp_healthy else '❌'}")
    print(f"   添加记忆测试: {'✅' if add_result else '❌'}")
    print(f"   搜索记忆测试: {'✅' if search_result else '❌'}")
    print(f"   获取记忆测试: {'✅' if all_memories_result else '❌'}")
    if mcp_healthy:
        print(f"   MCP添加记忆测试: {'✅' if 'mcp_result' in locals() and mcp_result else '❌'}")

if __name__ == "__main__":
    main()