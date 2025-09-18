#!/usr/bin/env python3
"""
Debug temp scores accumulation specifically
"""
import requests

BASE_URL = "http://localhost:8000"

def debug_temp_scores():
    print("=== Debug Temp Scores Accumulation ===")

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
        "title": "Debug Temp Scores"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}
    print(f"Created conversation: {conv_id}")

    # Send minimal test sequence
    print("\n=== Minimal Test Sequence ===")

    # Step 1: Initialize
    print("Step 1: Initialize")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "Begin",
        "dimension_focus": "Aesthetic"
    }, headers=chat_headers)

    if response.status_code == 200:
        result = response.json()
        print(f"  Initial: {result.get('current_pnm')}/{result.get('current_term')}")
    else:
        print(f"  ERROR: {response.status_code}")
        return

    # Step 2: Single score
    print("\nStep 2: Send score '2'")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "2"
    }, headers=chat_headers)

    if response.status_code == 200:
        result = response.json()
        print(f"  After score: {result.get('current_pnm')}/{result.get('current_term')}")
    else:
        print(f"  ERROR: {response.status_code}")

    print(f"\n=== Required Backend Log Messages ===")
    print("You MUST see these exact messages in the backend logs:")
    print("1. [UC2] *** PROCESSING USER RESPONSE: '2' ***")
    print("2. [UC2] DEBUG: Attempting to extract score from user input: '2'")
    print("3. [UC2] SCORING: Direct numeric score: 2.0")
    print("4. [UC2] DEBUG: Extracted score result: 2.0")
    print("5. [UC2] Collected score 2.0 for term X, total scores: 1")
    print("6. [UC2] Staying on current question to allow more responses (current: 1 scores)")
    print("7. [UC2] Current temp scores after processing: {'temp_scores_X': [2.0]}")
    print("8. [UC2] *** ABOUT TO CHECK TERM COMPLETION FOR Aesthetic ***")
    print("9. [UC2] FORCE CHECK: temp_scores count = 1")
    print()
    print("If you DON'T see these messages:")
    print("- Missing 1-4: Score extraction is failing")
    print("- Missing 5-6: Score accumulation is failing")
    print("- Missing 7: Temp scores are not being stored")
    print("- Missing 8-9: Term completion check is not running")

if __name__ == "__main__":
    debug_temp_scores()