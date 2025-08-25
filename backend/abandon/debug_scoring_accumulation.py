#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug PNM scoring accumulation issue
"""

import requests
import json
import sys
import time

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def debug_scoring_accumulation():
    """Debug why PNM scores are not accumulating"""
    
    print("=== DEBUGGING PNM SCORING ACCUMULATION ===")
    
    session_id = "debug-accumulation-test"
    
    # Step 1: Route and start conversation
    print("1. INITIAL SETUP")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have breathing difficulties"}
    )
    
    print(f"Routing: {route_response.status_code}")
    
    # Check state after routing
    state_response = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        print(f"After routing - PNM scores: {state_data.get('pnm_scores_count')}")
    
    print("\n2. PROGRESSIVE SCORING TEST")
    print("-" * 50)
    
    # Make several responses and check accumulation after each
    responses = [
        "Yes, I have severe breathing problems every night",
        "I wake up gasping for air frequently", 
        "I'm using BiPAP machine for ventilatory support",
        "I practice breathing exercises daily with my therapist",
        "I monitor my oxygen levels regularly"
    ]
    
    for i, response in enumerate(responses, 1):
        print(f"\nResponse {i}: {response[:50]}...")
        
        # Make conversation call
        conv_response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"user_response": response}
        )
        
        if conv_response.status_code == 200:
            conv_data = conv_response.json()
            print(f"  Evidence threshold: {conv_data.get('evidence_threshold_met')}")
            print(f"  Info cards: {len(conv_data.get('info_cards', []) or [])}")
            
            # Check session state immediately after each response
            state_response = requests.get(
                f"{BASE_URL}/chat/conversation-state",
                headers={"X-Session-Id": session_id}
            )
            
            if state_response.status_code == 200:
                state_data = state_response.json()
                scores_count = state_data.get('pnm_scores_count', 0)
                print(f"  PNM scores count: {scores_count}")
                print(f"  Current PNM: {state_data.get('current_pnm')}")
                print(f"  Current Term: {state_data.get('current_term')}")
                print(f"  Turn index: {state_data.get('turn_index')}")
                
                # If we have scores, try to get profile
                if scores_count > 0:
                    profile_response = requests.get(
                        f"{BASE_URL}/chat/pnm-profile",
                        headers={"X-Session-Id": session_id}
                    )
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        profile_scores = profile_data.get('scores', [])
                        print(f"  Profile scores: {len(profile_scores)}")
                        
                        if profile_scores:
                            last_score = profile_scores[-1]
                            print(f"    Latest score: {last_score.get('domain')} = {last_score.get('total_score')} ({last_score.get('percentage'):.1f}%)")
                    else:
                        print(f"  Profile error: {profile_response.status_code}")
            
            # Small delay to ensure processing
            time.sleep(0.5)
        else:
            print(f"  Conversation error: {conv_response.status_code}")
            if conv_response.text:
                print(f"  Error details: {conv_response.text[:200]}")
    
    print("\n3. FINAL STATE CHECK")
    print("-" * 50)
    
    # Final comprehensive check
    final_state = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if final_state.status_code == 200:
        final_data = final_state.json()
        print("Final session state:")
        for key, value in final_data.items():
            print(f"  {key}: {value}")
    
    # Try to get all PNM scores
    final_profile = requests.get(
        f"{BASE_URL}/chat/pnm-profile",
        headers={"X-Session-Id": session_id}
    )
    
    if final_profile.status_code == 200:
        profile_data = final_profile.json()
        scores = profile_data.get('scores', [])
        print(f"\nFinal PNM Profile:")
        print(f"  Total scores: {len(scores)}")
        print(f"  Has profile: {profile_data.get('profile') is not None}")
        
        if scores:
            print("  Score details:")
            for score in scores:
                print(f"    {score.get('pnm_level')}:{score.get('domain')} = {score.get('total_score')}/{score.get('max_score', 16)} ({score.get('percentage'):.1f}%)")
        else:
            print("  No scores in profile!")
    else:
        print(f"Final profile error: {final_profile.status_code}")

def check_single_scoring_call():
    """Test a single scoring call in isolation"""
    
    print("\n=== SINGLE SCORING CALL TEST ===")
    
    session_id = "single-scoring-test"
    
    # Setup
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I practice breathing exercises"}
    )
    
    print(f"Setup routing: {route_response.status_code}")
    
    # Single conversation call
    conv_response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"user_response": "Yes, I practice diaphragmatic breathing daily"}
    )
    
    if conv_response.status_code == 200:
        conv_data = conv_response.json()
        print(f"Conversation successful")
        print(f"Evidence threshold: {conv_data.get('evidence_threshold_met')}")
        
        # Check state
        state_response = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            print(f"PNM scores after single call: {state_data.get('pnm_scores_count')}")
            print(f"Current context: {state_data.get('current_pnm')} -> {state_data.get('current_term')}")
        
    else:
        print(f"Single call failed: {conv_response.status_code}")

if __name__ == "__main__":
    debug_scoring_accumulation()
    check_single_scoring_call()