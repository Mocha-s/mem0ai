#!/usr/bin/env python3
"""Quick test for categories functionality"""

import tempfile
import os
from mem0.memory.storage import SQLiteManager

def main():
    print("🔄 Quick Categories Test")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        print("1. Creating SQLiteManager...")
        db = SQLiteManager(db_path)
        
        print("2. Adding category...")
        cat_id = db.add_category("test", "Test category")
        print(f"   Category ID: {cat_id}")
        
        print("3. Assigning to memory...")
        db.assign_memory_categories("mem-123", ["test", "sports"])
        
        print("4. Getting categories...")
        cats = db.get_memory_categories("mem-123")
        print(f"   Categories: {cats}")
        
        print("5. Getting all categories...")
        all_cats = db.get_all_categories()
        print(f"   Found {len(all_cats)} categories")
        
        db.close()
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    main()