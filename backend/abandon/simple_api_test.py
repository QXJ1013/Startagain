#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple API test for critical functions
"""

import requests
import json
import sys
import time
import uuid

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def simple_api_test():
    """Simple test of API functionality"""
    session_id = f"simple-api-{uuid.uuid4().hex[:6]}"
    print(f"=== Simple API Test ===")
    print(f"Session: {session_id}")
    
    # Test 1: Health check via question bank
    print("\n1. Health Check...")
    try:
        qb_response = requests.get(f"{BASE_URL}/chat/debug-question-bank")
        if qb_response.status_code == 200:
            qb_data = qb_response.json()
            print(f"  [PASS] Question Bank: {qb_data.get('total_questions', 0)} questions")
        else:
            print(f"  [FAIL] Question Bank: HTTP {qb_response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Question Bank error: {e}")
        return False
    
    # Test 2: Routing
    print("\n2. Testing routing...")
    try:
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "I need help with breathing problems from ALS"}
        )
        
        if route_response.status_code == 200:
            route_data = route_response.json()
            print(f"  [PASS] Routing successful")
            print(f"    PNM: {route_data.get('pnm', 'Not specified')}")
            print(f"    Term: {route_data.get('term', 'Not specified')}")
        else:
            print(f"  [FAIL] Routing: HTTP {route_response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Routing error: {e}")
        return False
    
    # Test 3: Basic conversation
    print("\n3. Testing conversation...")
    success_count = 0
    total_info_cards = 0
    
    responses = [
        "Yes, I have severe breathing difficulties",
        "I use a BiPAP machine for ventilatory support",
        "I work with respiratory therapists"
    ]
    
    for i, response in enumerate(responses, 1):
        try:
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"user_response": response}
            )
            
            if conv_response.status_code == 200:
                conv_data = conv_response.json()
                success_count += 1
                
                # Count info cards
                info_cards = conv_data.get('info_cards', []) or []
                total_info_cards += len(info_cards)
                
                print(f"  Round {i}: {conv_data.get('question_type', 'unknown')} question")
                if info_cards:
                    print(f"    Info cards: {len(info_cards)}")
            else:
                print(f"  [FAIL] Round {i}: HTTP {conv_response.status_code}")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  [FAIL] Round {i} error: {e}")
    
    print(f"  [RESULT] Conversation: {success_count}/{len(responses)} rounds successful")
    print(f"  [RESULT] Info cards: {total_info_cards} total generated")
    
    # Test 4: Session state
    print("\n4. Testing session state...")
    try:
        state_response = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            print(f"  [PASS] Session state retrieved")
            print(f"    Turn index: {state_data.get('turn_index', 0)}")
            print(f"    Current PNM: {state_data.get('current_pnm', 'None')}")
            print(f"    Current Term: {state_data.get('current_term', 'None')}")
            print(f"    PNM scores: {state_data.get('pnm_scores_count', 0)}")
            print(f"    Asked questions: {len(state_data.get('asked_qids', []))}")
        else:
            print(f"  [FAIL] Session state: HTTP {state_response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Session state error: {e}")
        return False
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    
    core_functions = [
        ("Question Bank Access", True),
        ("Routing System", True),
        ("Conversation Flow", success_count >= 2),
        ("Info Card Generation", total_info_cards > 0),
        ("Session Management", True)
    ]
    
    passed = sum(1 for _, success in core_functions if success)
    total = len(core_functions)
    success_rate = (passed / total * 100)
    
    print(f"Core Functions Test Results:")
    for function_name, success in core_functions:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {function_name}")
    
    print(f"\nOverall: {passed}/{total} core functions working ({success_rate:.0f}%)")
    
    if success_rate >= 80:
        print("\n[SUCCESS] Core system functions are operational!")
        print("The ALS Assistant backend is functional for basic use.")
        return True
    else:
        print(f"\n[WARNING] Only {success_rate:.0f}% of core functions working")
        print("Some critical issues need to be addressed.")
        return False

if __name__ == "__main__":
    result = simple_api_test()
    if result:
        print("\n✓ Basic API functionality test PASSED")
    else:
        print("\n✗ Basic API functionality test FAILED")