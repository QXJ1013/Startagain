#!/usr/bin/env python3
"""
Test to trigger and capture the UC2 exception
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_exception_trigger():
    print("🔍 Testing to trigger UC2 exception")

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
        "title": "Exception Test"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    # Steps to trigger the exception
    steps = [
        {"user_response": "Start", "dimension_focus": "Aesthetic"},
        {"user_response": "first"},
        {"user_response": "second"},
        {"user_response": "third"}  # This should trigger the exception
    ]

    for i, step in enumerate(steps):
        print(f"\n=== Step {i+1}: {step['user_response']} ===")

        # Add a small delay to ensure server processing is complete
        time.sleep(0.5)

        response = requests.post(f"{BASE_URL}/chat/conversation", json=step, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            print(f"Response: PNM={result.get('current_pnm')}, Term={result.get('current_term')}")
            print(f"Question Type: {result.get('question_type')}")
            print(f"Next State: {result.get('next_state')}")

            # If we detect the fallback response, we've found the exception point
            if result.get('question_type') == 'main' and result.get('next_state') == 'ask_question':
                print(f"❌ DETECTED FALLBACK TO LEGACY SYSTEM!")
                print(f"This means Enhanced Dialogue threw an exception on step {i+1}")
                break
        else:
            print(f"❌ HTTP Error: {response.status_code} - {response.text}")
            break

    # Check the conversation state to see what got stored
    print(f"\n=== Final State Check ===")
    response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
    if response.status_code == 200:
        conv = response.json()
        assessment_state = conv.get('assessment_state', {})

        print(f"Type: {conv.get('type')}, Dimension: {conv.get('dimension')}")
        print(f"Assessment state keys: {list(assessment_state.keys())}")

        # Look for UC2-specific state
        for key, value in assessment_state.items():
            if 'Aesthetic' in key or 'term' in key:
                print(f"  {key}: {value}")

if __name__ == "__main__":
    test_exception_trigger()