#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug simple scoring flow step by step
"""

import requests
import json
import random

BASE_URL = "http://127.0.0.1:8002"

def test_step_by_step():
    """Test step by step with detailed logging"""
    
    session_id = f"debug-simple-{random.randint(10000, 99999)}"
    
    print(f"Testing step by step: {session_id}")
    print("=" * 50)
    
    # Step 1: Route
    print("Step 1: Route to breathing problem")
    route_resp = requests.post(f"{BASE_URL}/chat/route", 
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have trouble breathing"})
    
    if route_resp.status_code != 200:
        print(f"Route failed: {route_resp.status_code} - {route_resp.text}")
        return
    
    route_data = route_resp.json()
    print(f"  Routed to: {route_data.get('current_pnm')} -> {route_data.get('current_term')}")
    
    # Step 2: Get first question
    print("\nStep 2: Get first question")
    q1_resp = requests.get(f"{BASE_URL}/chat/question", 
        headers={"X-Session-Id": session_id})
    
    if q1_resp.status_code != 200:
        print(f"Q1 failed: {q1_resp.status_code} - {q1_resp.text}")
        return
        
    q1_data = q1_resp.json()
    print(f"  Q1 ID: {q1_data.get('id')}")
    print(f"  Q1 Type: {q1_data.get('type')}")
    print(f"  Q1 Text: {q1_data.get('text', '')[:100]}...")
    
    # Step 3: Answer first question
    print("\nStep 3: Answer first question")
    a1_resp = requests.post(f"{BASE_URL}/chat/answer", 
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "Yes, this is a significant problem", "meta": {"confidence": 4}})
    
    if a1_resp.status_code != 200:
        print(f"A1 failed: {a1_resp.status_code} - {a1_resp.text}")
        return
        
    a1_data = a1_resp.json()
    print(f"  A1 next_state: {a1_data.get('next_state')}")
    
    # Step 4: Get second question
    print("\nStep 4: Get second question")
    q2_resp = requests.get(f"{BASE_URL}/chat/question", 
        headers={"X-Session-Id": session_id})
    
    if q2_resp.status_code != 200:
        print(f"Q2 failed: {q2_resp.status_code} - {q2_resp.text}")
        return
        
    q2_data = q2_resp.json()
    print(f"  Q2 ID: {q2_data.get('id')}")
    print(f"  Q2 Type: {q2_data.get('type')}")
    print(f"  Q2 Text: {q2_data.get('text', '')[:100]}...")
    
    # Step 5: Answer second question
    print("\nStep 5: Answer second question")
    a2_resp = requests.post(f"{BASE_URL}/chat/answer", 
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "Yes, I need help with this", "meta": {"confidence": 4}})
    
    if a2_resp.status_code != 200:
        print(f"A2 failed: {a2_resp.status_code} - {a2_resp.text}")
        return
        
    a2_data = a2_resp.json()
    print(f"  A2 next_state: {a2_data.get('next_state')}")
    
    # Continue until we hit scoring or max attempts
    attempts = 0
    while attempts < 10:
        attempts += 1
        print(f"\nAttempt {attempts}: Getting next question...")
        
        q_resp = requests.get(f"{BASE_URL}/chat/question", 
            headers={"X-Session-Id": session_id})
        
        if q_resp.status_code != 200:
            print(f"Question failed: {q_resp.status_code} - {q_resp.text}")
            break
            
        q_data = q_resp.json()
        print(f"  Question ID: {q_data.get('id')}")
        print(f"  Question Type: {q_data.get('type')}")
        
        # Answer question
        a_resp = requests.post(f"{BASE_URL}/chat/answer", 
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "Yes, significant issue", "meta": {"confidence": 4}})
        
        if a_resp.status_code != 200:
            print(f"Answer failed: {a_resp.status_code} - {a_resp.text}")
            break
            
        a_data = a_resp.json()
        print(f"  Answer next_state: {a_data.get('next_state')}")
        
        if a_data.get('next_state') == 'scored':
            print("  SUCCESS: Scoring achieved!")
            scored = a_data.get('scored')
            if scored:
                print(f"    Score: {scored.get('score_0_7')}/7")
                print(f"    Term: {scored.get('term')}")
            break
        elif a_data.get('next_state') == 'done':
            print("  Flow completed")
            break
            
    # Check final state
    print("\nFinal state check:")
    state_resp = requests.get(f"{BASE_URL}/chat/state", headers={"X-Session-Id": session_id})
    if state_resp.status_code == 200:
        state_data = state_resp.json()
        print(f"  FSM state: {state_data.get('fsm_state')}")
        print(f"  Followup ptr: {state_data.get('followup_ptr')}")
        print(f"  Asked QIDs: {len(state_data.get('asked_qids', []))}")

if __name__ == "__main__":
    test_step_by_step()