#!/usr/bin/env python3
"""
Debug the exact critical point where dimension is lost
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_critical_point():
    print("🔍 Testing critical failure point")

    # Login
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "uc2test@example.com",
        "password": "testpass123"
    })

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create conversation
    response = requests.post(f"{BASE_URL}/conversations", json={
        "type": "dimension",
        "dimension": "Aesthetic",
        "title": "Critical Point Test"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    # Step 1: Start
    print("\n=== Step 1: Start ===")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "Start",
        "dimension_focus": "Aesthetic"
    }, headers=chat_headers)
    print(f"Result: PNM={response.json().get('current_pnm')}, Term={response.json().get('current_term')}")

    # Step 2: Answer 1
    print("\n=== Step 2: First Answer ===")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "answer1"
    }, headers=chat_headers)
    print(f"Result: PNM={response.json().get('current_pnm')}, Term={response.json().get('current_term')}")

    # Step 3: Answer 2
    print("\n=== Step 3: Second Answer ===")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "answer2"
    }, headers=chat_headers)
    print(f"Result: PNM={response.json().get('current_pnm')}, Term={response.json().get('current_term')}")

    # Step 4: Critical Answer 3 - This is where it breaks
    print("\n=== Step 4: CRITICAL THIRD Answer ===")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "answer3"
    }, headers=chat_headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Result: PNM={result.get('current_pnm')}, Term={result.get('current_term')}")

        if result.get('current_pnm') != 'Aesthetic':
            print(f"❌ DIMENSION LOST! Expected Aesthetic, got {result.get('current_pnm')}")
            print(f"Full response: {json.dumps(result, indent=2)}")
        else:
            print(f"✅ Still in Aesthetic dimension")
    else:
        print(f"❌ Request failed: {response.text}")

if __name__ == "__main__":
    test_critical_point()