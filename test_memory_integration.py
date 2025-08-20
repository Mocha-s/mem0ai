#!/usr/bin/env python3
"""Test Memory class integration without LLM dependency"""

import os
import tempfile
from mem0 import Memory

def test_memory_integration():
    """Test Memory class with categories but without LLM calls"""
    print("🔄 Testing Memory Class Integration")
    
    # Create Memory instance with basic config (no LLM)
    config = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "test_memories",
                "path": "/tmp/test_chroma"
            }
        },
        # No LLM config to avoid API calls
    }
    
    try:
        m = Memory(config=config)
        
        print("1. Memory instance created")
        
        # Reset to start clean
        m.reset()
        print("2. Memory reset")
        
        # Test if db has categories functionality
        if hasattr(m.db, 'add_category'):
            print("3. ✅ Categories functionality detected in Memory.db")
            
            # Test direct database operations
            cat_id = m.db.add_category("test_integration", "Integration test category")
            print(f"4. ✅ Added category with ID: {cat_id}")
            
            # Test memory-category assignment
            m.db.assign_memory_categories("test-mem-456", ["test_integration", "manual"])
            print("5. ✅ Assigned categories to memory")
            
            # Test category retrieval
            categories = m.db.get_memory_categories("test-mem-456")
            print(f"6. ✅ Retrieved categories: {categories}")
            
            # Test get all categories
            all_cats = m.db.get_all_categories()
            print(f"7. ✅ Found {len(all_cats)} categories")
            
            # Test category methods on Memory class
            if hasattr(m, 'get_all_categories'):
                memory_cats = m.get_all_categories()
                print(f"8. ✅ Memory.get_all_categories() returned {len(memory_cats)} categories")
            else:
                print("8. ❌ Memory.get_all_categories() method not found")
                
            if hasattr(m, 'get_memory_categories'):
                mem_cats = m.get_memory_categories("test-mem-456")
                print(f"9. ✅ Memory.get_memory_categories() returned: {mem_cats}")
            else:
                print("9. ❌ Memory.get_memory_categories() method not found")
            
        else:
            print("3. ❌ Categories functionality not found in Memory.db")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_memory_integration()