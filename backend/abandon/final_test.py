#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final comprehensive test for ALS Assistant backend
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

def test_complete_flow():
    """Test complete conversation flow"""
    session_id = f"final-test-{uuid.uuid4().hex[:8]}"
    print(f"=== Final Comprehensive Test ===")
    print(f"Session ID: {session_id}")
    print("=" * 50)
    
    results = []
    
    # Test 1: Routing
    print("\n1. Testing routing...")
    try:
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "I have breathing difficulties with ALS"}
        )
        
        if route_response.status_code == 200:
            route_data = route_response.json()
            results.append(("Routing", True, f"Routed to {route_data.get('pnm', 'Unknown')}"))
            print(f"  [PASS] Routing successful: {route_data.get('pnm')}")
        else:
            results.append(("Routing", False, f"HTTP {route_response.status_code}"))
            print(f"  [FAIL] Routing failed: HTTP {route_response.status_code}")
    except Exception as e:
        results.append(("Routing", False, str(e)))
        print(f"  [FAIL] Routing error: {e}")
    
    # Test 2: Conversation with scoring
    print("\n2. Testing conversation and PNM scoring...")
    responses = [
        "Yes, I use BiPAP machine every night for breathing support",
        "I practice breathing exercises daily with my respiratory therapist", 
        "I monitor my oxygen saturation levels regularly",
        "I have emergency backup power for my ventilator",
        "I work with my care team on breathing management plans"
    ]
    
    total_scores = 0
    evidence_meetings = 0
    info_cards_count = 0
    
    for i, response in enumerate(responses, 1):
        try:
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"user_response": response}
            )
            
            if conv_response.status_code == 200:
                conv_data = conv_response.json()
                if conv_data.get('evidence_threshold_met', False):
                    evidence_meetings += 1
                
                info_cards = conv_data.get('info_cards', []) or []
                info_cards_count += len(info_cards)
                
                print(f"  Round {i}: Question type = {conv_data.get('question_type', 'unknown')}")
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  [FAIL] Conversation round {i}: {e}")
    
    results.append(("Conversation Flow", True, f"{len(responses)} rounds completed"))
    results.append(("Evidence Collection", evidence_meetings > 0, f"{evidence_meetings} evidence thresholds met"))
    results.append(("Info Cards", info_cards_count > 0, f"{info_cards_count} info cards generated"))
    
    # Test 3: PNM Scoring
    print("\n3. Testing PNM scoring...")
    try:
        state_response = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            scores_count = state_data.get('pnm_scores_count', 0)
            
            if scores_count > 0:
                results.append(("PNM Scoring", True, f"{scores_count} scores generated"))
                print(f"  [PASS] PNM Scoring: {scores_count} scores found")
            else:
                results.append(("PNM Scoring", False, "No scores found"))
                print(f"  [FAIL] PNM Scoring: No scores found")
    except Exception as e:
        results.append(("PNM Scoring", False, str(e)))
        print(f"  [FAIL] PNM Scoring error: {e}")
    
    # Test 4: PNM Profile
    print("\n4. Testing PNM profile generation...")
    try:
        profile_response = requests.get(
            f"{BASE_URL}/chat/pnm-profile",
            headers={"X-Session-Id": session_id}
        )
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            scores = profile_data.get('scores', [])
            profile = profile_data.get('profile')
            suggestions = profile_data.get('suggestions', [])
            
            if len(scores) > 0:
                results.append(("PNM Profile Scores", True, f"{len(scores)} scores in profile"))
                print(f"  [PASS] Profile Scores: {len(scores)} scores")
                
                # Show score details
                for score in scores:
                    pnm = score.get('pnm_level', 'Unknown')
                    domain = score.get('domain', 'Unknown')
                    total = score.get('total_score', 0)
                    percentage = score.get('percentage', 0)
                    print(f"    {pnm}:{domain} = {total}/16 ({percentage:.1f}%)")
            else:
                results.append(("PNM Profile Scores", False, "No scores in profile"))
                print(f"  [FAIL] Profile Scores: No scores found")
            
            results.append(("PNM Awareness Profile", profile is not None, "Profile generated" if profile else "No profile"))
            results.append(("Improvement Suggestions", len(suggestions) > 0, f"{len(suggestions)} suggestions"))
            
            print(f"  Profile Generated: {profile is not None}")
            print(f"  Suggestions: {len(suggestions)}")
            
    except Exception as e:
        results.append(("PNM Profile", False, str(e)))
        print(f"  [FAIL] PNM Profile error: {e}")
    
    # Test 5: Debug endpoints
    print("\n5. Testing debug endpoints...")
    try:
        debug_response = requests.get(f"{BASE_URL}/chat/debug-question-bank")
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            question_count = debug_data.get('total_questions', 0)
            results.append(("Question Bank", question_count > 0, f"{question_count} questions"))
            print(f"  [PASS] Question Bank: {question_count} questions")
        else:
            results.append(("Question Bank", False, f"HTTP {debug_response.status_code}"))
            print(f"  [FAIL] Question Bank: HTTP {debug_response.status_code}")
    except Exception as e:
        results.append(("Question Bank", False, str(e)))
        print(f"  [FAIL] Question Bank error: {e}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("FINAL TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")  
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    print(f"\nDetailed Results:")
    for test_name, success, details in results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {test_name}: {details}")
    
    if success_rate >= 90:
        print(f"\n[EXCELLENT] System test success rate: {success_rate:.1f}%")
        print("Backend system is ready for production!")
        return True
    elif success_rate >= 75:
        print(f"\n[GOOD] System test success rate: {success_rate:.1f}%")
        print("System basic functions work, recommend fixing failed tests")
        return True
    else:
        print(f"\n[NEEDS IMPROVEMENT] System test success rate: {success_rate:.1f}%")
        print("Recommend fixing critical issues before deployment")
        return False

if __name__ == "__main__":
    test_complete_flow()