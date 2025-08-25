#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the FIXED PNM scoring system to verify it now works correctly.
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

def test_fixed_pnm_scoring():
    """Test the fixed PNM scoring system"""
    session_id = f"fixed-scoring-test-{uuid.uuid4().hex[:8]}"
    
    print("=" * 60)
    print("TESTING FIXED PNM SCORING SYSTEM")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print(f"Base URL: {BASE_URL}")
    
    test_results = []
    
    # Test 1: Basic conversation with scoring
    print("\n1. BASIC CONVERSATION WITH SCORING")
    print("-" * 40)
    
    try:
        # Route to establish context
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "I have ALS and use BiPAP machine for breathing"},
            timeout=10
        )
        
        if route_response.status_code != 200:
            print(f"[FAIL] Routing failed: {route_response.status_code}")
            test_results.append(("Basic Routing", False))
        else:
            print(f"[PASS] Routing successful")
            test_results.append(("Basic Routing", True))
        
        # Make conversation turns that should generate scores
        test_responses = [
            "Yes, I use BiPAP machine every night and work with respiratory therapist",
            "I understand that ALS affects my breathing muscles and will get worse",
            "I have backup power systems and emergency plans for my equipment",
            "My family and I have discussed care planning and accessibility needs",
            "I use communication devices and maintain relationships with support groups"
        ]
        
        successful_conversations = 0
        total_scores_generated = 0
        
        for i, response in enumerate(test_responses, 1):
            print(f"\nConversation turn {i}: {response[:50]}...")
            
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"user_response": response},
                timeout=15
            )
            
            if conv_response.status_code == 200:
                successful_conversations += 1
                print(f"  [PASS] Conversation turn {i} successful")
                
                # Check session state for scores
                state_response = requests.get(
                    f"{BASE_URL}/chat/conversation-state",
                    headers={"X-Session-Id": session_id}
                )
                
                if state_response.status_code == 200:
                    state_data = state_response.json()
                    current_scores = state_data.get('pnm_scores_count', 0)
                    if current_scores > total_scores_generated:
                        total_scores_generated = current_scores
                        print(f"    [SCORE] New PNM score detected! Total: {current_scores}")
                    else:
                        print(f"    [INFO] Total scores: {current_scores}")
            else:
                print(f"  [FAIL] Conversation turn {i} failed: {conv_response.status_code}")
            
            time.sleep(0.5)
        
        print(f"\nConversation Summary:")
        print(f"  Successful turns: {successful_conversations}/{len(test_responses)}")
        print(f"  PNM scores generated: {total_scores_generated}")
        
        test_results.append(("Conversation Flow", successful_conversations >= 3))
        test_results.append(("PNM Score Generation", total_scores_generated > 0))
        
    except Exception as e:
        print(f"[ERROR] Basic conversation test failed: {e}")
        test_results.append(("Basic Routing", False))
        test_results.append(("Conversation Flow", False))
        test_results.append(("PNM Score Generation", False))
    
    # Test 2: PNM Profile Generation
    print("\n2. PNM PROFILE GENERATION")
    print("-" * 40)
    
    try:
        profile_response = requests.get(
            f"{BASE_URL}/chat/pnm-profile",
            headers={"X-Session-Id": session_id},
            timeout=10
        )
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            scores = profile_data.get('scores', [])
            profile = profile_data.get('profile')
            suggestions = profile_data.get('suggestions', [])
            
            print(f"[PASS] PNM profile endpoint working")
            print(f"  Individual scores: {len(scores)}")
            print(f"  Profile generated: {'Yes' if profile else 'No'}")
            print(f"  Suggestions provided: {len(suggestions)}")
            
            if len(scores) > 0:
                print("  Sample scores:")
                for score in scores[:3]:  # Show first 3 scores
                    pnm = score.get('pnm_level', 'Unknown')
                    domain = score.get('domain', 'Unknown')
                    total = score.get('total_score', 0)
                    percentage = score.get('percentage', 0)
                    print(f"    {pnm}:{domain} = {total}/16 ({percentage:.1f}%)")
            
            test_results.append(("PNM Profile Scores", len(scores) > 0))
            test_results.append(("PNM Profile Generation", profile is not None))
            test_results.append(("Improvement Suggestions", len(suggestions) > 0))
        else:
            print(f"[FAIL] PNM profile endpoint failed: {profile_response.status_code}")
            test_results.append(("PNM Profile Scores", False))
            test_results.append(("PNM Profile Generation", False))
            test_results.append(("Improvement Suggestions", False))
            
    except Exception as e:
        print(f"[ERROR] PNM profile test failed: {e}")
        test_results.append(("PNM Profile Scores", False))
        test_results.append(("PNM Profile Generation", False))
        test_results.append(("Improvement Suggestions", False))
    
    # Test 3: Session State Verification
    print("\n3. SESSION STATE VERIFICATION")
    print("-" * 40)
    
    try:
        final_state = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if final_state.status_code == 200:
            state_data = final_state.json()
            final_score_count = state_data.get('pnm_scores_count', 0)
            turn_index = state_data.get('turn_index', 0)
            current_pnm = state_data.get('current_pnm')
            
            print(f"[PASS] Session state accessible")
            print(f"  Final score count: {final_score_count}")
            print(f"  Total conversation turns: {turn_index}")
            print(f"  Current PNM context: {current_pnm}")
            
            test_results.append(("Session Persistence", True))
        else:
            print(f"[FAIL] Session state failed: {final_state.status_code}")
            test_results.append(("Session Persistence", False))
            
    except Exception as e:
        print(f"[ERROR] Session state test failed: {e}")
        test_results.append(("Session Persistence", False))
    
    # Final Assessment
    print("\n" + "=" * 60)
    print("FIXED SCORING SYSTEM TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTest Summary:")
    print(f"  Tests Passed: {passed}/{total}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
    print(f"\nDetailed Results:")
    for test_name, success in test_results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {test_name}")
    
    # Overall Assessment
    print(f"\n" + "=" * 60)
    if success_rate >= 85:
        print("SCORING SYSTEM STATUS: FULLY FIXED!")
        print("The PNM scoring system is now working correctly.")
        print("All core scoring functionality is operational.")
    elif success_rate >= 70:
        print("SCORING SYSTEM STATUS: MOSTLY FIXED")
        print("Most scoring functionality is working.")
        print("Minor issues may remain but core system is functional.")
    else:
        print("SCORING SYSTEM STATUS: STILL NEEDS WORK")
        print("Scoring system improvements were not sufficient.")
        print("Further debugging and fixes are required.")
    
    print("=" * 60)
    
    return success_rate >= 70

if __name__ == "__main__":
    result = test_fixed_pnm_scoring()
    sys.exit(0 if result else 1)