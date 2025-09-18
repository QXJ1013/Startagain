#!/usr/bin/env python3
"""
Debug script to check conversation creation and state
"""

import requests
import json

# API配置
BASE_URL = "http://localhost:8000"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"

# 测试用户
TEST_EMAIL = "debug_user@example.com"
TEST_PASSWORD = "testpassword123"

def get_auth_token():
    """获取认证token"""
    # 尝试登录
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }

    try:
        login_response = requests.post(f"{AUTH_ENDPOINT}/login", json=login_data)
        if login_response.status_code == 200:
            result = login_response.json()
            return result.get('access_token')
    except:
        pass

    # 注册新用户
    register_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "display_name": "Debug User"
    }

    try:
        register_response = requests.post(f"{AUTH_ENDPOINT}/register", json=register_data)
        if register_response.status_code == 201:
            result = register_response.json()
            return result.get('access_token')
    except Exception as e:
        print(f"❌ 认证失败: {e}")
        return None

def debug_conversation_creation():
    """测试对话创建"""
    token = get_auth_token()
    if not token:
        print("❌ 无法获取token")
        return

    print("🔍 Debug: 测试对话创建")

    # 测试1: 无dimension_focus的普通对话
    payload1 = {
        "user_response": "Hello, I need help with ALS",
        "user_id": "debug_user"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("\n1️⃣ 测试普通对话创建（无dimension_focus）")
    response1 = requests.post(f"{BASE_URL}/chat/conversation", json=payload1, headers=headers)
    print(f"状态码: {response1.status_code}")

    if response1.status_code == 200:
        data1 = response1.json()
        print(f"对话ID: {data1.get('conversation_id')}")
        print(f"对话模式: {data1.get('dialogue_mode')}")
        print(f"当前维度: {data1.get('current_pnm')}")
        print(f"问题类型: {data1.get('question_type')}")
    else:
        print(f"错误: {response1.text}")

    # 测试2: 有dimension_focus的维度评估
    payload2 = {
        "user_response": "Start physiological assessment",
        "user_id": "debug_user",
        "dimension_focus": "Physiological"
    }

    print("\n2️⃣ 测试维度评估创建（有dimension_focus）")
    response2 = requests.post(f"{BASE_URL}/chat/conversation", json=payload2, headers=headers)
    print(f"状态码: {response2.status_code}")

    if response2.status_code == 200:
        data2 = response2.json()
        print(f"对话ID: {data2.get('conversation_id')}")
        print(f"对话模式: {data2.get('dialogue_mode')}")
        print(f"当前维度: {data2.get('current_pnm')}")
        print(f"问题类型: {data2.get('question_type')}")
    else:
        print(f"错误: {response2.text}")

if __name__ == "__main__":
    debug_conversation_creation()