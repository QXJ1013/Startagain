#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the fixed PNM scoring system
"""

import requests
import json
import sys
import time

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def test_scoring_fix():
    """Test that PNM scores are now being persisted correctly"""
    
    print("=== TESTING FIXED PNM SCORING PERSISTENCE ===")
    
    session_id = "test-scoring-fix"
    
    # Step 1: Route to start conversation
    print("1. Initial routing...")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have respiratory issues and use breathing equipment"}
    )
    
    if route_response.status_code != 200:
        print(f"Routing failed: {route_response.status_code}")
        return
    
    print("Routing successful")
    
    # Step 2: Make a response that should trigger scoring
    print("\n2. Making response that should trigger scoring...")
    conv_response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"user_response": "Yes, I use BiPAP machine every night and practice diaphragmatic breathing exercises daily"}
    )
    
    if conv_response.status_code == 200:
        conv_data = conv_response.json()
        print(f"Response processed successfully")
        print(f"Evidence threshold met: {conv_data.get('evidence_threshold_met', False)}")
        print(f"Info cards provided: {len(conv_data.get('info_cards', []) or [])}")
    else:
        print(f"Conversation failed: {conv_response.status_code}")
        return
    
    # Step 3: Check session state immediately
    print("\n3. Checking session state...")
    state_response = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        scores_count = state_data.get('pnm_scores_count', 0)
        print(f"PNM scores count in session: {scores_count}")
        
        if scores_count > 0:
            print("✓ SUCCESS: Scores are being persisted!")
        else:
            print("✗ ISSUE: No scores found in session state")
            
        print(f"Current context: {state_data.get('current_pnm')} -> {state_data.get('current_term')}")
        print(f"Turn index: {state_data.get('turn_index')}")
    else:
        print(f"State check failed: {state_response.status_code}")
        return
    
    # Step 4: Try to get PNM profile
    print("\n4. Checking PNM profile...")
    profile_response = requests.get(
        f"{BASE_URL}/chat/pnm-profile",
        headers={"X-Session-Id": session_id}
    )
    
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        scores = profile_data.get('scores', [])
        profile = profile_data.get('profile')
        
        print(f"Profile scores: {len(scores)}")
        
        if scores:
            print("✓ SUCCESS: Profile contains scores!")
            for score in scores:
                print(f"  {score.get('pnm_level')}:{score.get('domain')} = {score.get('total_score')} ({score.get('percentage', 0):.1f}%)")
        else:
            print("✗ ISSUE: No scores in profile")
            
        if profile:
            print("✓ SUCCESS: PNM awareness profile generated!")
        else:
            print("✗ ISSUE: No PNM awareness profile")
    else:
        print(f"Profile check failed: {profile_response.status_code}")

if __name__ == "__main__":
    test_scoring_fix()