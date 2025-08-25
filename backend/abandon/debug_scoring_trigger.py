#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug why PNM scoring is not being triggered
"""

import requests
import json
import sys
import time

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8003"

def debug_scoring_trigger():
    """Debug the scoring trigger mechanism"""
    session_id = "debug-scoring-trigger"
    
    print("=== DEBUGGING PNM SCORING TRIGGER ===")
    print(f"Session: {session_id}")
    print(f"Base URL: {BASE_URL}")
    
    try:
        # Step 1: Route to establish PNM/term context
        print("\n1. ROUTING TO ESTABLISH CONTEXT")
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "I have severe breathing problems and use BiPAP machine"},
            timeout=10
        )
        
        if route_response.status_code != 200:
            print(f"[FAIL] Routing failed: {route_response.status_code}")
            if route_response.text:
                print(f"  Error: {route_response.text}")
            return False
        
        route_data = route_response.json()
        print(f"[PASS] Routing successful")
        print(f"  PNM: {route_data.get('pnm', 'Not set')}")
        print(f"  Term: {route_data.get('term', 'Not set')}")
        
        # Step 2: Check initial session state
        print("\n2. CHECKING INITIAL SESSION STATE")
        state_response = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            print(f"[PASS] Initial session state retrieved")
            print(f"  Session ID: {state_data.get('session_id')}")
            print(f"  Current PNM: {state_data.get('current_pnm', 'None')}")
            print(f"  Current Term: {state_data.get('current_term', 'None')}")
            print(f"  Turn Index: {state_data.get('turn_index', 0)}")
            print(f"  PNM Scores: {state_data.get('pnm_scores_count', 0)}")
        else:
            print(f"[FAIL] Cannot get session state: {state_response.status_code}")
            return False
        
        # Step 3: Make a scoring-eligible response
        print("\n3. MAKING SCORING-ELIGIBLE RESPONSE")
        
        # This should be a high-scoring response based on the PNM scoring criteria
        scoring_response = "Yes, I use BiPAP machine every night effectively, I monitor my oxygen saturation daily, I work closely with my respiratory therapist on breathing management, and I have backup power systems for my ventilation equipment"
        
        print(f"Response: {scoring_response[:80]}...")
        
        conv_response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"user_response": scoring_response},
            timeout=15
        )
        
        if conv_response.status_code != 200:
            print(f"[FAIL] Conversation failed: {conv_response.status_code}")
            if conv_response.text:
                print(f"  Error: {conv_response.text[:200]}")
            return False
        
        conv_data = conv_response.json()
        print(f"[PASS] Conversation response received")
        print(f"  Question type: {conv_data.get('question_type', 'unknown')}")
        print(f"  Evidence threshold met: {conv_data.get('evidence_threshold_met', False)}")
        
        # Step 4: Check session state after response
        print("\n4. CHECKING SESSION STATE AFTER RESPONSE")
        state_response2 = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response2.status_code == 200:
            state_data2 = state_response2.json()
            scores_after = state_data2.get('pnm_scores_count', 0)
            turn_after = state_data2.get('turn_index', 0)
            
            print(f"[INFO] Session state after response:")
            print(f"  Turn Index: {state_data.get('turn_index', 0)} -> {turn_after}")
            print(f"  PNM Scores: {state_data.get('pnm_scores_count', 0)} -> {scores_after}")
            print(f"  Current PNM: {state_data2.get('current_pnm', 'None')}")
            print(f"  Current Term: {state_data2.get('current_term', 'None')}")
            
            if scores_after > 0:
                print(f"[SUCCESS] PNM scoring is working! {scores_after} scores found")
                return True
            else:
                print(f"[ISSUE] No PNM scores generated despite conversation")
        else:
            print(f"[FAIL] Cannot get updated session state: {state_response2.status_code}")
        
        # Step 5: Try PNM profile endpoint
        print("\n5. CHECKING PNM PROFILE ENDPOINT")
        profile_response = requests.get(
            f"{BASE_URL}/chat/pnm-profile",
            headers={"X-Session-Id": session_id}
        )
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            scores = profile_data.get('scores', [])
            profile = profile_data.get('profile')
            
            print(f"[INFO] PNM Profile endpoint response:")
            print(f"  Scores in profile: {len(scores)}")
            print(f"  Profile object exists: {profile is not None}")
            
            if len(scores) > 0:
                print(f"[SUCCESS] Found {len(scores)} scores in profile!")
                for score in scores:
                    print(f"    {score.get('pnm_level')}:{score.get('domain')} = {score.get('total_score', 0)}/16")
                return True
        else:
            print(f"[FAIL] PNM profile endpoint failed: {profile_response.status_code}")
        
        print(f"\n[CONCLUSION] PNM scoring appears to NOT be working")
        print("Possible issues:")
        print("- Scoring logic not triggered")
        print("- Session context missing")
        print("- Database persistence failing")
        print("- Scoring criteria not met")
        
        return False
        
    except Exception as e:
        print(f"[ERROR] Debug test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    result = debug_scoring_trigger()
    
    print(f"\n{'='*50}")
    if result:
        print("RESULT: PNM SCORING IS WORKING!")
    else:
        print("RESULT: PNM SCORING NEEDS DEBUGGING")
    print(f"{'='*50}")
    
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)