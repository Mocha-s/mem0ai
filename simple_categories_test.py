#!/usr/bin/env python3
"""
Simple test for categories database schema
"""

import tempfile
import os
from mem0.memory.storage import SQLiteManager

# Test basic functionality
with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
    db_path = tmp.name

try:
    print("Creating SQLiteManager...")
    db = SQLiteManager(db_path)
    
    print("Testing category addition...")
    cat_id = db.add_category("test_category", "A test category")
    print(f"Category added with ID: {cat_id}")
    
    print("Testing memory-category assignment...")
    db.assign_memory_categories("test-memory-123", ["test_category", "another_category"])
    
    print("Testing category retrieval...")
    categories = db.get_memory_categories("test-memory-123")
    print(f"Retrieved categories: {categories}")
    
    print("Testing get all categories...")
    all_cats = db.get_all_categories()
    print(f"All categories: {all_cats}")
    
    print("✅ Basic categories functionality works!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    try:
        db.close()
    except:
        pass
    if os.path.exists(db_path):
        os.unlink(db_path)