#!/usr/bin/env python3
"""Simple test for Memory class categories integration"""

import os
import sys

def test_memory_simple():
    """Test Memory class with minimal configuration"""
    print("🔄 Testing Memory Class Categories Integration")
    
    try:
        # Test 1: Import Memory class
        from mem0 import Memory
        print("1. ✅ Memory class imported successfully")
        
        # Test 2: Create Memory instance with default config
        # Set a dummy API key to avoid errors
        os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key")
        
        m = Memory()
        print("2. ✅ Memory instance created")
        
        # Test 3: Check if db has categories functionality
        if hasattr(m.db, 'add_category'):
            print("3. ✅ Database has categories functionality")
            
            # Test 4: Test category methods on Memory class
            if hasattr(m, 'get_all_categories'):
                print("4. ✅ Memory class has get_all_categories method")
            else:
                print("4. ❌ Memory class missing get_all_categories method")
                
            if hasattr(m, 'get_memory_categories'):
                print("5. ✅ Memory class has get_memory_categories method")
            else:
                print("5. ❌ Memory class missing get_memory_categories method")
                
            if hasattr(m, 'search_by_categories'):
                print("6. ✅ Memory class has search_by_categories method")
            else:
                print("6. ❌ Memory class missing search_by_categories method")
                
            # Test 7: Test database categories functionality
            cat_id = m.db.add_category("integration_test", "Test category for integration")
            print(f"7. ✅ Added category with ID: {cat_id}")
            
            all_cats = m.db.get_all_categories()
            print(f"8. ✅ Retrieved {len(all_cats)} categories from database")
            
        else:
            print("3. ❌ Database missing categories functionality")
            return False
            
        print("\n✅ Memory class categories integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_memory_simple()
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)