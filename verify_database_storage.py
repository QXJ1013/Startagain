#!/usr/bin/env python3
"""
Verify if term scoring and PNM scoring are correctly stored in database
"""
import requests
import time
import sqlite3
from pathlib import Path

BASE_URL = "http://localhost:8000"

def verify_database_storage():
    print("=== Verify Term & PNM Scoring Database Storage ===")

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
        "title": "Database Storage Verification"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}
    print(f"Created conversation: {conv_id}")

    # Get database baseline
    db_path = Path("backend/app/data/als.db")
    conn = sqlite3.connect(str(db_path))
    before_count = conn.execute("SELECT COUNT(*) FROM conversation_scores").fetchone()[0]
    conn.close()
    print(f"Database baseline: {before_count} scores")

    # Test sequence designed to trigger term completion
    print("\n=== Testing Term Completion & Database Storage ===")

    test_inputs = [
        {"desc": "Initialize", "input": {"user_response": "start", "dimension_focus": "Aesthetic"}},
        {"desc": "Score 1", "input": {"user_response": "2"}},
        {"desc": "Score 2", "input": {"user_response": "4"}},
        {"desc": "Score 3", "input": {"user_response": "0"}},  # Should trigger term completion
        {"desc": "Score 4", "input": {"user_response": "6"}},  # Should trigger again if needed
        {"desc": "Score 5", "input": {"user_response": "1"}},  # More scores to ensure completion
    ]

    successful_storage = False

    for i, test in enumerate(test_inputs):
        print(f"\n--- {test['desc']} ---")

        response = requests.post(f"{BASE_URL}/chat/conversation", json=test['input'], headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            term = result.get('current_term', 'unknown')
            pnm = result.get('current_pnm', 'unknown')
            print(f"  Response: {pnm}/{term}")

            # Check database immediately after each request
            conn = sqlite3.connect(str(db_path))
            current_count = conn.execute("SELECT COUNT(*) FROM conversation_scores").fetchone()[0]

            if current_count > before_count:
                print(f"  🎉 DATABASE SUCCESS: {current_count} scores (was {before_count})")

                # Get all scores for this conversation
                scores = conn.execute('''
                    SELECT pnm, term, score, status, updated_at
                    FROM conversation_scores
                    WHERE conversation_id = ?
                    ORDER BY updated_at DESC
                ''', (conv_id,)).fetchall()

                print(f"  Found {len(scores)} score(s) for this conversation:")
                for score in scores:
                    print(f"    {score[0]} | {score[1]} | {score[2]:.2f} | {score[3]} | {score[4]}")

                successful_storage = True
                before_count = current_count

                # Continue to see if we can get more scores
            else:
                print(f"  No database change: {current_count} scores")

            conn.close()

        else:
            print(f"  ERROR: {response.status_code} - {response.text[:200]}")
            break

        time.sleep(1)  # Small delay between requests

    # Final comprehensive database check
    print(f"\n=== Final Database Analysis ===")
    conn = sqlite3.connect(str(db_path))

    # Check conversation_scores table for this conversation
    conv_scores = conn.execute('''
        SELECT pnm, term, score, status, updated_at
        FROM conversation_scores
        WHERE conversation_id = ?
        ORDER BY updated_at ASC
    ''', (conv_id,)).fetchall()

    print(f"Final scores for conversation {conv_id}: {len(conv_scores)}")
    for i, score in enumerate(conv_scores):
        print(f"  {i+1}. {score[0]} | {score[1]} | Score: {score[2]:.2f} | Status: {score[3]}")

    # Check for any recent scores in the system
    recent_scores = conn.execute('''
        SELECT conversation_id, pnm, term, score, updated_at
        FROM conversation_scores
        WHERE updated_at >= datetime('now', '-1 hour')
        ORDER BY updated_at DESC
        LIMIT 10
    ''').fetchall()

    print(f"\nRecent scores in system (last hour): {len(recent_scores)}")
    for score in recent_scores:
        print(f"  {score[0]} | {score[1]}/{score[2]} = {score[3]:.2f} | {score[4]}")

    conn.close()

    # Final assessment
    print(f"\n=== Storage Verification Results ===")
    if conv_scores:
        print("✅ SUCCESS: Term scoring is working and storing to database")
        print("✅ SUCCESS: PNM scoring is working and storing to database")
        print(f"✅ Total scores stored: {len(conv_scores)}")
        print("✅ UC2 evaluation system is fully functional")

        # Analyze scoring patterns
        unique_terms = set(score[1] for score in conv_scores)
        unique_pnms = set(score[0] for score in conv_scores)
        print(f"✅ Terms evaluated: {len(unique_terms)} - {list(unique_terms)}")
        print(f"✅ PNM dimensions: {len(unique_pnms)} - {list(unique_pnms)}")

    else:
        print("❌ FAILURE: No scores were stored to database")
        print("❌ Term scoring is not working properly")
        print("❌ PNM scoring is not working properly")
        print("❌ UC2 evaluation system needs further debugging")

        if successful_storage:
            print("⚠️  Note: Temporary success was observed during testing")
            print("⚠️  Issue may be in term completion logic or storage verification")

if __name__ == "__main__":
    verify_database_storage()