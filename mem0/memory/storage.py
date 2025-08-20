import logging
import sqlite3
import threading
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SQLiteManager:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._migrate_history_table()
        self._create_history_table()
        self._create_categories_tables()

    def _migrate_history_table(self) -> None:
        """
        If a pre-existing history table had the old group-chat columns,
        rename it, create the new schema, copy the intersecting data, then
        drop the old table.
        """
        with self._lock:
            try:
                # Start a transaction
                self.connection.execute("BEGIN")
                cur = self.connection.cursor()

                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
                if cur.fetchone() is None:
                    self.connection.execute("COMMIT")
                    return  # nothing to migrate

                cur.execute("PRAGMA table_info(history)")
                old_cols = {row[1] for row in cur.fetchall()}

                expected_cols = {
                    "id",
                    "memory_id",
                    "old_memory",
                    "new_memory",
                    "event",
                    "created_at",
                    "updated_at",
                    "is_deleted",
                    "actor_id",
                    "role",
                }

                if old_cols == expected_cols:
                    self.connection.execute("COMMIT")
                    return

                logger.info("Migrating history table to new schema (no convo columns).")

                # Clean up any existing history_old table from previous failed migration
                cur.execute("DROP TABLE IF EXISTS history_old")

                # Rename the current history table
                cur.execute("ALTER TABLE history RENAME TO history_old")

                # Create the new history table with updated schema
                cur.execute(
                    """
                    CREATE TABLE history (
                        id           TEXT PRIMARY KEY,
                        memory_id    TEXT,
                        old_memory   TEXT,
                        new_memory   TEXT,
                        event        TEXT,
                        created_at   DATETIME,
                        updated_at   DATETIME,
                        is_deleted   INTEGER,
                        actor_id     TEXT,
                        role         TEXT
                    )
                """
                )

                # Copy data from old table to new table
                intersecting = list(expected_cols & old_cols)
                if intersecting:
                    cols_csv = ", ".join(intersecting)
                    cur.execute(f"INSERT INTO history ({cols_csv}) SELECT {cols_csv} FROM history_old")

                # Drop the old table
                cur.execute("DROP TABLE history_old")

                # Commit the transaction
                self.connection.execute("COMMIT")
                logger.info("History table migration completed successfully.")

            except Exception as e:
                # Rollback the transaction on any error
                self.connection.execute("ROLLBACK")
                logger.error(f"History table migration failed: {e}")
                raise

    def _create_history_table(self) -> None:
        with self._lock:
            try:
                self.connection.execute("BEGIN")
                self.connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS history (
                        id           TEXT PRIMARY KEY,
                        memory_id    TEXT,
                        old_memory   TEXT,
                        new_memory   TEXT,
                        event        TEXT,
                        created_at   DATETIME,
                        updated_at   DATETIME,
                        is_deleted   INTEGER,
                        actor_id     TEXT,
                        role         TEXT
                    )
                """
                )
                self.connection.execute("COMMIT")
            except Exception as e:
                self.connection.execute("ROLLBACK")
                logger.error(f"Failed to create history table: {e}")
                raise

    def add_history(
        self,
        memory_id: str,
        old_memory: Optional[str],
        new_memory: Optional[str],
        event: str,
        *,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        is_deleted: int = 0,
        actor_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> None:
        with self._lock:
            try:
                self.connection.execute("BEGIN")
                self.connection.execute(
                    """
                    INSERT INTO history (
                        id, memory_id, old_memory, new_memory, event,
                        created_at, updated_at, is_deleted, actor_id, role
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(uuid.uuid4()),
                        memory_id,
                        old_memory,
                        new_memory,
                        event,
                        created_at,
                        updated_at,
                        is_deleted,
                        actor_id,
                        role,
                    ),
                )
                self.connection.execute("COMMIT")
            except Exception as e:
                self.connection.execute("ROLLBACK")
                logger.error(f"Failed to add history record: {e}")
                raise

    def get_history(self, memory_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self.connection.execute(
                """
                SELECT id, memory_id, old_memory, new_memory, event,
                       created_at, updated_at, is_deleted, actor_id, role
                FROM history
                WHERE memory_id = ?
                ORDER BY created_at ASC, DATETIME(updated_at) ASC
            """,
                (memory_id,),
            )
            rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "memory_id": r[1],
                "old_memory": r[2],
                "new_memory": r[3],
                "event": r[4],
                "created_at": r[5],
                "updated_at": r[6],
                "is_deleted": bool(r[7]),
                "actor_id": r[8],
                "role": r[9],
            }
            for r in rows
        ]

    def reset(self) -> None:
        """Drop and recreate all tables."""
        with self._lock:
            try:
                self.connection.execute("BEGIN")
                self.connection.execute("DROP TABLE IF EXISTS memory_categories")
                self.connection.execute("DROP TABLE IF EXISTS categories")
                self.connection.execute("DROP TABLE IF EXISTS history")
                self.connection.execute("COMMIT")
                self._create_history_table()
                self._create_categories_tables()
            except Exception as e:
                self.connection.execute("ROLLBACK")
                logger.error(f"Failed to reset tables: {e}")
                raise

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def _create_categories_tables(self) -> None:
        """Create categories and memory_categories tables"""
        with self._lock:
            try:
                self.connection.execute("BEGIN")
                
                # Create categories table
                self.connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS categories (
                        id           TEXT PRIMARY KEY,
                        name         TEXT UNIQUE NOT NULL,
                        description  TEXT,
                        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                
                # Create memory_categories junction table
                self.connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_categories (
                        memory_id    TEXT,
                        category_id  TEXT,
                        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (memory_id, category_id),
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )
                """
                )
                
                # Create indexes for better query performance
                self.connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_categories_memory ON memory_categories(memory_id)"
                )
                self.connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_categories_category ON memory_categories(category_id)"
                )
                self.connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name)"
                )
                
                self.connection.execute("COMMIT")
                
            except Exception as e:
                self.connection.execute("ROLLBACK")
                logger.error(f"Failed to create categories tables: {e}")
                raise

    def add_category(self, name: str, description: Optional[str] = None) -> str:
        """Add or get a category by name"""
        category_id = str(uuid.uuid4())
        
        with self._lock:
            try:
                self.connection.execute("BEGIN")
                
                # Check if category already exists
                cur = self.connection.execute("SELECT id FROM categories WHERE name = ?", (name,))
                existing = cur.fetchone()
                
                if existing:
                    self.connection.execute("COMMIT")
                    return existing[0]
                
                # Create new category
                self.connection.execute(
                    """
                    INSERT INTO categories (id, name, description, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (category_id, name, description or f"Auto-generated category for {name}")
                )
                
                self.connection.execute("COMMIT")
                return category_id
                
            except Exception as e:
                self.connection.execute("ROLLBACK")
                logger.error(f"Failed to add category '{name}': {e}")
                raise

    def _get_or_create_category_within_transaction(self, name: str, description: Optional[str] = None) -> str:
        """Get or create a category within an existing transaction (no lock or transaction management)"""
        category_id = str(uuid.uuid4())
        
        # Check if category already exists
        cur = self.connection.execute("SELECT id FROM categories WHERE name = ?", (name,))
        existing = cur.fetchone()
        
        if existing:
            return existing[0]
        
        # Create new category
        self.connection.execute(
            """
            INSERT INTO categories (id, name, description, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (category_id, name, description or f"Auto-generated category for {name}")
        )
        
        return category_id

    def assign_memory_categories(self, memory_id: str, category_names: List[str]) -> None:
        """Assign categories to a memory"""
        with self._lock:
            try:
                self.connection.execute("BEGIN")
                
                # Remove existing category assignments
                self.connection.execute(
                    "DELETE FROM memory_categories WHERE memory_id = ?",
                    (memory_id,)
                )
                
                # Add new category assignments
                for category_name in category_names:
                    if category_name.strip():
                        # Get or create category within the same transaction
                        category_id = self._get_or_create_category_within_transaction(category_name.strip())
                        
                        # Create memory-category association
                        self.connection.execute(
                            """
                            INSERT OR IGNORE INTO memory_categories (memory_id, category_id, created_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                            """,
                            (memory_id, category_id)
                        )
                
                self.connection.execute("COMMIT")
                
            except Exception as e:
                self.connection.execute("ROLLBACK")
                logger.error(f"Failed to assign categories to memory {memory_id}: {e}")
                raise

    def get_memory_categories(self, memory_id: str) -> List[str]:
        """Get category names for a memory"""
        with self._lock:
            cur = self.connection.execute(
                """
                SELECT c.name
                FROM categories c
                JOIN memory_categories mc ON c.id = mc.category_id
                WHERE mc.memory_id = ?
                ORDER BY c.name
                """,
                (memory_id,)
            )
            return [row[0] for row in cur.fetchall()]

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with their usage count"""
        with self._lock:
            cur = self.connection.execute(
                """
                SELECT c.id, c.name, c.description, c.created_at,
                       COUNT(mc.memory_id) as usage_count
                FROM categories c
                LEFT JOIN memory_categories mc ON c.id = mc.category_id
                GROUP BY c.id, c.name, c.description, c.created_at
                ORDER BY usage_count DESC, c.name
                """
            )
            return [
                {
                    "id": row[0],
                    "name": row[1], 
                    "description": row[2],
                    "created_at": row[3],
                    "usage_count": row[4]
                }
                for row in cur.fetchall()
            ]

    def get_memories_by_categories(self, category_names: List[str], limit: Optional[int] = None) -> List[str]:
        """Get memory IDs that have any of the specified categories"""
        if not category_names:
            return []
            
        with self._lock:
            placeholders = ", ".join("?" * len(category_names))
            query = f"""
                SELECT DISTINCT mc.memory_id
                FROM memory_categories mc
                JOIN categories c ON mc.category_id = c.id
                WHERE c.name IN ({placeholders})
                ORDER BY mc.created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cur = self.connection.execute(query, category_names)
            return [row[0] for row in cur.fetchall()]

    def delete_memory_categories(self, memory_id: str) -> None:
        """Remove all category associations for a memory"""
        with self._lock:
            try:
                self.connection.execute("BEGIN")
                self.connection.execute(
                    "DELETE FROM memory_categories WHERE memory_id = ?",
                    (memory_id,)
                )
                self.connection.execute("COMMIT")
                
            except Exception as e:
                self.connection.execute("ROLLBACK")
                logger.error(f"Failed to delete categories for memory {memory_id}: {e}")
                raise

    def __del__(self):
        self.close()
