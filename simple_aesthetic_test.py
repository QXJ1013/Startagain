#!/usr/bin/env python3
"""
Simple test to check Aesthetic dimension completion
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_simple_aesthetic():
    print("🎯 Simple Aesthetic Completion Test")

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
        "title": "Simple Aesthetic Test"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    # 1. Start assessment - expect first question
    print("\n=== Step 1: Start Assessment ===")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "Start",
        "dimension_focus": "Aesthetic"
    }, headers=chat_headers)

    result = response.json()
    print(f"Question: {result.get('question_text', '')[:100]}...")
    print(f"Term: {result.get('current_term')}")
    print(f"Type: {result.get('question_type')}")

    # 2. Answer with simple response to move forward
    print("\n=== Step 2: Answer First Question ===")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "good"  # Simple text answer
    }, headers=chat_headers)

    result = response.json()
    print(f"Question: {result.get('question_text', '')[:100]}...")
    print(f"Term: {result.get('current_term')}")
    print(f"PNM: {result.get('current_pnm')}")
    print(f"Type: {result.get('question_type')}")

    # If we got another question in same dimension, answer it
    if result.get('current_pnm') == 'Aesthetic':
        print("\n=== Step 3: Answer Follow-up or Next Question ===")
        response = requests.post(f"{BASE_URL}/chat/conversation", json={
            "user_response": "fine"
        }, headers=chat_headers)

        result = response.json()
        print(f"Question: {result.get('question_text', '')[:100]}...")
        print(f"Term: {result.get('current_term')}")
        print(f"PNM: {result.get('current_pnm')}")
        print(f"Type: {result.get('question_type')}")

        # If still in Aesthetic, try one more
        if result.get('current_pnm') == 'Aesthetic':
            print("\n=== Step 4: Answer Next Aesthetic Question ===")
            response = requests.post(f"{BASE_URL}/chat/conversation", json={
                "user_response": "okay"
            }, headers=chat_headers)

            result = response.json()
            print(f"Question: {result.get('question_text', '')[:100]}...")
            print(f"Term: {result.get('current_term')}")
            print(f"PNM: {result.get('current_pnm')}")
            print(f"Type: {result.get('question_type')}")

    # Check final status
    print("\n=== Final Status ===")
    response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
    conv = response.json()
    print(f"Status: {conv.get('status')}")

    # Show assessment state
    assessment_state = conv.get('assessment_state', {})
    for key, value in assessment_state.items():
        if 'Aesthetic' in key or 'completed' in key or 'locked' in key:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    test_simple_aesthetic()