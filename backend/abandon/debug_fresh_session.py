#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug fresh session state
"""

import requests
import json
import random

BASE_URL = "http://127.0.0.1:8002"

def test_fresh_session():
    """Test with completely fresh session"""
    
    session_id = f"fresh-{random.randint(100000, 999999)}"
    
    print(f"Testing fresh session: {session_id}")
    print("=" * 50)
    
    # Check initial state
    print("Step 1: Check initial state")
    state_resp = requests.get(f"{BASE_URL}/chat/state", 
        headers={"X-Session-Id": session_id})
    
    if state_resp.status_code == 200:
        state_data = state_resp.json()
        print(f"  Initial FSM state: {state_data.get('fsm_state')}")
        print(f"  Initial current_qid: {state_data.get('current_qid')}")
        print(f"  Initial asked_qids: {state_data.get('asked_qids')}")
    else:
        print(f"  No existing state (expected for fresh session)")
    
    # Route with BIPAP
    print("\nStep 2: Route with BIPAP")
    route_resp = requests.post(f"{BASE_URL}/chat/route", 
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I use a BIPAP machine"})
    
    if route_resp.status_code != 200:
        print(f"Route failed: {route_resp.status_code} - {route_resp.text}")
        return
    
    route_data = route_resp.json()
    print(f"  Routed to: {route_data.get('current_pnm')} -> {route_data.get('current_term')}")
    
    # Check state after routing
    print("\nStep 3: Check state after routing")
    state_resp = requests.get(f"{BASE_URL}/chat/state", 
        headers={"X-Session-Id": session_id})
    
    if state_resp.status_code == 200:
        state_data = state_resp.json()
        print(f"  FSM state: {state_data.get('fsm_state')}")
        print(f"  Current QID: {state_data.get('current_qid')}")
        print(f"  Asked QIDs: {state_data.get('asked_qids')}")
        print(f"  Followup ptr: {state_data.get('followup_ptr')}")
    
    # Get first question
    print("\nStep 4: Get first question")
    q1_resp = requests.get(f"{BASE_URL}/chat/question", 
        headers={"X-Session-Id": session_id})
    
    if q1_resp.status_code != 200:
        print(f"Q1 failed: {q1_resp.status_code} - {q1_resp.text}")
        return
    
    q1_data = q1_resp.json()
    print(f"  Question ID: {q1_data.get('id')}")
    print(f"  Question Type: {q1_data.get('type')}")
    print(f"  Question Text: {q1_data.get('text', '')[:100]}...")
    
    # THIS IS THE KEY QUESTION: Should this be a main question or followup?
    if q1_data.get('type') == 'main':
        print("  SUCCESS: Correctly got main question")
    else:
        print(f"  ERROR: Got {q1_data.get('type')} instead of main question!")
        print("  This explains why we're jumping to followups!")

if __name__ == "__main__":
    test_fresh_session()