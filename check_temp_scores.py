#!/usr/bin/env python3
"""
检查temp scores是否保留（表明存储失败）
"""
import requests

BASE_URL = "http://localhost:8000"

def check_temp_scores():
    print("🔍 检查Temp Scores状态")

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
        "title": "Temp Scores Check"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    print(f"✅ Created conversation: {conv_id}")

    # Answer a few questions to accumulate temp scores
    answers = [
        {"user_response": "Start", "dimension_focus": "Aesthetic"},
        {"user_response": "guided"},
        {"user_response": "partial"},
        {"user_response": "independent"},  # This should complete first term
    ]

    for i, req in enumerate(answers):
        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            current_term = result.get('current_term', 'unknown')

            print(f"Answer {i+1}: term={current_term}")

            # Check conversation state after each answer
            conv_response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
            if conv_response.status_code == 200:
                conv = conv_response.json()
                assessment_state = conv.get('assessment_state', {})

                # Check for any temp scores
                temp_scores = {}
                for key, value in assessment_state.items():
                    if 'temp_scores' in key:
                        temp_scores[key] = value

                if temp_scores:
                    print(f"   Temp scores: {temp_scores}")
                else:
                    print(f"   No temp scores")

            # If we switched to Gaming term, check if previous term scores remain
            if current_term == "Gaming with adaptive devices":
                print(f"\n🎯 Term切换detected! 检查前一个term的temp scores状态:")

                # Check for adaptive entertainment controls scores
                adaptive_scores = assessment_state.get('temp_scores_Aesthetic_Adaptive entertainment controls')
                if adaptive_scores:
                    print(f"❌ 前一个term的temp scores仍然存在: {adaptive_scores}")
                    print(f"   这说明数据库存储失败了!")
                else:
                    print(f"✅ 前一个term的temp scores已清除")
                    print(f"   这说明数据库存储成功了!")

                break

if __name__ == "__main__":
    check_temp_scores()