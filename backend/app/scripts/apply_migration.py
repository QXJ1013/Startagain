#!/usr/bin/env python3
"""
Apply database migrations for conversation history feature
"""
import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import get_settings

def apply_migration(db_path: str):
    """Apply conversation history migration to existing database"""
    
    print(f"Applying migration to: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    try:
        # Check if conversations table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conversations'
        """)
        if cursor.fetchone():
            print("Conversations table already exists, skipping migration")
            return
        
        print("Creating conversations table...")
        
        # Read and execute migration SQL
        migration_path = Path(__file__).parent.parent / 'data' / 'migrations' / '001_add_conversations.sql'
        if migration_path.exists():
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            # Execute only the CREATE TABLE statements first
            # Remove ALTER TABLE statements as we'll handle them separately
            lines = migration_sql.split('\n')
            filtered_sql = []
            skip_alter = False
            
            for line in lines:
                if 'ALTER TABLE' in line:
                    skip_alter = True
                elif line.strip().endswith(';'):
                    skip_alter = False
                elif not skip_alter:
                    filtered_sql.append(line)
            
            create_statements = '\n'.join(filtered_sql)
            statements = create_statements.split(';')
            
            for stmt in statements:
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--') and 'CREATE' in stmt:
                    try:
                        cursor.execute(stmt)
                        conn.commit()
                    except sqlite3.OperationalError as e:
                        # Handle cases where columns/tables already exist
                        if "duplicate column name" in str(e) or "already exists" in str(e):
                            print(f"  Skipping (already exists): {stmt[:50]}...")
                        else:
                            print(f"  Error executing: {stmt[:100]}...")
                            print(f"  Error details: {e}")
        
        # Add missing columns to existing tables (safe to run multiple times)
        print("Updating existing tables...")
        
        # Check and add conversation_id to turns
        cursor.execute("PRAGMA table_info(turns)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'conversation_id' not in columns:
            print("  Adding conversation_id to turns table...")
            cursor.execute("ALTER TABLE turns ADD COLUMN conversation_id TEXT")
            cursor.execute("CREATE INDEX idx_turns_conversation_id ON turns(conversation_id)")
        
        # Check and add columns to evidence_log
        cursor.execute("PRAGMA table_info(evidence_log)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'conversation_id' not in columns:
            print("  Adding conversation_id to evidence_log table...")
            cursor.execute("ALTER TABLE evidence_log ADD COLUMN conversation_id TEXT")
            cursor.execute("CREATE INDEX idx_evidence_conversation_id ON evidence_log(conversation_id)")
        
        if 'card_type' not in columns:
            print("  Adding card_type to evidence_log table...")
            cursor.execute("ALTER TABLE evidence_log ADD COLUMN card_type TEXT DEFAULT 'info'")
        
        if 'card_data' not in columns:
            print("  Adding card_data to evidence_log table...")
            cursor.execute("ALTER TABLE evidence_log ADD COLUMN card_data TEXT")
        
        if 'display_order' not in columns:
            print("  Adding display_order to evidence_log table...")
            cursor.execute("ALTER TABLE evidence_log ADD COLUMN display_order INTEGER DEFAULT 0")
        
        # Add missing columns to users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'password_hash' not in columns:
            print("  Adding password_hash to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        
        if 'last_login' not in columns:
            print("  Adding last_login to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
        
        if 'is_active' not in columns:
            print("  Adding is_active to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Show statistics
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM turns")
        turn_count = cursor.fetchone()[0]
        
        print(f"\nDatabase statistics:")
        print(f"  Users: {user_count}")
        print(f"  Sessions: {session_count}")
        print(f"  Turns: {turn_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    settings = get_settings()
    db_path = settings.DB_PATH
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        sys.exit(1)
    
    # Backup database first
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    
    apply_migration(db_path)