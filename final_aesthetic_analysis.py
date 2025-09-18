#!/usr/bin/env python3
"""
Final analysis of Aesthetic term structure to identify UC2 completion issue
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def analyze_aesthetic_completion():
    print("🔍 Final Aesthetic Term Structure Analysis")

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
        "title": "Final Analysis"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    print(f"\n✅ Created conversation: {conv_id}")

    # Test exactly the progression that causes issues
    responses = [
        {"user_response": "Start", "dimension_focus": "Aesthetic"},
        {"user_response": "answer1"},
        {"user_response": "answer2"},
        {"user_response": "answer3"}  # This should complete "Adaptive entertainment controls" and move to next term
    ]

    for i, req in enumerate(responses):
        print(f"\n--- Step {i+1}: {req['user_response']} ---")

        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()

            print(f"Response PNM: {result.get('current_pnm')}")
            print(f"Response Term: {result.get('current_term')}")
            print(f"Question Type: {result.get('question_type')}")
            print(f"Dialogue Mode: {result.get('dialogue_mode')}")

            if result.get('question_text'):
                print(f"Question: {result.get('question_text')[:80]}...")

            # Check conversation state after each step
            conv_response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
            if conv_response.status_code == 200:
                conv = conv_response.json()
                assessment_state = conv.get('assessment_state', {})

                print(f"State: type={conv.get('type')}, dimension={conv.get('dimension')}")

                # Show key UC2 state variables
                term_index = assessment_state.get('Aesthetic_term_index', 'not_set')
                question_index = assessment_state.get('Aesthetic_term_question_index', 'not_set')

                print(f"UC2 State: term_index={term_index}, question_index={question_index}")

                # Show temp scores
                temp_scores = {}
                for key, value in assessment_state.items():
                    if 'temp_scores_Aesthetic' in key:
                        temp_scores[key] = value

                if temp_scores:
                    print(f"Temp scores: {temp_scores}")

            # If we've detected the failure point, analyze what should happen next
            if result.get('current_pnm') != 'Aesthetic' and i == 3:
                print(f"\n❌ FAILURE DETECTED!")
                print(f"Expected: Should move to 'Gaming with adaptive devices' term or generate summary")
                print(f"Actual: Jumped to {result.get('current_pnm')}/{result.get('current_term')}")

                # The Aesthetic dimension has 2 terms:
                # - "Adaptive entertainment controls" (what we just completed)
                # - "Gaming with adaptive devices" (where we should go next)

                print(f"\nAnalysis:")
                print(f"  - We completed 'Adaptive entertainment controls' with 3 answers")
                print(f"  - We should now move to 'Gaming with adaptive devices' term")
                print(f"  - Or if that was the last term, generate summary")
                print(f"  - Instead, system fell back to legacy and went to Physiological")

                break
        else:
            print(f"❌ HTTP Error: {response.status_code} - {response.text}")
            break

    print(f"\n🎯 Conclusion:")
    print(f"The UC2 system fails when transitioning between terms or detecting completion.")
    print(f"This suggests an exception in the term progression logic around line 3327-3340.")

if __name__ == "__main__":
    analyze_aesthetic_completion()