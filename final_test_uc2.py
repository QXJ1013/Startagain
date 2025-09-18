#!/usr/bin/env python3
"""
Final test of UC2 complete flow after all fixes
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_uc2_complete_flow():
    print("🎯 Final UC2 Complete Flow Test")

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

    # Create fresh conversation for complete test
    response = requests.post(f"{BASE_URL}/conversations", json={
        "type": "dimension",
        "dimension": "Aesthetic",
        "title": "Final Complete Test"
    }, headers=headers)

    if response.status_code != 200:
        print("❌ Conversation creation failed")
        return

    conv_id = response.json()["id"]
    print(f"✅ Created conversation: {conv_id}")

    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    # Complete a full Aesthetic dimension assessment
    # This should trigger term completion and final scores
    responses = [
        {"user_response": "Start assessment", "dimension_focus": "Aesthetic"},
        {"user_response": "guided"},  # Score 6
        {"user_response": "partial"},  # Score 4
        {"user_response": "independent"},  # Score 2
        {"user_response": "none"},  # Score 7
        {"user_response": "guided"},  # Score 6
        {"user_response": "partial"},  # Score 4
        {"user_response": "continue assessment"},  # Keep going
        {"user_response": "independent"},  # Score 2
        {"user_response": "mentor"},  # Score 0
        {"user_response": "guided"},  # Score 6
    ]

    conversation_completed = False

    for i, req in enumerate(responses):
        print(f"\n--- Request {i+1}: {req['user_response']} ---")

        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response type: {result.get('question_type')}")
            print(f"   Current PNM: {result.get('current_pnm')}")
            print(f"   Current term: {result.get('current_term')}")

            # Check if we got a summary (conversation completed)
            if result.get('question_type') == 'summary':
                print(f"🎉 SUMMARY RECEIVED - Conversation should be completed!")
                conversation_completed = True
                break

        else:
            print(f"❌ Request failed: {response.text}")

        time.sleep(0.5)  # Small delay between requests

    # Final verification
    print(f"\n🔍 Final Verification...")

    # 1. Check conversation status
    response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
    if response.status_code == 200:
        conv = response.json()
        print(f"✅ Conversation status: {conv.get('status')}")

        if conv.get('status') == 'completed':
            print(f"✅ Conversation correctly marked as completed!")
        else:
            print(f"❌ Conversation status should be 'completed' but is '{conv.get('status')}'")

        # Check temp scores and final scores
        assessment_state = conv.get('assessment_state', {})
        temp_scores = {}
        final_scores = assessment_state.get('scores', {})

        for key, value in assessment_state.items():
            if 'temp_scores_' in key:
                temp_scores[key] = value

        print(f"   Temp scores: {temp_scores}")
        print(f"   Final scores: {final_scores}")

    # 2. Check database for stored scores
    print(f"\n💾 Database Check...")
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

    # 3. Check scores API
    print(f"\n📊 Scores API Check...")
    response = requests.get(f"{BASE_URL}/conversations/scores/summary", headers=headers)
    if response.status_code == 200:
        scores_data = response.json()
        print(f"   Total conversations: {scores_data.get('total_conversations')}")
        print(f"   Completed assessments: {scores_data.get('completed_assessments')}")

        aesthetic_scores = [d for d in scores_data.get('dimensions', []) if d['name'] == 'Aesthetic']
        if aesthetic_scores:
            aesthetic = aesthetic_scores[0]
            print(f"   Aesthetic dimension: score={aesthetic['score']}, assessments={aesthetic['assessments_count']}")

            if aesthetic['assessments_count'] > 0:
                print(f"✅ Aesthetic scores found in API!")
            else:
                print(f"❌ No Aesthetic assessments in API")

    print(f"\n🎉 Final UC2 Test Completed")
    return conversation_completed

if __name__ == "__main__":
    test_uc2_complete_flow()