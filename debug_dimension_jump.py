#!/usr/bin/env python3
"""
Debug dimension jumping issue
"""
import requests

BASE_URL = "http://localhost:8000"

def debug_dimension_jump():
    print("=== Debug Dimension Jumping Issue ===")

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
        "title": "Debug Dimension Jump"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}
    print(f"Created conversation: {conv_id}")
    print(f"Target dimension: Aesthetic")

    # Test minimal sequence to isolate the problem
    test_steps = [
        {
            "name": "Initialize",
            "input": {"user_response": "start", "dimension_focus": "Aesthetic"},
            "expected_pnm": "Aesthetic",
            "description": "Should establish Aesthetic dimension"
        },
        {
            "name": "First Score",
            "input": {"user_response": "2"},
            "expected_pnm": "Aesthetic",
            "description": "Should stay in Aesthetic dimension"
        }
    ]

    for i, step in enumerate(test_steps):
        print(f"\n--- Step {i+1}: {step['name']} ---")
        print(f"Description: {step['description']}")
        print(f"Expected PNM: {step['expected_pnm']}")
        print(f"Input: {step['input']}")

        response = requests.post(f"{BASE_URL}/chat/conversation", json=step['input'], headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            actual_pnm = result.get('current_pnm', 'unknown')
            actual_term = result.get('current_term', 'unknown')

            print(f"Actual result: {actual_pnm}/{actual_term}")

            # Check if dimension is correct
            if actual_pnm == step['expected_pnm']:
                print(f"✅ GOOD: PNM dimension is correct ({actual_pnm})")
            else:
                print(f"❌ BAD: PNM dimension changed unexpectedly!")
                print(f"   Expected: {step['expected_pnm']}")
                print(f"   Actual:   {actual_pnm}")
                print(f"   🚨 DIMENSION JUMP DETECTED!")
                break

        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            break

    print(f"\n=== Analysis ===")
    print("If dimension jumping occurred, check backend logs for:")
    print("1. [MAIN] Routing to UC2 manager for dimension: X")
    print("2. [UC2] *** CRITICAL: UC2 ENTRY POINT REACHED FOR X ***")
    print("3. [UC2] Conversation type: 'dimension', dimension: 'X'")
    print("4. Any error messages in question loading or processing")
    print("5. Look for inconsistencies in dimension values")

if __name__ == "__main__":
    debug_dimension_jump()