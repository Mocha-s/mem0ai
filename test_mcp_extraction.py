#!/usr/bin/env python3
"""测试MCP服务器的memories提取逻辑"""

import json
from typing import Dict, Any, List

def extract_memories_from_api_result(api_result: Any) -> List[Dict[str, Any]]:
    """
    Extract memories array from various API response structures.
    
    Handles:
    - Direct array responses
    - Nested results.results structure
    - Dictionary with results key
    """
    memories = []
    
    if isinstance(api_result, dict):
        # Handle nested results structure (results.results)
        if 'results' in api_result and isinstance(api_result['results'], dict):
            if 'results' in api_result['results']:
                memories = api_result['results']['results']
            elif isinstance(api_result['results'], list):
                memories = api_result['results']
        # Handle direct results array in dict
        elif 'results' in api_result and isinstance(api_result['results'], list):
            memories = api_result['results']
        # Handle dictionary response that might be memories itself
        elif isinstance(api_result, list):
            memories = api_result
    elif isinstance(api_result, list):
        memories = api_result
    
    # Ensure memories is always a list
    return memories if isinstance(memories, list) else []

def test_extract_logic():
    print("🧪 Testing MCP memories extraction logic")
    
    # Simulate the actual API response structure  
    api_response = {
        "results": {
            "results": [
                {
                    "id": "mem-1",
                    "memory": "小红是我的好朋友",
                    "score": 0.9,
                    "categories": ["personal", "friends"]
                },
                {
                    "id": "mem-2", 
                    "memory": "小红喜欢打篮球",
                    "score": 0.8,
                    "categories": ["sports", "hobbies"]
                }
            ]
        },
        "total_count": 2,
        "query": "小红",
        "limit": 10
    }
    
    print("🔍 Testing with API response structure:")
    print(json.dumps(api_response, indent=2, ensure_ascii=False))
    
    # Test extraction
    memories = extract_memories_from_api_result(api_response)
    
    print(f"\n📊 Extraction Results:")
    print(f"   Extracted {len(memories)} memories")
    
    for i, memory in enumerate(memories):
        print(f"   Memory {i+1}: {memory.get('memory', 'NO MEMORY')}")
        print(f"     ID: {memory.get('id', 'NO ID')}")  
        print(f"     Categories: {memory.get('categories', 'NO CATEGORIES')}")
        print()
    
    if len(memories) > 0:
        print("✅ Extraction logic works correctly!")
        return True
    else:
        print("❌ Extraction logic failed - no memories extracted")
        return False

if __name__ == "__main__":
    success = test_extract_logic()
    print(f"\n🎯 Result: {'PASS' if success else 'FAIL'}")
