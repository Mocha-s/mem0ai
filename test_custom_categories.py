#!/usr/bin/env python3
"""
测试Mem0 API的custom_categories功能
验证使用custom_categories参数时记忆是否包含categories字段
"""

import json
import requests
import uuid
import time
from typing import Dict, List, Any

# API配置
API_BASE_URL = "http://localhost:8000"

def test_add_memory_with_custom_categories(user_id: str) -> Dict[str, Any]:
    """测试使用custom_categories参数添加记忆"""
    print("\n=== 测试使用custom_categories参数添加记忆 ===")
    
    # 测试数据
    test_messages = [
        {
            "role": "user",
            "content": "我是一名软件工程师，主要使用Python开发Web应用。我最喜欢的框架是FastAPI。"
        },
        {
            "role": "assistant", 
            "content": "很好，你是Python开发者，专注于Web应用开发，偏爱FastAPI框架。"
        }
    ]
    
    # 自定义categories
    custom_categories = [
        {"职业信息": "用户的工作、职位、技能相关信息"},
        {"技术偏好": "用户喜欢的编程语言、框架、工具等"},
        {"工作技能": "用户的专业技能和能力"}
    ]
    
    payload = {
        "messages": test_messages,
        "user_id": user_id,
        "custom_categories": custom_categories,
        "metadata": {"test_type": "custom_categories_test", "timestamp": time.time()}
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/v1/memories/", json=payload)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 记忆添加成功")
            print(f"Response Data: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查是否有categories字段
            has_categories = False
            if isinstance(result, list):
                for i, memory in enumerate(result):
                    if "categories" in memory:
                        print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                        has_categories = True
                    else:
                        print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            elif "categories" in result:
                print(f"✅ 响应包含categories: {result['categories']}")
                has_categories = True
            else:
                print("⚠️ 响应不包含categories字段")
            
            if not has_categories:
                print("💡 提示：尝试使用output_format参数")
                
            return result
        else:
            print(f"❌ 记忆添加失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {}

def test_add_memory_with_output_format(user_id: str) -> Dict[str, Any]:
    """测试使用output_format=v1.1参数添加记忆"""
    print("\n=== 测试使用output_format=v1.1参数添加记忆 ===")
    
    # 测试数据
    test_messages = [
        {
            "role": "user",
            "content": "我喜欢旅行，去过日本、韩国和泰国。最喜欢的城市是东京，那里的食物和文化都很棒。"
        }
    ]
    
    # 自定义categories  
    custom_categories = [
        {"旅行经历": "用户的旅行历史和经验"},
        {"地点偏好": "用户喜欢的城市、国家或地区"},
        {"文化兴趣": "用户对不同文化的兴趣和体验"}
    ]
    
    payload = {
        "messages": test_messages,
        "user_id": user_id,
        "custom_categories": custom_categories,
        "output_format": "v1.1",
        "metadata": {"test_type": "output_format_test", "timestamp": time.time()}
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/v1/memories/", json=payload)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 记忆添加成功")
            print(f"Response Data: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查v1.1格式的响应结构
            if "results" in result:
                print("✅ 发现v1.1格式的results字段")
                results = result["results"]
                if isinstance(results, list):
                    for i, memory in enumerate(results):
                        if "categories" in memory:
                            print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                        else:
                            print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            
            if "relations" in result:
                print(f"✅ 发现v1.1格式的relations字段: {result['relations']}")
                
            return result
        else:
            print(f"❌ 记忆添加失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {}

def test_search_with_output_format(user_id: str) -> Dict[str, Any]:
    """测试使用output_format=v1.1参数搜索记忆"""
    print("\n=== 测试使用output_format=v1.1参数搜索记忆 ===")
    
    search_query = "旅行喜好"
    
    payload = {
        "query": search_query,
        "user_id": user_id,
        "output_format": "v1.1"
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/v1/memories/search/", json=payload)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 记忆搜索成功")
            print(f"Search Results: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查v1.1格式的搜索结果
            if "results" in result:
                print("✅ 发现v1.1格式的results字段")
                results = result["results"]
                if isinstance(results, list):
                    for i, memory in enumerate(results):
                        if "categories" in memory:
                            print(f"✅ 搜索结果 {i+1} 包含categories: {memory['categories']}")
                        else:
                            print(f"⚠️ 搜索结果 {i+1} 不包含categories字段")
            else:
                # 检查直接返回的列表格式
                if isinstance(result, list):
                    for i, memory in enumerate(result):
                        if "categories" in memory:
                            print(f"✅ 搜索结果 {i+1} 包含categories: {memory['categories']}")
                        else:
                            print(f"⚠️ 搜索结果 {i+1} 不包含categories字段")
                
            return result
        else:
            print(f"❌ 记忆搜索失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {}

def main():
    """主测试函数"""
    print("🚀 开始测试Mem0 custom_categories功能")
    print("=" * 60)
    
    # 生成唯一用户ID用于测试
    test_user_id = f"test_categories_{uuid.uuid4().hex[:8]}"
    print(f"测试用户ID: {test_user_id}")
    
    # 1. 测试使用custom_categories参数
    result1 = test_add_memory_with_custom_categories(test_user_id)
    
    # 等待一小段时间确保记忆被处理
    time.sleep(2)
    
    # 2. 测试使用output_format=v1.1参数
    result2 = test_add_memory_with_output_format(test_user_id)
    
    # 等待一小段时间确保记忆被处理
    time.sleep(2)
    
    # 3. 测试搜索时使用output_format=v1.1
    result3 = test_search_with_output_format(test_user_id)
    
    print("\n" + "=" * 60)
    print("🎯 测试总结:")
    print(f"   使用custom_categories添加记忆: {'✅' if result1 else '❌'}")
    print(f"   使用output_format=v1.1添加记忆: {'✅' if result2 else '❌'}")
    print(f"   使用output_format=v1.1搜索记忆: {'✅' if result3 else '❌'}")
    
    # 分析结果
    print("\n📊 分析结果:")
    if not any([result1, result2, result3]):
        print("❌ 所有测试都失败了")
    else:
        categories_found = False
        for i, result in enumerate([result1, result2, result3], 1):
            if result:
                # 检查结果中是否包含categories
                if _has_categories_in_result(result):
                    categories_found = True
                    print(f"✅ 测试 {i} 发现了categories字段")
                else:
                    print(f"⚠️ 测试 {i} 未发现categories字段")
        
        if not categories_found:
            print("\n❌ 结论：当前配置下，Mem0服务器没有返回categories字段")
            print("💡 可能的原因：")
            print("   1. categories功能需要特殊配置")
            print("   2. categories功能仅在Mem0 Cloud中可用")
            print("   3. 需要不同的API版本或参数")
        else:
            print("\n✅ 结论：categories功能部分可用")

def _has_categories_in_result(result: Any) -> bool:
    """检查结果中是否包含categories字段"""
    if isinstance(result, dict):
        if "categories" in result:
            return True
        if "results" in result:
            return _has_categories_in_result(result["results"])
    elif isinstance(result, list):
        return any(_has_categories_in_result(item) for item in result)
    return False

if __name__ == "__main__":
    main()