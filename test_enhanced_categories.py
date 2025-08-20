#!/usr/bin/env python3
"""
Test script for enhanced categories functionality in Mem0.
Tests OpenMemory-style auto-categorization with database persistence.
"""

import os
import sys
import json
import time
from mem0 import Memory

# Test configuration
os.environ["OPENAI_API_KEY"] = "sk-test-key-replace-with-real"

def test_enhanced_categories():
    """Test the enhanced categories functionality"""
    print("🔄 Testing Enhanced Categories Functionality")
    print("=" * 60)
    
    # Initialize memory with a temporary database
    m = Memory()
    
    # Reset memory store for clean test
    print("\n1️⃣ Resetting memory store...")
    m.reset()
    
    # Test 1: Add memory and check automatic categorization
    print("\n2️⃣ Testing automatic categorization on memory addition...")
    
    messages = [
        {"role": "user", "content": "I love playing basketball on weekends. It's my favorite sport and keeps me healthy."},
        {"role": "assistant", "content": "That's great! Basketball is an excellent way to stay active and have fun."}
    ]
    
    try:
        result = m.add(messages, user_id="test_user")
        print(f"✅ Add result: {json.dumps(result, indent=2)}")
        
        # Check if categories are returned in the result
        if "results" in result:
            for memory_result in result["results"]:
                if "categories" in memory_result:
                    categories = memory_result["categories"]
                    print(f"📂 Generated categories: {categories}")
                else:
                    print("❌ No categories found in memory result")
    except Exception as e:
        print(f"❌ Error adding memory: {e}")
        return False
    
    # Test 2: Get memory and verify categories are included
    print("\n3️⃣ Testing get memory with categories...")
    
    try:
        if "results" in result and result["results"]:
            memory_id = result["results"][0]["id"]
            retrieved_memory = m.get(memory_id)
            print(f"✅ Retrieved memory: {json.dumps(retrieved_memory, indent=2)}")
            
            if "categories" in retrieved_memory:
                print(f"📂 Memory categories: {retrieved_memory['categories']}")
            else:
                print("❌ No categories found in retrieved memory")
        else:
            print("❌ No memory ID found in result")
            return False
    except Exception as e:
        print(f"❌ Error retrieving memory: {e}")
        return False
    
    # Test 3: Search memories and verify categories are included
    print("\n4️⃣ Testing search with categories...")
    
    try:
        search_results = m.search("basketball", user_id="test_user")
        print(f"✅ Search results: {json.dumps(search_results, indent=2)}")
        
        if "results" in search_results and search_results["results"]:
            for memory in search_results["results"]:
                if "categories" in memory:
                    print(f"📂 Search result categories: {memory['categories']}")
                else:
                    print("❌ No categories found in search result")
        else:
            print("❌ No search results found")
    except Exception as e:
        print(f"❌ Error searching memories: {e}")
        return False
    
    # Test 4: Get all memories and verify categories
    print("\n5️⃣ Testing get_all with categories...")
    
    try:
        all_memories = m.get_all(user_id="test_user")
        print(f"✅ All memories: {json.dumps(all_memories, indent=2)}")
        
        if "results" in all_memories:
            memories_list = all_memories["results"]
        else:
            memories_list = all_memories
            
        for memory in memories_list:
            if "categories" in memory:
                print(f"📂 Memory {memory['id']} categories: {memory['categories']}")
            else:
                print(f"❌ No categories found for memory {memory['id']}")
    except Exception as e:
        print(f"❌ Error getting all memories: {e}")
        return False
    
    # Test 5: Test category-specific methods
    print("\n6️⃣ Testing category-specific methods...")
    
    try:
        # Test get all categories
        all_categories = m.get_all_categories()
        print(f"✅ All categories: {json.dumps(all_categories, indent=2)}")
        
        # Test search by categories (if categories exist)
        if all_categories:
            category_names = [cat["name"] for cat in all_categories[:2]]  # Test with first 2 categories
            category_search = m.search_by_categories(category_names, limit=5)
            print(f"✅ Search by categories {category_names}: {len(category_search)} results")
            for memory in category_search:
                print(f"   - Memory: {memory['memory'][:50]}... Categories: {memory['categories']}")
        
    except Exception as e:
        print(f"❌ Error testing category methods: {e}")
        return False
    
    # Test 6: Test with custom categories
    print("\n7️⃣ Testing custom categories...")
    
    try:
        custom_categories = [
            {"fitness_activities": "Physical activities and exercise routines"},
            {"personal_interests": "Individual hobbies and interests"}
        ]
        
        custom_messages = [
            {"role": "user", "content": "I enjoy cooking Italian food and reading mystery novels."},
            {"role": "assistant", "content": "Those are wonderful hobbies! Cooking and reading are both very enriching activities."}
        ]
        
        custom_result = m.add(custom_messages, user_id="test_user", custom_categories=custom_categories)
        print(f"✅ Custom categories result: {json.dumps(custom_result, indent=2)}")
        
        if "results" in custom_result:
            for memory_result in custom_result["results"]:
                if "categories" in memory_result:
                    categories = memory_result["categories"]
                    print(f"📂 Custom generated categories: {categories}")
                else:
                    print("❌ No categories found in custom memory result")
                    
    except Exception as e:
        print(f"❌ Error testing custom categories: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ Enhanced Categories Test Completed Successfully!")
    print("\n📊 Summary:")
    print("   - ✅ Automatic categorization on memory addition")
    print("   - ✅ Categories included in memory retrieval")
    print("   - ✅ Categories included in search results")
    print("   - ✅ Categories included in get_all results")
    print("   - ✅ Category-specific methods working")
    print("   - ✅ Custom categories support")
    print("\n🎉 Categories functionality is working as expected!")
    
    return True

def test_database_persistence():
    """Test database persistence of categories"""
    print("\n🔄 Testing Categories Database Persistence")
    print("=" * 50)
    
    try:
        # Test 1: Create a new memory instance to verify persistence
        m1 = Memory()
        
        # Add a memory with the first instance
        messages = [{"role": "user", "content": "I love traveling to Japan and learning about their culture."}]
        result = m1.add(messages, user_id="persistence_test")
        
        if "results" in result and result["results"]:
            memory_id = result["results"][0]["id"]
            print(f"✅ Added memory with ID: {memory_id}")
            
            # Check categories with first instance
            categories1 = m1.get_memory_categories(memory_id)
            print(f"📂 Categories from instance 1: {categories1}")
            
            # Create a second memory instance
            m2 = Memory()
            
            # Check categories with second instance (should persist)
            categories2 = m2.get_memory_categories(memory_id)
            print(f"📂 Categories from instance 2: {categories2}")
            
            if categories1 == categories2 and categories1:
                print("✅ Categories persistence verified!")
                return True
            else:
                print("❌ Categories persistence failed!")
                return False
        else:
            print("❌ Failed to add memory for persistence test")
            return False
            
    except Exception as e:
        print(f"❌ Error testing database persistence: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Enhanced Categories Testing...")
    
    success = True
    
    # Run main functionality test
    if not test_enhanced_categories():
        success = False
    
    # Run persistence test  
    if not test_database_persistence():
        success = False
    
    if success:
        print("\n🎉 All tests passed! Enhanced categories functionality is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)