#!/usr/bin/env python3
"""
調試記憶API的簡化測試腳本
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api_endpoint(method, endpoint, data=None, params=None):
    """測試API端點並返回詳細信息"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, params=params)
        else:
            return {"error": f"Unsupported method: {method}"}
            
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text,
            "json": response.json() if response.content else {}
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    print("🔍 調試記憶API")
    print("=" * 40)
    
    # 1. 測試健康檢查
    print("\n1. 健康檢查:")
    health = test_api_endpoint("GET", "/health")
    print(f"   狀態碼: {health.get('status_code')}")
    print(f"   響應: {health.get('json', {})}")
    
    # 2. 測試記憶創建
    print("\n2. 記憶創建測試:")
    memory_data = {
        "messages": [
            {"role": "user", "content": "這是一個測試記憶"}
        ],
        "user_id": "debug_user_123"
    }
    
    create_result = test_api_endpoint("POST", "/v1/memories/", memory_data)
    print(f"   狀態碼: {create_result.get('status_code')}")
    print(f"   響應內容: {create_result.get('content')}")
    print(f"   JSON響應: {create_result.get('json', {})}")
    
    # 3. 測試記憶獲取
    print("\n3. 記憶獲取測試:")
    get_result = test_api_endpoint("GET", "/v1/memories/", params={"user_id": "debug_user_123"})
    print(f"   狀態碼: {get_result.get('status_code')}")
    print(f"   響應內容: {get_result.get('content')}")
    print(f"   JSON響應: {get_result.get('json', {})}")
    
    # 4. 測試搜索
    print("\n4. 記憶搜索測試:")
    search_data = {
        "query": "測試",
        "user_id": "debug_user_123"
    }
    
    search_result = test_api_endpoint("POST", "/v1/memories/search/", search_data)
    print(f"   狀態碼: {search_result.get('status_code')}")
    print(f"   響應內容: {search_result.get('content')}")
    print(f"   JSON響應: {search_result.get('json', {})}")
    
    # 5. 測試配置端點
    print("\n5. 配置測試:")
    config_data = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": "localhost",
                "port": 6333
            }
        }
    }
    
    config_result = test_api_endpoint("POST", "/configure", config_data)
    print(f"   狀態碼: {config_result.get('status_code')}")
    print(f"   響應內容: {config_result.get('content')}")
    
    # 6. 重新測試記憶創建
    print("\n6. 重新測試記憶創建:")
    memory_data2 = {
        "messages": [
            {"role": "user", "content": "配置後的測試記憶"}
        ],
        "user_id": "debug_user_456"
    }
    
    create_result2 = test_api_endpoint("POST", "/v1/memories/", memory_data2)
    print(f"   狀態碼: {create_result2.get('status_code')}")
    print(f"   響應內容: {create_result2.get('content')}")
    print(f"   JSON響應: {create_result2.get('json', {})}")

if __name__ == "__main__":
    main()
