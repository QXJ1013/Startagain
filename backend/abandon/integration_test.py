#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前后端集成测试
确保API接口正常工作并且数据流完整
"""
import requests
import json
import sys

API_BASE = "http://localhost:8000"
SESSION_ID = "integration-test-session"

def headers():
    return {
        "Content-Type": "application/json",
        "X-Session-Id": SESSION_ID
    }

def test_backend_health():
    """测试后端健康检查"""
    print("=== 1. 测试后端健康检查 ===")
    try:
        response = requests.get(f"{API_BASE}/health/readyz")
        response.raise_for_status()
        data = response.json()
        print(f"[SUCCESS] 健康检查通过: {data['status']}")
        return True
    except Exception as e:
        print(f"[FAILED] 健康检查失败: {e}")
        return False

def test_conversation_start():
    """测试对话开始"""
    print("\n=== 2. 测试对话开始 ===")
    try:
        response = requests.post(
            f"{API_BASE}/chat/conversation",
            headers=headers(),
            json={}
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ 对话开始成功")
        print(f"  问题类型: {data['question_type']}")
        print(f"  问题文本: {data['question_text'][:50]}...")
        print(f"  选项数量: {len(data['options'])}")
        print(f"  当前PNM: {data.get('current_pnm', 'None')}")
        return data
    except Exception as e:
        print(f"✗ 对话开始失败: {e}")
        return None

def test_user_response(question_data):
    """测试用户响应处理"""
    print("\n=== 3. 测试用户响应处理 ===")
    try:
        # 模拟用户选择第一个选项
        user_response = "I have a comprehensive emergency plan that I review regularly with my family"
        
        response = requests.post(
            f"{API_BASE}/chat/conversation",
            headers=headers(),
            json={"user_response": user_response}
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ 用户响应处理成功")
        print(f"  下一个问题类型: {data['question_type']}")
        print(f"  FSM状态: {data.get('fsm_state', 'Unknown')}")
        print(f"  证据阈值是否达到: {data.get('evidence_threshold_met', False)}")
        return data
    except Exception as e:
        print(f"✗ 用户响应处理失败: {e}")
        return None

def test_followup_response(question_data):
    """测试跟进问题响应"""
    print("\n=== 4. 测试跟进问题响应 ===")
    try:
        user_response = "We practice emergency drills monthly and have backup equipment ready"
        
        response = requests.post(
            f"{API_BASE}/chat/conversation",
            headers=headers(),
            json={"user_response": user_response}
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ 跟进响应处理成功")
        print(f"  问题类型: {data['question_type']}")
        print(f"  证据阈值: {data.get('evidence_threshold_met', False)}")
        return data
    except Exception as e:
        print(f"✗ 跟进响应处理失败: {e}")
        return None

def test_pnm_profile():
    """测试PNM评分档案"""
    print("\n=== 5. 测试PNM评分档案 ===")
    try:
        response = requests.get(
            f"{API_BASE}/chat/pnm-profile",
            headers=headers()
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ PNM档案获取成功")
        
        if data.get('profile'):
            profile = data['profile']
            if 'overall' in profile:
                overall = profile['overall']
                print(f"  总体评分: {overall.get('percentage', 0):.1f}%")
                print(f"  评估水平: {overall.get('level', 'Unknown')}")
                print(f"  已评估维度: {overall.get('domains_assessed', 0)}")
            else:
                print("  档案数据不包含总体评分")
        else:
            print("  暂无档案数据（正常，需要更多对话）")
        
        print(f"  建议数量: {len(data.get('suggestions', []))}")
        print(f"  评分记录: {len(data.get('scores', []))}")
        return data
    except Exception as e:
        print(f"✗ PNM档案获取失败: {e}")
        return None

def test_conversation_state():
    """测试会话状态"""
    print("\n=== 6. 测试会话状态 ===")
    try:
        response = requests.get(
            f"{API_BASE}/chat/conversation-state",
            headers=headers()
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ 会话状态获取成功")
        
        session_state = data.get('session_state', {})
        print(f"  会话ID: {session_state.get('session_id', 'Unknown')}")
        print(f"  当前PNM: {session_state.get('current_pnm', 'None')}")
        print(f"  当前术语: {session_state.get('current_term', 'None')}")
        print(f"  FSM状态: {session_state.get('fsm_state', 'Unknown')}")
        print(f"  轮次索引: {session_state.get('turn_index', 0)}")
        
        return data
    except Exception as e:
        print(f"✗ 会话状态获取失败: {e}")
        return None

def run_integration_test():
    """运行完整集成测试"""
    print("ALS Assistant - 前后端集成测试")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 6
    
    # 1. 健康检查
    if test_backend_health():
        tests_passed += 1
    
    # 2. 开始对话
    first_question = test_conversation_start()
    if first_question:
        tests_passed += 1
    
    # 3. 用户响应
    second_question = None
    if first_question:
        second_question = test_user_response(first_question)
        if second_question:
            tests_passed += 1
    
    # 4. 跟进响应
    if second_question:
        third_question = test_followup_response(second_question)
        if third_question:
            tests_passed += 1
    
    # 5. PNM档案
    if test_pnm_profile():
        tests_passed += 1
    
    # 6. 会话状态
    if test_conversation_state():
        tests_passed += 1
    
    print(f"\n测试结果: {tests_passed}/{total_tests} 通过")
    
    if tests_passed == total_tests:
        print("所有集成测试通过 - 前后端功能完整!")
        return True
    else:
        print("部分测试失败 - 需要检查集成问题")
        return False

if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)