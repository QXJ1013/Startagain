#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug PROMPT-052 specifically
"""

import requests
import json
import random

BASE_URL = "http://127.0.0.1:8002"

def test_ventilatory_support():
    """Test ventilatory support routing (PROMPT-052)"""
    
    session_id = f"debug-vent-{random.randint(10000, 99999)}"
    
    print(f"Testing ventilatory support: {session_id}")
    print("=" * 50)
    
    # Try ventilatory support specific terms
    test_phrases = [
        "I use a BIPAP machine",
        "I need ventilator support", 
        "I have a tracheostomy",
        "non-invasive ventilation"
    ]
    
    for phrase in test_phrases:
        print(f"\nTesting phrase: '{phrase}'")
        
        # Route
        route_resp = requests.post(f"{BASE_URL}/chat/route", 
            headers={"X-Session-Id": f"{session_id}-{hash(phrase)}", "Content-Type": "application/json"},
            json={"text": phrase})
        
        if route_resp.status_code == 200:
            route_data = route_resp.json()
            print(f"  Routed to: {route_data.get('current_pnm')} -> {route_data.get('current_term')}")
            
            # Get question
            q_resp = requests.get(f"{BASE_URL}/chat/question", 
                headers={"X-Session-Id": f"{session_id}-{hash(phrase)}"})
            
            if q_resp.status_code == 200:
                q_data = q_resp.json()
                print(f"  Question ID: {q_data.get('id')}")
                if q_data.get('id') == 'PROMPT-052':
                    print("  FOUND PROMPT-052!")
                    # Test this one fully
                    return test_prompt_052_flow(f"{session_id}-{hash(phrase)}")
            else:
                print(f"  Question failed: {q_resp.status_code}")
        else:
            print(f"  Route failed: {route_resp.status_code}")
    
    print("\nNo phrase successfully routed to PROMPT-052")
    return False

def test_prompt_052_flow(session_id):
    """Test the full PROMPT-052 flow"""
    
    print(f"\n=== Testing PROMPT-052 Full Flow ===")
    
    # Answer first question
    print("Answering first question...")
    a1_resp = requests.post(f"{BASE_URL}/chat/answer", 
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I use it every night", "meta": {"confidence": 4}})
    
    if a1_resp.status_code != 200:
        print(f"A1 failed: {a1_resp.status_code} - {a1_resp.text}")
        return False
    
    a1_data = a1_resp.json()
    print(f"A1 next_state: {a1_data.get('next_state')}")
    
    # Get second question 
    print("Getting second question...")
    q2_resp = requests.get(f"{BASE_URL}/chat/question", 
        headers={"X-Session-Id": session_id})
    
    if q2_resp.status_code != 200:
        print(f"Q2 failed: {q2_resp.status_code} - {q2_resp.text}")
        return False
    
    q2_data = q2_resp.json()
    print(f"Q2 ID: {q2_data.get('id')}")
    
    # Answer second question - THIS IS WHERE THE ERROR SHOULD HAPPEN
    print("Answering second question...")
    a2_resp = requests.post(f"{BASE_URL}/chat/answer", 
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I can manage most tasks", "meta": {"confidence": 4}})
    
    if a2_resp.status_code != 200:
        print(f"A2 failed: {a2_resp.status_code} - {a2_resp.text}")
        print("THIS IS THE ERROR WE'RE DEBUGGING!")
        return False
    
    print("A2 succeeded!")
    return True

if __name__ == "__main__":
    test_ventilatory_support()