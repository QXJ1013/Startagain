#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test to check if a single score gets persisted correctly
"""

import requests
import json
import sys
import time

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def test_single_score():
    """Test a single scoring interaction"""
    
    print("=== SIMPLE SCORING TEST ===")
    
    session_id = "simple-test-123"
    
    # Route first
    print("1. Routing...")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have breathing problems and need help"}
    )
    
    if route_response.status_code == 200:
        print("Routing successful")
    else:
        print(f"Routing failed: {route_response.status_code}")
        return
    
    # Make one response that should trigger scoring
    print("2. Making a response that should be scored...")
    
    conv_response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"user_response": "Yes, I use BiPAP machine for breathing support every night"}
    )
    
    if conv_response.status_code == 200:
        conv_data = conv_response.json()
        print(f"Response processed successfully")
        print(f"Evidence threshold: {conv_data.get('evidence_threshold_met', False)}")
    else:
        print(f"Response failed: {conv_response.status_code}")
        return
    
    # Check session state immediately
    print("3. Checking session state...")
    
    state_response = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        scores_count = state_data.get('pnm_scores_count', 0)
        
        print(f"Session state:")
        print(f"  PNM scores count: {scores_count}")
        print(f"  Current PNM: {state_data.get('current_pnm')}")
        print(f"  Current Term: {state_data.get('current_term')}")
        print(f"  Turn index: {state_data.get('turn_index')}")
        
        if scores_count > 0:
            print("SUCCESS: Score found in session!")
            
            # Try to get the profile
            profile_response = requests.get(
                f"{BASE_URL}/chat/pnm-profile",
                headers={"X-Session-Id": session_id}
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                scores = profile_data.get('scores', [])
                print(f"Profile scores: {len(scores)}")
                if scores:
                    score = scores[0]
                    print(f"  Score: {score.get('pnm_level')}:{score.get('domain')} = {score.get('total_score')}/16 ({score.get('percentage'):.1f}%)")
                    return True
                    
        else:
            print("FAILURE: No scores in session state")
            return False
    else:
        print(f"State check failed: {state_response.status_code}")
        return False

if __name__ == "__main__":
    success = test_single_score()
    print(f"\nResult: {'SUCCESS' if success else 'FAILURE'}")
