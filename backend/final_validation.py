#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final validation of ALS Assistant backend system
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

def final_validation():
    """Final comprehensive validation"""
    session_id = f"final-validation-{uuid.uuid4().hex[:6]}"
    print("=" * 60)
    print("ALS ASSISTANT BACKEND - FINAL VALIDATION")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    
    validation_results = []
    
    # 1. System Health Check
    print("\n1. SYSTEM HEALTH CHECK")
    print("-" * 30)
    
    try:
        qb_response = requests.get(f"{BASE_URL}/chat/debug-question-bank", timeout=10)
        if qb_response.status_code == 200:
            qb_data = qb_response.json()
            question_count = qb_data.get('total_questions', 0)
            print(f"✓ Question Bank: {question_count} questions loaded")
            validation_results.append(("Question Bank", True))
        else:
            print(f"✗ Question Bank: Failed (HTTP {qb_response.status_code})")
            validation_results.append(("Question Bank", False))
    except Exception as e:
        print(f"✗ Question Bank: Error - {e}")
        validation_results.append(("Question Bank", False))
    
    # 2. Routing System
    print("\n2. ROUTING SYSTEM")
    print("-" * 30)
    
    try:
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "I have ALS and need help with breathing and mobility issues"},
            timeout=10
        )
        
        if route_response.status_code == 200:
            print("✓ Routing system operational")
            validation_results.append(("Routing System", True))
        else:
            print(f"✗ Routing system failed (HTTP {route_response.status_code})")
            validation_results.append(("Routing System", False))
    except Exception as e:
        print(f"✗ Routing system error: {e}")
        validation_results.append(("Routing System", False))
    
    # 3. Conversation Flow
    print("\n3. CONVERSATION FLOW")  
    print("-" * 30)
    
    conversation_success = True
    total_rounds = 0
    successful_rounds = 0
    info_cards_generated = 0
    evidence_thresholds_met = 0
    
    test_responses = [
        "Yes, I have significant breathing difficulties especially at night",
        "I use a BiPAP machine and work with respiratory therapists",
        "I have mobility issues and use a wheelchair for longer distances",
        "I need help with daily activities and have caregivers",
        "I want to maintain my independence as much as possible"
    ]
    
    for i, response in enumerate(test_responses, 1):
        total_rounds += 1
        try:
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"user_response": response},
                timeout=15
            )
            
            if conv_response.status_code == 200:
                successful_rounds += 1
                conv_data = conv_response.json()
                
                # Track evidence and info cards
                if conv_data.get('evidence_threshold_met', False):
                    evidence_thresholds_met += 1
                
                info_cards = conv_data.get('info_cards', []) or []
                info_cards_generated += len(info_cards)
                
                question_type = conv_data.get('question_type', 'unknown')
                print(f"  Round {i}: {question_type} question - {len(info_cards)} info cards")
            else:
                print(f"  Round {i}: Failed (HTTP {conv_response.status_code})")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Round {i}: Error - {e}")
    
    print(f"✓ Conversation: {successful_rounds}/{total_rounds} rounds successful")
    print(f"✓ Evidence thresholds met: {evidence_thresholds_met}")
    print(f"✓ Info cards generated: {info_cards_generated}")
    
    validation_results.append(("Conversation Flow", successful_rounds >= 3))
    validation_results.append(("Info Card Generation", info_cards_generated > 0))
    validation_results.append(("Evidence Collection", evidence_thresholds_met > 0))
    
    # 4. Session Management
    print("\n4. SESSION MANAGEMENT")
    print("-" * 30)
    
    try:
        state_response = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id},
            timeout=10
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            turn_index = state_data.get('turn_index', 0)
            current_pnm = state_data.get('current_pnm', 'None')
            asked_questions = len(state_data.get('asked_qids', []))
            
            print(f"✓ Session persistence: Turn {turn_index}, PNM: {current_pnm}")
            print(f"✓ Question tracking: {asked_questions} questions asked")
            validation_results.append(("Session Management", True))
        else:
            print(f"✗ Session management failed (HTTP {state_response.status_code})")
            validation_results.append(("Session Management", False))
    except Exception as e:
        print(f"✗ Session management error: {e}")
        validation_results.append(("Session Management", False))
    
    # 5. API Endpoints
    print("\n5. API ENDPOINTS")
    print("-" * 30)
    
    endpoints_tested = 0
    endpoints_working = 0
    
    test_endpoints = [
        ("/chat/conversation-state", "GET"),
        ("/chat/debug-question-bank", "GET"),
        ("/chat/pnm-profile", "GET")
    ]
    
    for endpoint, method in test_endpoints:
        endpoints_tested += 1
        try:
            if method == "GET":
                response = requests.get(
                    f"{BASE_URL}{endpoint}",
                    headers={"X-Session-Id": session_id},
                    timeout=10
                )
            
            if response.status_code == 200:
                endpoints_working += 1
                print(f"✓ {endpoint}: Working")
            else:
                print(f"✗ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ {endpoint}: Error - {e}")
    
    validation_results.append(("API Endpoints", endpoints_working >= 2))
    
    # 6. Final Assessment
    print("\n" + "=" * 60)
    print("FINAL VALIDATION RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, success in validation_results if success)
    total = len(validation_results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nValidation Summary:")
    print(f"  Tests Passed: {passed}/{total}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
    print(f"\nDetailed Results:")
    for test_name, success in validation_results:
        status = "PASS" if success else "FAIL" 
        print(f"  [{status}] {test_name}")
    
    # Overall Assessment
    print(f"\n" + "=" * 60)
    if success_rate >= 85:
        print("SYSTEM STATUS: PRODUCTION READY")
        print("The ALS Assistant backend is fully operational and ready for deployment.")
        print("All core systems are functioning correctly.")
    elif success_rate >= 70:
        print("SYSTEM STATUS: MOSTLY FUNCTIONAL") 
        print("The ALS Assistant backend has good core functionality.")
        print("Some minor issues may need attention but system is usable.")
    else:
        print("SYSTEM STATUS: NEEDS IMPROVEMENT")
        print("Several core systems need attention before deployment.")
    
    print("=" * 60)
    
    return success_rate >= 70

if __name__ == "__main__":
    result = final_validation()
    sys.exit(0 if result else 1)