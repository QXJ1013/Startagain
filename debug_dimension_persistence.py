#!/usr/bin/env python3
"""
Debug dimension persistence in conversation
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_dimension_persistence():
    print("🔍 Testing dimension persistence")

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
        "title": "Dimension Persistence Test"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    def check_conversation_state(step_name):
        response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
        conv = response.json()
        print(f"\n--- {step_name} Conversation State ---")
        print(f"  Type: {conv.get('type')}")
        print(f"  Dimension: {conv.get('dimension')}")
        print(f"  Status: {conv.get('status')}")
        return conv

    # Check initial state
    check_conversation_state("Initial")

    # Start assessment
    print("\n=== Starting Assessment ===")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "Start",
        "dimension_focus": "Aesthetic"
    }, headers=chat_headers)

    result = response.json()
    print(f"Response PNM: {result.get('current_pnm')}")
    print(f"Response Term: {result.get('current_term')}")
    check_conversation_state("After Start")

    # Answer questions
    for i in range(4):  # Try 4 answers to see when it breaks
        print(f"\n=== Answer {i+1} ===")
        response = requests.post(f"{BASE_URL}/chat/conversation", json={
            "user_response": f"answer{i+1}"
        }, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            print(f"Response PNM: {result.get('current_pnm')}")
            print(f"Response Term: {result.get('current_term')}")
            print(f"Question Type: {result.get('question_type')}")

            conv = check_conversation_state(f"After Answer {i+1}")

            # Check if we're still in Aesthetic dimension
            if result.get('current_pnm') != 'Aesthetic':
                print(f"❌ DIMENSION LOST! Now in {result.get('current_pnm')}")
                break
        else:
            print(f"❌ Request failed: {response.text}")
            break

if __name__ == "__main__":
    test_dimension_persistence()