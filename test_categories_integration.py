#!/usr/bin/env python3
"""为现有memories添加categories"""

import os
import requests
import json

def add_test_memory_with_categories():
    """添加一个带categories的新memory"""
    print("🧪 Testing memory addition with auto-categorization")
    
    # Add a new memory via API
    payload = {
        "messages": [
            {"role": "user", "content": "我明天打算去健身房锻炼身体，然后晚上和朋友们一起吃火锅。"}
        ],
        "user_id": "test_categories_user"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/memories/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Memory added successfully:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Now search for this memory
            search_payload = {
                "query": "健身房",
                "filters": {"user_id": "test_categories_user"},
                "top_k": 5
            }
            
            search_response = requests.post(
                "http://localhost:8000/v2/memories/search/",
                json=search_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if search_response.status_code == 200:
                search_result = search_response.json()
                print("\n🔍 Search results:")
                memories = search_result.get("results", {}).get("results", [])
                for mem in memories:
                    print(f"Memory: {mem.get('memory')}")
                    print(f"Categories: {mem.get('categories', [])}")
                    print(f"Score: {mem.get('score', 0):.3f}")
                    print()
            
            return True
        else:
            print(f"❌ Failed to add memory: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = add_test_memory_with_categories()
    print(f"\n🎯 Result: {'PASS' if success else 'FAIL'}")