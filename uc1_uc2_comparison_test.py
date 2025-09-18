#!/usr/bin/env python3
"""
UC1 vs UC2 详细对比测试
分析问题选择逻辑、评分机制、数据库存储的差异
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test-token-user1"
}

def authenticate():
    """统一认证"""
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": "test_comparison@example.com",
            "password": "testpassword123"
        }
    )

    if login_response.status_code == 200:
        token_data = login_response.json()
        access_token = token_data.get('access_token')
        HEADERS["Authorization"] = f"Bearer {access_token}"
        return True
    return False

def test_uc1_question_generation():
    """测试UC1问题生成逻辑"""
    print("\n🧪 UC1 问题生成测试")
    print("=" * 40)

    # 触发UC1对话并激活diagonal trigger
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers=HEADERS,
        json={
            "user_response": "I have ALS symptoms and need help",
            "dimension_focus": None,  # UC1: No dimension focus
            "request_info": True
        }
    )

    if response.status_code != 200:
        print(f"❌ UC1初始对话失败: {response.status_code}")
        return None

    conv_data = response.json()
    conversation_id = conv_data.get('conversation_id')

    # 明确触发评估模式
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={**HEADERS, "X-Conversation-Id": conversation_id},
        json={
            "user_response": "Please assess my current condition now",
            "dimension_focus": None,
            "request_info": False
        }
    )

    if response.status_code != 200:
        print(f"❌ UC1评估触发失败: {response.status_code}")
        return None

    assessment_data = response.json()

    # 分析UC1问题特征
    uc1_analysis = {
        "conversation_id": conversation_id,
        "dialogue_mode": assessment_data.get('dialogue_mode'),
        "question_type": assessment_data.get('question_type'),
        "current_pnm": assessment_data.get('current_pnm'),
        "current_term": assessment_data.get('current_term'),
        "options_count": len(assessment_data.get('options', [])),
        "question_text": assessment_data.get('question_text', '')[:100] + "...",
        "options": assessment_data.get('options', [])[:2]  # 前两个选项
    }

    print(f"✅ UC1评估模式激活:")
    print(f"   对话模式: {uc1_analysis['dialogue_mode']}")
    print(f"   问题类型: {uc1_analysis['question_type']}")
    print(f"   PNM: {uc1_analysis['current_pnm']}")
    print(f"   Term: {uc1_analysis['current_term']}")
    print(f"   选项数量: {uc1_analysis['options_count']}")
    print(f"   问题文本: {uc1_analysis['question_text']}")

    return uc1_analysis

def test_uc2_question_generation():
    """测试UC2问题生成逻辑"""
    print("\n🧪 UC2 问题生成测试")
    print("=" * 40)

    # 直接创建UC2维度评估
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers=HEADERS,
        json={
            "user_response": "",
            "dimension_focus": "Physiological",  # UC2: 明确维度
            "request_info": True
        }
    )

    if response.status_code != 200:
        print(f"❌ UC2评估创建失败: {response.status_code}")
        return None

    assessment_data = response.json()

    # 分析UC2问题特征
    uc2_analysis = {
        "conversation_id": assessment_data.get('conversation_id'),
        "dialogue_mode": assessment_data.get('dialogue_mode'),
        "question_type": assessment_data.get('question_type'),
        "current_pnm": assessment_data.get('current_pnm'),
        "current_term": assessment_data.get('current_term'),
        "options_count": len(assessment_data.get('options', [])),
        "question_text": assessment_data.get('question_text', '')[:100] + "...",
        "options": assessment_data.get('options', [])[:2]  # 前两个选项
    }

    print(f"✅ UC2评估模式:")
    print(f"   对话模式: {uc2_analysis['dialogue_mode']}")
    print(f"   问题类型: {uc2_analysis['question_type']}")
    print(f"   PNM: {uc2_analysis['current_pnm']}")
    print(f"   Term: {uc2_analysis['current_term']}")
    print(f"   选项数量: {uc2_analysis['options_count']}")
    print(f"   问题文本: {uc2_analysis['question_text']}")

    return uc2_analysis

def test_scoring_comparison(uc1_data, uc2_data):
    """对比UC1和UC2的评分机制"""
    print("\n🧪 UC1 vs UC2 评分对比测试")
    print("=" * 45)

    # UC1评分测试
    print("\n📊 UC1评分测试:")
    if uc1_data and uc1_data['conversation_id']:
        response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={**HEADERS, "X-Conversation-Id": uc1_data['conversation_id']},
            json={
                "user_response": "1",  # 选择第一个选项
                "dimension_focus": None,
                "request_info": False
            }
        )

        if response.status_code == 200:
            # 检查UC1评分存储
            time.sleep(1)  # 等待数据库写入
            scores_response = requests.get(
                f"{BASE_URL}/conversations/scores/summary?conversation_id={uc1_data['conversation_id']}",
                headers=HEADERS
            )

            if scores_response.status_code == 200:
                uc1_scores = scores_response.json().get('term_scores', [])
                print(f"   UC1评分记录: {len(uc1_scores)}个")
                for score in uc1_scores:
                    print(f"   📊 {score.get('pnm')}/{score.get('term')}: {score.get('score_0_7')} (方法: {score.get('scoring_method')})")
            else:
                print(f"   ❌ UC1评分获取失败: {scores_response.status_code}")
        else:
            print(f"   ❌ UC1回答失败: {response.status_code}")

    # UC2评分测试
    print("\n📊 UC2评分测试:")
    if uc2_data and uc2_data['conversation_id']:
        response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={**HEADERS, "X-Conversation-Id": uc2_data['conversation_id']},
            json={
                "user_response": "partial",  # UC2典型选项
                "dimension_focus": "Physiological",
                "request_info": False
            }
        )

        if response.status_code == 200:
            # 检查UC2评分存储
            time.sleep(1)  # 等待数据库写入
            scores_response = requests.get(
                f"{BASE_URL}/conversations/scores/summary?conversation_id={uc2_data['conversation_id']}",
                headers=HEADERS
            )

            if scores_response.status_code == 200:
                uc2_scores = scores_response.json().get('term_scores', [])
                print(f"   UC2评分记录: {len(uc2_scores)}个")
                for score in uc2_scores:
                    print(f"   📊 {score.get('pnm')}/{score.get('term')}: {score.get('score_0_7')} (方法: {score.get('scoring_method')})")
            else:
                print(f"   ❌ UC2评分获取失败: {scores_response.status_code}")
        else:
            print(f"   ❌ UC2回答失败: {response.status_code}")

def analyze_differences(uc1_data, uc2_data):
    """分析UC1与UC2的关键差异"""
    print("\n📋 UC1 vs UC2 差异分析")
    print("=" * 35)

    print("🔍 问题选择逻辑差异:")
    print(f"   UC1: AI智能选择PNM/Term (选择了 {uc1_data.get('current_pnm', 'N/A')}/{uc1_data.get('current_term', 'N/A')})")
    print(f"   UC2: 指定维度遍历 (固定维度 {uc2_data.get('current_pnm', 'N/A')}/{uc2_data.get('current_term', 'N/A')})")

    print("\n🔍 触发方式差异:")
    print(f"   UC1: 对话模式 → 对角触发 → 评估模式")
    print(f"   UC2: 直接进入评估模式 (dimension_focus)")

    print("\n🔍 问题库使用:")
    print(f"   UC1: 限制3个问题用于单term评估")
    print(f"   UC2: 遍历指定维度的所有问题")

    print("\n🔍 评分策略:")
    print(f"   UC1: 单term完成 → 快速summary")
    print(f"   UC2: 完整维度遍历 → 维度summary")

def main():
    print("🧪 UC1 vs UC2 完整对比分析")
    print("=" * 50)

    # 认证
    if not authenticate():
        print("❌ 认证失败")
        return

    print("✅ 认证成功")

    # 测试UC1问题生成
    uc1_data = test_uc1_question_generation()

    # 测试UC2问题生成
    uc2_data = test_uc2_question_generation()

    # 评分对比测试
    test_scoring_comparison(uc1_data, uc2_data)

    # 差异分析
    if uc1_data and uc2_data:
        analyze_differences(uc1_data, uc2_data)

    print("\n🎉 UC1 vs UC2 对比分析完成")

if __name__ == "__main__":
    time.sleep(2)  # 等待服务器
    main()