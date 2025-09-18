#!/usr/bin/env python3
"""
Debug script to test term scoring function directly
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def debug_term_scoring():
    print("=== Debug UC2 Term Scoring ===")

    # Login
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "uc2test@example.com",
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create dimension conversation
    response = requests.post(f"{BASE_URL}/conversations", json={
        "type": "dimension",
        "dimension": "Aesthetic",
        "title": "Debug Term Scoring"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}
    print(f"Created conversation: {conv_id}")

    # Make exactly 4 requests to accumulate scores and force term completion
    for i in range(4):
        print(f"\n--- Request {i+1} ---")

        if i == 0:
            req = {"user_response": "Start debug test", "dimension_focus": "Aesthetic"}
        else:
            req = {"user_response": f"debug response {i}"}

        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            current_term = result.get('current_term', 'unknown')
            print(f"  Current term: {current_term}")
            print(f"  Status: {response.status_code}")
        else:
            print(f"  ERROR: {response.status_code}")
            print(f"  Response: {response.text}")
            break

    # Check database immediately after test
    print("\n=== Checking database for new scores ===")
    time.sleep(2)  # Give time for async operations

    import sqlite3
    from pathlib import Path

    db_path = Path("backend/app/data/als.db")
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        scores = conn.execute('''
            SELECT conversation_id, pnm, term, score, status, updated_at
            FROM conversation_scores
            WHERE conversation_id = ?
            ORDER BY updated_at DESC
        ''', (conv_id,)).fetchall()

        if scores:
            print(f"  Found {len(scores)} scores for this conversation:")
            for score in scores:
                print(f"    {score[1]} | {score[2]} | {score[3]:.2f} | {score[5]}")
        else:
            print(f"  No scores found for conversation {conv_id}")

        conn.close()

    print("\n=== Look for these debug messages in backend logs: ===")
    print("- [UC2] FORCE CHECK: temp_scores count = X")
    print("- [UC2] *** FORCE TERM COMPLETION")
    print("- [UC2] CALLING _trigger_term_scoring_uc2")
    print("- [UC2] FUNCTION CALLED: _trigger_term_scoring_uc2")
    print("- [UC2] DEBUG: About to insert score with values")
    print("- [UC2] INSERT statement executed successfully")
    print("- [UC2] Database transaction committed")
    print("- [UC2] Verification: Score X stored successfully")

if __name__ == "__main__":
    debug_term_scoring()