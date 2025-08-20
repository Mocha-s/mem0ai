#!/usr/bin/env python3
"""
测试Mem0 API的自动categories生成功能
验证当不提供custom_categories时，系统是否自动生成categories
"""

import json
import requests
import uuid
import time
from typing import Dict, List, Any

# API配置
API_BASE_URL = "http://localhost:8000"

def test_auto_categories_generation(user_id: str) -> Dict[str, Any]:
    """测试自动categories生成（不提供custom_categories参数）"""
    print("\n=== 测试自动categories生成功能 ===")
    
    # 测试数据 - 包含多种类型内容来触发不同categories
    test_messages = [
        {
            "role": "user",
            "content": "我是一名机器学习工程师，专注于深度学习和自然语言处理。我最喜欢的编程语言是Python，常用的框架包括TensorFlow和PyTorch。"
        },
        {
            "role": "assistant", 
            "content": "了解了，你是ML工程师，专攻深度学习和NLP，偏爱Python，使用TensorFlow和PyTorch框架。"
        },
        {
            "role": "user",
            "content": "我还喜欢阅读科技书籍，特别是AI相关的。最近在读《深度学习》这本书，觉得很有启发。"
        }
    ]
    
    # 不提供custom_categories参数，测试自动生成
    payload = {
        "messages": test_messages,
        "user_id": user_id,
        "metadata": {"test_type": "auto_categories_test", "timestamp": time.time()}
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/v1/memories/", json=payload)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 记忆添加成功")
            print(f"Response Data: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查是否有categories字段
            categories_found = False
            if isinstance(result, list):
                for i, memory in enumerate(result):
                    if "categories" in memory:
                        print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                        categories_found = True
                    else:
                        print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            elif "categories" in result:
                print(f"✅ 响应包含categories: {result['categories']}")
                categories_found = True
            else:
                print("⚠️ 响应不包含categories字段")
            
            return {"result": result, "categories_found": categories_found}
        else:
            print(f"❌ 记忆添加失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {"result": {}, "categories_found": False}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {"result": {}, "categories_found": False}

def test_auto_categories_with_v11_format(user_id: str) -> Dict[str, Any]:
    """测试使用v1.1格式的自动categories生成"""
    print("\n=== 测试v1.1格式的自动categories生成功能 ===")
    
    # 测试数据
    test_messages = [
        {
            "role": "user",
            "content": "我是一个健身爱好者，每周去健身房3次。我最喜欢的运动是举重和游泳，这让我保持良好的身体状态。"
        },
        {
            "role": "assistant", 
            "content": "很好，你坚持健身，每周3次，喜欢举重和游泳，注重身体健康。"
        }
    ]
    
    # 使用v1.1格式但不提供custom_categories
    payload = {
        "messages": test_messages,
        "user_id": user_id,
        "output_format": "v1.1",
        "metadata": {"test_type": "auto_categories_v11_test", "timestamp": time.time()}
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/v1/memories/", json=payload)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 记忆添加成功")
            print(f"Response Data: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查v1.1格式的响应结构
            categories_found = False
            if "results" in result:
                print("✅ 发现v1.1格式的results字段")
                results = result["results"]
                if isinstance(results, list):
                    for i, memory in enumerate(results):
                        if "categories" in memory:
                            print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                            categories_found = True
                        else:
                            print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            
            if "relations" in result:
                print(f"✅ 发现v1.1格式的relations字段: {result['relations']}")
            
            return {"result": result, "categories_found": categories_found}
        else:
            print(f"❌ 记忆添加失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {"result": {}, "categories_found": False}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {"result": {}, "categories_found": False}

def test_search_auto_categories(user_id: str) -> Dict[str, Any]:
    """测试搜索时是否返回自动生成的categories"""
    print("\n=== 测试搜索自动生成的categories ===")
    
    search_query = "工程师技能"
    
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
            
            # 检查搜索结果中的categories
            categories_found = False
            if "results" in result:
                results = result["results"]
                if isinstance(results, list):
                    for i, memory in enumerate(results):
                        if "categories" in memory:
                            print(f"✅ 搜索结果 {i+1} 包含categories: {memory['categories']}")
                            categories_found = True
                        else:
                            print(f"⚠️ 搜索结果 {i+1} 不包含categories字段")
            
            return {"result": result, "categories_found": categories_found}
        else:
            print(f"❌ 记忆搜索失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {"result": {}, "categories_found": False}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {"result": {}, "categories_found": False}

def test_get_all_auto_categories(user_id: str) -> Dict[str, Any]:
    """测试获取所有记忆时是否包含自动生成的categories"""
    print("\n=== 测试获取所有记忆的categories ===")
    
    try:
        response = requests.get(f"{API_BASE_URL}/v1/memories/?user_id={user_id}&limit=20&output_format=v1.1")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取记忆成功")
            print(f"All Memories: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查获取的记忆中的categories
            categories_found = False
            if "results" in result:
                results = result["results"]
                if isinstance(results, list):
                    for i, memory in enumerate(results):
                        if "categories" in memory:
                            print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                            categories_found = True
                        else:
                            print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            elif isinstance(result, list):
                for i, memory in enumerate(result):
                    if "categories" in memory:
                        print(f"✅ 记忆 {i+1} 包含categories: {memory['categories']}")
                        categories_found = True
                    else:
                        print(f"⚠️ 记忆 {i+1} 不包含categories字段")
            
            return {"result": result, "categories_found": categories_found}
        else:
            print(f"❌ 获取记忆失败: {response.status_code}")
            print(f"Error: {response.text}")
            return {"result": {}, "categories_found": False}
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {"result": {}, "categories_found": False}

def main():
    """主测试函数"""
    print("🚀 开始测试Mem0自动categories生成功能")
    print("=" * 70)
    
    # 生成唯一用户ID用于测试
    test_user_id = f"test_auto_categories_{uuid.uuid4().hex[:8]}"
    print(f"测试用户ID: {test_user_id}")
    
    # 1. 测试基本的自动categories生成
    result1 = test_auto_categories_generation(test_user_id)
    
    # 等待一小段时间确保记忆被处理
    time.sleep(2)
    
    # 2. 测试v1.1格式的自动categories生成
    result2 = test_auto_categories_with_v11_format(test_user_id)
    
    # 等待一小段时间确保记忆被处理
    time.sleep(2)
    
    # 3. 测试搜索时的categories
    result3 = test_search_auto_categories(test_user_id)
    
    # 4. 测试获取所有记忆时的categories
    result4 = test_get_all_auto_categories(test_user_id)
    
    print("\n" + "=" * 70)
    print("🎯 测试总结:")
    print(f"   基本自动categories测试: {'✅' if result1['result'] else '❌'}")
    print(f"   v1.1格式自动categories测试: {'✅' if result2['result'] else '❌'}")
    print(f"   搜索categories测试: {'✅' if result3['result'] else '❌'}")
    print(f"   获取所有记忆categories测试: {'✅' if result4['result'] else '❌'}")
    
    # 分析结果
    print("\n📊 Categories功能分析:")
    categories_tests = [result1, result2, result3, result4]
    any_categories_found = any(test.get('categories_found', False) for test in categories_tests)
    
    if any_categories_found:
        print("✅ 发现了categories字段！")
        for i, test in enumerate(categories_tests, 1):
            if test.get('categories_found', False):
                print(f"   测试 {i} 成功发现categories")
    else:
        print("❌ 所有测试都未发现categories字段")
        print("\n💡 可能的解决方案:")
        print("   1. 检查Mem0版本是否支持categories功能")
        print("   2. 查看是否需要特殊的配置或环境变量")
        print("   3. 检查是否需要使用Mem0 Cloud API而非本地实例")
        print("   4. 查看mem0/configs/prompts.py中的FACT_RETRIEVAL_PROMPT是否包含categories相关指令")
        
    print(f"\n🔍 总体结论:")
    if any_categories_found:
        print("✅ Mem0 categories功能在当前环境中可用")
    else:
        print("❌ Mem0 categories功能在当前环境中不可用或需要额外配置")

if __name__ == "__main__":
    main()