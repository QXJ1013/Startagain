"""
Database Optimization Script
Improves query performance for demo environment
"""

import sqlite3
import os
import time
from datetime import datetime, timedelta

def optimize_database():
    """Main optimization function"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'als.db')
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return False
    
    print(f"[INFO] Optimizing database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    try:
        # 1. Add missing indexes for performance
        print("\n[STEP 1] Adding performance indexes...")
        
        indexes = [
            # User queries
            ("idx_users_email", "users(email)"),
            ("idx_users_active", "users(is_active)"),
            
            # Session queries - most important for performance
            ("idx_sessions_user_id", "sessions(user_id)"),
            ("idx_sessions_status", "sessions(status)"),
            ("idx_sessions_updated", "sessions(updated_at DESC)"),
            ("idx_sessions_pnm_term", "sessions(current_pnm, current_term)"),
            
            # Turn queries - very frequent
            ("idx_turns_role", "turns(role)"),
            ("idx_turns_created", "turns(created_at DESC)"),
            
            # Score queries
            ("idx_term_scores_session", "term_scores(session_id)"),
            ("idx_term_scores_pnm", "term_scores(pnm)"),
            ("idx_dim_scores_session", "dimension_scores(session_id)"),
            
            # Evidence queries
            ("idx_evidence_pnm_term", "evidence_log(pnm, term)"),
            ("idx_evidence_tag", "evidence_log(tag)"),
            
            # Conversation queries
            ("idx_conversations_session", "conversations(session_id)"),
            ("idx_conversations_type", "conversations(conversation_type)"),
        ]
        
        for idx_name, idx_def in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
                print(f"  [OK] Created index {idx_name}")
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    print(f"  [WARN] Failed to create {idx_name}: {e}")
        
        # 2. Clean up old/orphaned data
        print("\n[STEP 2] Cleaning up old data...")
        
        # Delete inactive sessions older than 7 days
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            DELETE FROM sessions 
            WHERE status != 'active' 
            AND updated_at < ?
        """, (week_ago,))
        deleted_sessions = cursor.rowcount
        print(f"  [OK] Deleted {deleted_sessions} old inactive sessions")
        
        # Delete orphaned turns (sessions that don't exist)
        cursor.execute("""
            DELETE FROM turns 
            WHERE session_id NOT IN (SELECT session_id FROM sessions)
        """)
        deleted_turns = cursor.rowcount
        print(f"  [OK] Deleted {deleted_turns} orphaned turns")
        
        # Delete orphaned scores
        cursor.execute("""
            DELETE FROM term_scores 
            WHERE session_id NOT IN (SELECT session_id FROM sessions)
        """)
        deleted_scores = cursor.rowcount
        print(f"  [OK] Deleted {deleted_scores} orphaned term scores")
        
        # 3. Optimize table storage
        print("\n[STEP 3] Optimizing table storage...")
        
        # Update statistics for query planner
        cursor.execute("ANALYZE")
        print("  [OK] Updated query statistics")
        
        # Rebuild database to reclaim space
        cursor.execute("VACUUM")
        print("  [OK] Reclaimed unused space")
        
        # 4. Performance settings
        print("\n[STEP 4] Applying performance settings...")
        
        # Optimize for read-heavy workload
        cursor.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous = NORMAL")  # Faster writes
        cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store = MEMORY")  # Use memory for temp tables
        cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory-mapped I/O
        print("  [OK] Applied performance pragmas")
        
        # 5. Create useful views for common queries
        print("\n[STEP 5] Creating optimized views...")
        
        # View for active sessions with scores
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_active_sessions AS
            SELECT 
                s.session_id,
                s.user_id,
                s.current_pnm,
                s.current_term,
                s.turn_index,
                s.updated_at,
                COUNT(DISTINCT ts.term) as scored_terms,
                COUNT(DISTINCT ds.pnm) as scored_dimensions
            FROM sessions s
            LEFT JOIN term_scores ts ON s.session_id = ts.session_id
            LEFT JOIN dimension_scores ds ON s.session_id = ds.session_id
            WHERE s.status = 'active'
            GROUP BY s.session_id
        """)
        print("  [OK] Created v_active_sessions view")
        
        # View for recent conversations
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_recent_conversations AS
            SELECT 
                c.*,
                u.display_name as user_name,
                COUNT(t.id) as turn_count
            FROM conversations c
            JOIN users u ON c.user_id = u.id
            LEFT JOIN turns t ON c.session_id = t.session_id
            WHERE c.status = 'active'
            GROUP BY c.id
            ORDER BY c.last_activity DESC
        """)
        print("  [OK] Created v_recent_conversations view")
        
        # 6. Database integrity check
        print("\n[STEP 6] Checking database integrity...")
        integrity = cursor.execute("PRAGMA integrity_check").fetchone()
        if integrity[0] == "ok":
            print("  [OK] Database integrity verified")
        else:
            print(f"  [WARN] Integrity issue: {integrity[0]}")
        
        # Get database stats
        print("\n[STATS] Database Statistics:")
        
        # Table sizes
        tables = ['users', 'sessions', 'turns', 'conversations', 'term_scores', 'dimension_scores']
        for table in tables:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  - {table}: {count} rows")
        
        # Database file size
        file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        print(f"\n  [SIZE] Database size: {file_size:.2f} MB")
        
        conn.commit()
        print("\n[SUCCESS] Database optimization complete!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Optimization failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def create_demo_data():
    """Optional: Create demo data for testing"""
    print("\n[INFO] Creating demo data...")
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'als.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if demo user exists
        demo_user = cursor.execute(
            "SELECT id FROM users WHERE email = ?", 
            ("demo@example.com",)
        ).fetchone()
        
        if not demo_user:
            # Create demo user
            import hashlib
            password_hash = hashlib.sha256("demo123".encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, display_name)
                VALUES ('demo-user', 'demo@example.com', ?, 'Demo User')
            """, (password_hash,))
            
            print("  [OK] Created demo user (email: demo@example.com, password: demo123)")
        else:
            print("  [INFO] Demo user already exists")
        
        conn.commit()
        
    except Exception as e:
        print(f"  [WARN] Failed to create demo data: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    print("="*50)
    print("DATABASE OPTIMIZATION TOOL")
    print("="*50)
    
    # Run optimization
    success = optimize_database()
    
    # Optionally create demo data
    if success:
        response = input("\nCreate demo user? (y/n): ")
        if response.lower() == 'y':
            create_demo_data()
    
    print("\n" + "="*50)
    print("OPTIMIZATION COMPLETE")
    print("="*50)