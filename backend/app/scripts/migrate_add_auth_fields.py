#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database migration script to add authentication fields to existing database.
This handles the transition from session-based to auth-based system.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import get_settings


def migrate_database():
    """Add authentication fields to existing database"""
    settings = get_settings()
    db_path = settings.DB_PATH
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Creating new database with updated schema.")
        # If no database exists, the main app will create it with the new schema
        return
    
    print(f"Migrating database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Check if users table exists and what columns it has
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        print(f"Current users table columns: {user_columns}")
        
        # Add missing columns to users table
        migrations = []
        
        if 'password_hash' not in user_columns:
            migrations.append(("users", "password_hash", "TEXT DEFAULT ''"))
            
        if 'is_active' not in user_columns:
            migrations.append(("users", "is_active", "BOOLEAN DEFAULT 1"))
            
        if 'last_login' not in user_columns:
            migrations.append(("users", "last_login", "DATETIME"))
            
        if 'updated_at' not in user_columns:
            migrations.append(("users", "updated_at", "DATETIME"))
        
        # Apply migrations
        for table, column, column_def in migrations:
            try:
                sql = f"ALTER TABLE {table} ADD COLUMN {column} {column_def}"
                print(f"Executing: {sql}")
                cursor.execute(sql)
                print(f"  [OK] Added {column} to {table}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - Column {column} already exists in {table}")
                else:
                    print(f"  [ERROR] Error adding {column} to {table}: {e}")
        
        # Check sessions table
        cursor.execute("PRAGMA table_info(sessions)")
        session_columns = [col[1] for col in cursor.fetchall()]
        print(f"\nCurrent sessions table columns: {session_columns}")
        
        # Ensure sessions table has all required columns
        session_migrations = []
        
        if 'pnm_scores' not in session_columns:
            session_migrations.append(("sessions", "pnm_scores", "TEXT DEFAULT '[]'"))
            
        if 'evidence_count' not in session_columns:
            session_migrations.append(("sessions", "evidence_count", "TEXT DEFAULT '{}'"))
        
        for table, column, column_def in session_migrations:
            try:
                sql = f"ALTER TABLE {table} ADD COLUMN {column} {column_def}"
                print(f"Executing: {sql}")
                cursor.execute(sql)
                print(f"  [OK] Added {column} to {table}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - Column {column} already exists in {table}")
                else:
                    print(f"  [ERROR] Error adding {column} to {table}: {e}")
        
        # Clean up orphaned sessions (sessions without valid user_id)
        print("\nCleaning up orphaned sessions...")
        cursor.execute("""
            SELECT COUNT(*) FROM sessions 
            WHERE user_id IS NULL OR user_id NOT IN (SELECT id FROM users)
        """)
        orphaned_count = cursor.fetchone()[0]
        
        if orphaned_count > 0:
            print(f"Found {orphaned_count} orphaned sessions")
            # Archive orphaned sessions before deletion (optional)
            cursor.execute("""
                DELETE FROM sessions 
                WHERE user_id IS NULL OR user_id NOT IN (SELECT id FROM users)
            """)
            print(f"  [OK] Removed {orphaned_count} orphaned sessions")
        else:
            print("  [OK] No orphaned sessions found")
        
        # Create indexes if they don't exist
        indexes = [
            ("idx_users_email", "users", "email"),
            ("idx_sessions_user_id", "sessions", "user_id"),
            ("idx_conversations_user_id", "conversations", "user_id"),
        ]
        
        for index_name, table, column in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})")
                print(f"  [OK] Created/verified index {index_name}")
            except Exception as e:
                print(f"  - Index {index_name} error: {e}")
        
        conn.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[FAILED] Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()