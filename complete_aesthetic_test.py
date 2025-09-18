#!/usr/bin/env python3
"""
Complete all Aesthetic questions to trigger summary
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def complete_aesthetic_assessment():
    print("🎯 Complete Aesthetic Assessment Test")

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
        "title": "Complete Assessment"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    # Complete assessment systematically
    # Aesthetic has 2 terms with ~3 questions each = ~6 total questions
    answers = ["Start", "answer1", "answer2", "answer3", "answer4", "answer5", "answer6", "answer7", "answer8"]

    for i, answer in enumerate(answers):
        print(f"\n--- Answer {i+1}: {answer} ---")

        if i == 0:
            req = {"user_response": answer, "dimension_focus": "Aesthetic"}
        else:
            req = {"user_response": answer}

        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            response_type = result.get('question_type', 'unknown')
            current_pnm = result.get('current_pnm', 'unknown')
            current_term = result.get('current_term', 'unknown')

            print(f"Response: type={response_type}, PNM={current_pnm}, term={current_term}")

            if response_type == 'summary':
                print(f"\n🎉 SUMMARY GENERATED!")
                print(f"Summary text: {result.get('question_text', '')[:100]}...")

                # Check conversation status immediately
                conv_response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
                conv = conv_response.json()
                print(f"Conversation status: {conv.get('status')}")

                # Check for completion timestamp
                assessment_state = conv.get('assessment_state', {})
                completed_at = assessment_state.get('completed_at')
                conversation_locked = assessment_state.get('conversation_locked')

                print(f"Completed at: {completed_at}")
                print(f"Conversation locked: {conversation_locked}")

                # Check database for scores
                print(f"\n🔍 Checking database scores...")
                import sqlite3
                try:
                    conn = sqlite3.connect('backend/app/data/als.db')
                    scores = conn.execute(
                        "SELECT * FROM conversation_scores WHERE conversation_id = ?",
                        (conv_id,)
                    ).fetchall()

                    if scores:
                        print(f"✅ Found {len(scores)} scores in database:")
                        for score in scores:
                            print(f"   - {score[1]}/{score[2]}: {score[3]}")
                    else:
                        print(f"❌ No scores found in database")

                    conn.close()
                except Exception as e:
                    print(f"❌ Database check failed: {e}")

                break

            # If we've been going for a while and still no summary, something's wrong
            if i >= 8 and response_type != 'summary':
                print(f"\n❌ No summary after {i+1} answers - checking conversation state")
                conv_response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
                conv = conv_response.json()
                assessment_state = conv.get('assessment_state', {})

                print(f"Assessment state keys: {list(assessment_state.keys())}")
                for key, value in assessment_state.items():
                    if 'Aesthetic' in key or 'temp_scores' in key or 'completed' in key:
                        print(f"   {key}: {value}")
                break

        else:
            print(f"❌ Request failed: {response.text}")
            break

if __name__ == "__main__":
    complete_aesthetic_assessment()