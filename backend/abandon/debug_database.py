#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug database directly
"""

import sqlite3
from app.config import get_settings
from app.services.storage import Storage

def debug_database():
    """Debug database content"""
    
    cfg = get_settings()
    print(f"Database path: {cfg.DB_PATH}")
    
    # Connect directly to SQLite
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Check session table structure
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(sessions)")
    columns = cursor.fetchall()
    
    print("\nSessions table structure:")
    for col in columns:
        print(f"  {col[1]} {col[2]} (nullable: {col[3] == 0})")
    
    # Check all sessions
    cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 5")
    sessions = cursor.fetchall()
    
    print(f"\nRecent sessions:")
    for session in sessions:
        row_dict = dict(session)
        print(f"  Session ID: {row_dict['session_id']}")
        print(f"    current_qid: {row_dict.get('current_qid')}")
        print(f"    fsm_state: {row_dict.get('fsm_state')}")
        print(f"    asked_qids: {row_dict.get('asked_qids')}")
        print(f"    followup_ptr: {row_dict.get('followup_ptr')}")
        print(f"    updated_at: {row_dict.get('updated_at')}")
        print()
    
    conn.close()

if __name__ == "__main__":
    debug_database()