#!/usr/bin/env python3
"""
Try to trigger summary with one more answer
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def trigger_summary():
    print("🎯 Trigger Summary Test")

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
        "title": "Trigger Summary"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    # Fast track to the point where we were in the previous test
    answers = ["Start", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10"]

    for i, answer in enumerate(answers):
        if i == 0:
            req = {"user_response": answer, "dimension_focus": "Aesthetic"}
        else:
            req = {"user_response": answer}

        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            response_type = result.get('question_type', 'unknown')

            print(f"Answer {i+1}: type={response_type}, PNM={result.get('current_pnm')}, term={result.get('current_term')}")

            if response_type == 'summary':
                print(f"\n🎉 SUMMARY TRIGGERED on answer {i+1}!")
                print(f"Summary: {result.get('question_text', '')[:100]}...")

                # Check completion status
                conv_response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
                conv = conv_response.json()
                print(f"Status after summary: {conv.get('status')}")
                return True

        else:
            print(f"❌ Request {i+1} failed: {response.text}")
            return False

    print(f"❌ No summary triggered after {len(answers)} answers")
    return False

if __name__ == "__main__":
    trigger_summary()