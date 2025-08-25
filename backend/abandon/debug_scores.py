#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug scores directly
"""

import sqlite3
from app.config import get_settings

def debug_scores():
    """Debug term and dimension scores in database"""
    
    cfg = get_settings()
    print(f"Database path: {cfg.DB_PATH}")
    
    # Connect directly to SQLite
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.cursor()
    
    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\nAvailable tables:")
    for table in tables:
        print(f"  {table[0]}")
    
    # Check term_scores table
    print("\n=== TERM SCORES ===")
    cursor.execute("SELECT COUNT(*) as count FROM term_scores")
    count = cursor.fetchone()['count']
    print(f"Total term scores: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM term_scores ORDER BY updated_at DESC LIMIT 5")
        scores = cursor.fetchall()
        for score in scores:
            row_dict = dict(score)
            print(f"  Session: {row_dict['session_id']}")
            print(f"    PNM: {row_dict.get('pnm')}, Term: {row_dict.get('term')}")
            print(f"    Score: {row_dict.get('score_0_7')}/7")
            print(f"    Status: {row_dict.get('status')}")
            print(f"    Updated: {row_dict.get('updated_at')}")
            print()
    
    # Check dimension_scores table
    print("=== DIMENSION SCORES ===")
    cursor.execute("SELECT COUNT(*) as count FROM dimension_scores")
    count = cursor.fetchone()['count']
    print(f"Total dimension scores: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM dimension_scores ORDER BY updated_at DESC LIMIT 5")
        scores = cursor.fetchall()
        for score in scores:
            row_dict = dict(score)
            print(f"  Session: {row_dict['session_id']}")
            print(f"    PNM: {row_dict.get('pnm')}")
            print(f"    Score: {row_dict.get('score_0_7')}/7")
            print(f"    Coverage: {row_dict.get('coverage_ratio')}")
            print(f"    Updated: {row_dict.get('updated_at')}")
            print()
    
    # Check turns table
    print("=== RECENT TURNS ===")
    cursor.execute("SELECT * FROM turns ORDER BY id DESC LIMIT 10")
    turns = cursor.fetchall()
    for turn in turns:
        row_dict = dict(turn)
        print(f"  Session: {row_dict['session_id']}")
        print(f"    Turn {row_dict.get('turn_index')}: {row_dict.get('role')}")
        print(f"    Text: {row_dict.get('text', '')[:50]}...")
        print()
    
    conn.close()

if __name__ == "__main__":
    debug_scores()