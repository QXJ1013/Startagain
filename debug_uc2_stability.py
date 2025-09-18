#!/usr/bin/env python3
"""
调试UC2稳定性问题
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def debug_uc2_stability():
    print("🔍 调试UC2系统稳定性")

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
        "title": "UC2 Stability Debug"
    }, headers=headers)

    conv_id = response.json()["id"]
    chat_headers = {**headers, "X-Conversation-Id": conv_id}

    print(f"✅ Created conversation: {conv_id}")

    # Test with exact option IDs that should work
    test_inputs = [
        {"user_response": "Start", "dimension_focus": "Aesthetic"},
        {"user_response": "guided"},  # Should match score 6
        {"user_response": "partial"}, # Should match score 4
        {"user_response": "independent"}, # Should match score 2
        {"user_response": "mentor"},  # Should match score 0
        {"user_response": "guided"}   # Should match score 6
    ]

    consistent_count = 0
    fallback_count = 0

    for i, req in enumerate(test_inputs):
        print(f"\n--- Test {i+1}: {req['user_response']} ---")

        response = requests.post(f"{BASE_URL}/chat/conversation", json=req, headers=chat_headers)

        if response.status_code == 200:
            result = response.json()
            response_type = result.get('question_type', 'unknown')
            current_pnm = result.get('current_pnm', 'unknown')
            current_term = result.get('current_term', 'unknown')

            print(f"Response: type={response_type}, PNM={current_pnm}, term={current_term}")

            # 检查是否是UC2响应
            if current_pnm == 'Aesthetic' and response_type == 'assessment':
                consistent_count += 1
                print(f"✅ UC2系统正常工作")
            else:
                fallback_count += 1
                print(f"❌ UC2系统fallback: type={response_type}, PNM={current_pnm}")

            # 检查对话状态
            conv_response = requests.get(f"{BASE_URL}/conversations/{conv_id}", headers=headers)
            if conv_response.status_code == 200:
                conv = conv_response.json()
                assessment_state = conv.get('assessment_state', {})

                # 查看temp scores
                temp_scores = {}
                for key, value in assessment_state.items():
                    if 'temp_scores_Aesthetic' in key:
                        temp_scores[key] = value

                if temp_scores:
                    print(f"   Temp scores: {temp_scores}")
                else:
                    print(f"   No temp scores found")

        else:
            print(f"❌ HTTP Error: {response.status_code}")
            fallback_count += 1

    print(f"\n📊 稳定性统计:")
    print(f"   UC2正常工作: {consistent_count} 次")
    print(f"   Fallback发生: {fallback_count} 次")
    print(f"   稳定性: {consistent_count}/{consistent_count + fallback_count} = {consistent_count/(consistent_count + fallback_count)*100:.1f}%")

    if consistent_count > fallback_count:
        print(f"✅ UC2系统基本稳定")
        return True
    else:
        print(f"❌ UC2系统不稳定，需要进一步修复")
        return False

if __name__ == "__main__":
    debug_uc2_stability()