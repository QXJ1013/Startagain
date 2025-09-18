#!/usr/bin/env python3
"""
Debug UC2 completion detection
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_aesthetic_completion():
    print("🔍 Testing Aesthetic dimension completion")

    # Login
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "uc2test@example.com",
        "password": "testpass123"
    })

    if response.status_code != 200:
        print("❌ Login failed")
        return

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create Aesthetic dimension conversation
    response = requests.post(f"{BASE_URL}/conversations", json={
        "type": "dimension",
        "dimension": "Aesthetic",
        "title": "Aesthetic Debug Test"
    }, headers=headers)

    if response.status_code != 200:
        print("❌ Conversation creation failed")
        return

    conv_id = response.json()["id"]
    print(f"✅ Created conversation: {conv_id}")

    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    # Test exactly 2 responses for the 2 Aesthetic questions
    responses = [
        {"user_response": "Start assessment", "dimension_focus": "Aesthetic"},
        {"user_response": "4"}  # Answer first question with option 4
    ]

    for i, req in enumerate(responses):
        print(f"\n--- Request {i+1}: {req['user_response']} ---")

        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response type: {result.get('question_type')}")
            print(f"   Current PNM: {result.get('current_pnm')}")
            print(f"   Current term: {result.get('current_term')}")
            print(f"   dialogue_mode: {result.get('dialogue_mode')}")
            print(f"   Question text: {result.get('question_text', '')[:100]}...")

            if 'options' in result and result['options']:
                print(f"   Options count: {len(result['options'])}")

            # Check if we got a summary
            if result.get('question_type') == 'summary':
                print(f"🎉 SUMMARY RECEIVED!")
                break
        else:
            print(f"❌ Request failed: {response.text}")

    # Now test the second question
    print(f"\n--- Request 3: Answer second question ---")
    response = requests.post(f"{BASE_URL}/chat/conversation", json={
        "user_response": "3"  # Answer second question with option 3
    }, headers=chat_headers)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Response type: {result.get('question_type')}")
        print(f"   Current PNM: {result.get('current_pnm')}")
        print(f"   Current term: {result.get('current_term')}")
        print(f"   dialogue_mode: {result.get('dialogue_mode')}")

        if result.get('question_type') == 'summary':
            print(f"🎉 SUMMARY RECEIVED AFTER SECOND QUESTION!")
        else:
            print(f"❌ Expected summary but got: {result.get('question_type')}")
    else:
        print(f"❌ Second answer failed: {response.text}")

    # Check final conversation status
    print(f"\n🔍 Final Status Check...")
    response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
    if response.status_code == 200:
        conv = response.json()
        print(f"   Conversation status: {conv.get('status')}")
        assessment_state = conv.get('assessment_state', {})

        # Check for completion keys
        for key, value in assessment_state.items():
            if 'completed' in key or 'locked' in key:
                print(f"   {key}: {value}")

        # Check temp scores
        for key, value in assessment_state.items():
            if 'temp_scores' in key:
                print(f"   {key}: {value}")

if __name__ == "__main__":
    test_aesthetic_completion()