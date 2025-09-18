#!/usr/bin/env python3
"""
UC1 Scoring Quick Test
Test only the scoring mechanism in UC1 flow
"""
import requests
import time

BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test-token-user1"
}

def test_uc1_scoring():
    print("🧪 UC1 Scoring Quick Test")
    print("=" * 40)

    # Step 1: Authentication
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": "test_uc1@example.com",
            "password": "testpassword123"
        }
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False

    token_data = login_response.json()
    access_token = token_data.get('access_token')
    HEADERS["Authorization"] = f"Bearer {access_token}"
    print("✅ Authentication successful")

    # Step 2: Start conversation and trigger diagonal
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers=HEADERS,
        json={
            "user_response": "Please assess my current condition",
            "dimension_focus": None,
            "request_info": True
        }
    )

    if response.status_code != 200:
        print(f"❌ Failed to trigger assessment: {response.status_code}")
        return False

    data = response.json()
    conversation_id = data.get('conversation_id')
    dialogue_mode = data.get('dialogue_mode', True)

    print(f"✅ Assessment triggered: dialogue_mode={dialogue_mode}")
    print(f"   Options: {len(data.get('options', []))}")
    print(f"   PNM: {data.get('current_pnm')}")
    print(f"   Term: {data.get('current_term')}")

    if dialogue_mode:
        print("⚠️  Still in dialogue mode, trying explicit assessment trigger...")
        return False

    # Step 3: Answer question to test scoring
    print("\n📊 Testing scoring with answer '1'")
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={**HEADERS, "X-Conversation-Id": conversation_id},
        json={
            "user_response": "1",
            "dimension_focus": None,
            "request_info": False
        }
    )

    if response.status_code != 200:
        print(f"❌ Failed to answer question: {response.status_code}")
        return False

    # Step 4: Check scores in database
    print("\n💾 Checking database scores...")
    response = requests.get(
        f"{BASE_URL}/conversations/scores/summary?conversation_id={conversation_id}",
        headers=HEADERS
    )

    if response.status_code == 200:
        scores_data = response.json()
        term_scores = scores_data.get('term_scores', [])
        print(f"✅ Found {len(term_scores)} scores in database")

        for score in term_scores:
            pnm = score.get('pnm', 'Unknown')
            term = score.get('term', 'Unknown')
            score_val = score.get('score_0_7', 'N/A')
            method = score.get('scoring_method', 'unknown')
            print(f"   📊 {pnm}/{term}: {score_val} (method: {method})")

        return len(term_scores) > 0
    else:
        print(f"❌ Failed to retrieve scores: {response.status_code}")
        return False

if __name__ == "__main__":
    time.sleep(2)  # Wait for server
    success = test_uc1_scoring()

    if success:
        print("\n🎉 UC1 SCORING TEST: SUCCESS")
    else:
        print("\n❌ UC1 SCORING TEST: FAILED")