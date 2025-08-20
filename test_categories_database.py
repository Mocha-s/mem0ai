#!/usr/bin/env python3
"""
Test script for categories database functionality - no LLM required.
Tests the database schema and storage capabilities.
"""

import sys
import sqlite3
import tempfile
import os
from mem0.memory.storage import SQLiteManager

def test_categories_database():
    """Test categories database functionality"""
    print("🔄 Testing Categories Database Schema")
    print("=" * 50)
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        # Initialize SQLiteManager with the temporary database
        db = SQLiteManager(db_path)
        
        # Test 1: Check if tables were created
        print("\n1️⃣ Testing table creation...")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if categories table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
        if cursor.fetchone():
            print("✅ Categories table created successfully")
        else:
            print("❌ Categories table not found")
            return False
            
        # Check if memory_categories table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_categories'")
        if cursor.fetchone():
            print("✅ Memory_categories table created successfully")
        else:
            print("❌ Memory_categories table not found")
            return False
            
        # Test 2: Test adding categories
        print("\n2️⃣ Testing category addition...")
        
        category_id = db.add_category("sports", "Sports and physical activities")
        print(f"✅ Added category with ID: {category_id}")
        
        # Test duplicate category handling
        duplicate_id = db.add_category("sports", "Duplicate sports category")
        if duplicate_id == category_id:
            print("✅ Duplicate category handling works correctly")
        else:
            print("❌ Duplicate category handling failed")
            return False
            
        # Test 3: Test memory-category assignment
        print("\n3️⃣ Testing memory-category assignment...")
        
        memory_id = "test-memory-123"
        categories = ["sports", "health", "personal"]
        
        db.assign_memory_categories(memory_id, categories)
        print(f"✅ Assigned categories {categories} to memory {memory_id}")
        
        # Verify the assignment
        retrieved_categories = db.get_memory_categories(memory_id)
        if set(retrieved_categories) == set(categories):
            print(f"✅ Retrieved categories match: {retrieved_categories}")
        else:
            print(f"❌ Retrieved categories don't match. Expected: {categories}, Got: {retrieved_categories}")
            return False
            
        # Test 4: Test getting all categories
        print("\n4️⃣ Testing get all categories...")
        
        all_categories = db.get_all_categories()
        print(f"✅ Retrieved {len(all_categories)} categories:")
        for cat in all_categories:
            print(f"   - {cat['name']}: {cat['description']} (used {cat['usage_count']} times)")
            
        # Test 5: Test memory search by categories
        print("\n5️⃣ Testing memory search by categories...")
        
        # Add another memory with some overlapping categories
        memory_id_2 = "test-memory-456"
        db.assign_memory_categories(memory_id_2, ["sports", "entertainment"])
        
        # Search for memories with 'sports' category
        sports_memories = db.get_memories_by_categories(["sports"])
        if memory_id in sports_memories and memory_id_2 in sports_memories:
            print(f"✅ Found {len(sports_memories)} memories with 'sports' category")
        else:
            print(f"❌ Memory search by categories failed. Found: {sports_memories}")
            return False
            
        # Test 6: Test category deletion
        print("\n6️⃣ Testing category deletion...")
        
        db.delete_memory_categories(memory_id)
        remaining_categories = db.get_memory_categories(memory_id)
        if len(remaining_categories) == 0:
            print("✅ Memory categories deleted successfully")
        else:
            print(f"❌ Category deletion failed. Remaining: {remaining_categories}")
            return False
            
        # Test 7: Test database integrity
        print("\n7️⃣ Testing database integrity...")
        
        # Check foreign key constraints and indexes
        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()
        if len(fk_errors) == 0:
            print("✅ Foreign key constraints are intact")
        else:
            print(f"❌ Foreign key constraint violations: {fk_errors}")
            return False
            
        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = cursor.fetchall()
        expected_indexes = {'idx_memory_categories_memory', 'idx_memory_categories_category', 'idx_categories_name'}
        found_indexes = {idx[0] for idx in indexes}
        
        if expected_indexes.issubset(found_indexes):
            print(f"✅ All expected indexes found: {list(expected_indexes)}")
        else:
            missing = expected_indexes - found_indexes
            print(f"❌ Missing indexes: {list(missing)}")
            return False
            
        conn.close()
        db.close()
        
        print("\n" + "="*50)
        print("✅ Categories Database Test Completed Successfully!")
        print("\n📊 Summary:")
        print("   - ✅ Database tables created correctly")
        print("   - ✅ Category addition and deduplication")
        print("   - ✅ Memory-category assignment")
        print("   - ✅ Category retrieval")
        print("   - ✅ Memory search by categories")
        print("   - ✅ Category deletion")
        print("   - ✅ Database integrity checks")
        print("\n🎉 Database schema is working perfectly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during database testing: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up temporary file
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_storage_integration():
    """Test integration with existing storage system"""
    print("\n🔄 Testing Storage Integration")
    print("=" * 40)
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        db = SQLiteManager(db_path)
        
        # Test that both history and categories tables coexist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all expected tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {table[0] for table in cursor.fetchall()}
        
        expected_tables = {'history', 'categories', 'memory_categories'}
        if expected_tables.issubset(tables):
            print("✅ All tables coexist properly")
        else:
            missing = expected_tables - tables
            print(f"❌ Missing tables: {list(missing)}")
            return False
            
        # Test history table functionality still works
        memory_id = "integration-test-memory"
        db.add_history(memory_id, None, "Test memory", "ADD")
        
        history = db.get_history(memory_id)
        if len(history) == 1 and history[0]['event'] == 'ADD':
            print("✅ History table functionality preserved")
        else:
            print("❌ History table functionality broken")
            return False
            
        # Test categories functionality alongside history
        db.assign_memory_categories(memory_id, ["integration", "test"])
        categories = db.get_memory_categories(memory_id)
        
        if set(categories) == {"integration", "test"}:
            print("✅ Categories work alongside history")
        else:
            print(f"❌ Categories integration failed: {categories}")
            return False
            
        # Test reset functionality includes categories
        db.reset()
        
        # Check that all data was cleared
        cursor.execute("SELECT COUNT(*) FROM history")
        history_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM categories")
        categories_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memory_categories")
        memory_categories_count = cursor.fetchone()[0]
        
        if history_count == 0 and categories_count == 0 and memory_categories_count == 0:
            print("✅ Reset functionality includes categories")
        else:
            print(f"❌ Reset incomplete. History: {history_count}, Categories: {categories_count}, Links: {memory_categories_count}")
            return False
            
        conn.close()
        db.close()
        
        print("\n✅ Storage Integration Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during integration testing: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    print("🚀 Starting Categories Database Testing...")
    
    success = True
    
    # Run database functionality test
    if not test_categories_database():
        success = False
    
    # Run storage integration test
    if not test_storage_integration():
        success = False
    
    if success:
        print("\n🎉 All database tests passed! Categories database functionality is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some database tests failed. Please check the implementation.")
        sys.exit(1)