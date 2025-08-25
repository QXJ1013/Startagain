#!/usr/bin/env python3
"""
Test the improved AI routing for ALS Assistant
"""

import requests
import json
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_routing(test_name, user_input, expected_keywords):
    """Test routing for a specific input"""
    print(f"\n=== {test_name} ===")
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"user_response": user_input}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Input: '{user_input}'")
        print(f"Question: {data['question_text'][:100]}...")
        
        # Check session state
        state_resp = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_resp.status_code == 200:
            state = state_resp.json()
            print(f"PNM: {state.get('current_pnm')}")
            print(f"Term: {state.get('current_term')}")
            print(f"Keywords: {state.get('keyword_pool', [])}")
            print(f"Confidence: {state.get('ai_confidence', 0)}")
            print(f"Method: {state.get('routing_method')}")
            
            # Check if expected keywords are in the extracted keywords
            keywords = state.get('keyword_pool', [])
            matches = [kw for kw in expected_keywords if any(kw in k for k in keywords)]
            
            if matches:
                print(f"[OK] Found expected keywords: {matches}")
                return True
            else:
                print(f"[WARN] Expected keywords not found. Expected: {expected_keywords}, Got: {keywords}")
                return False
    else:
        print(f"[FAIL] Request failed: {response.status_code}")
        return False

def test_dimension_routing(dimension):
    """Test dimension-based routing"""
    print(f"\n=== Dimension: {dimension} ===")
    session_id = f"test_dim_{uuid.uuid4().hex[:8]}"
    
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"dimension_focus": dimension}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Question: {data['question_text'][:100]}...")
        
        # Check state
        state_resp = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_resp.status_code == 200:
            state = state_resp.json()
            print(f"PNM: {state.get('current_pnm')}")
            print(f"Term: {state.get('current_term')}")
            
            if state.get('current_pnm') == dimension:
                print(f"[OK] Dimension routing correct")
                return True
            else:
                print(f"[FAIL] Wrong PNM. Expected: {dimension}, Got: {state.get('current_pnm')}")
                return False
    
    return False

def main():
    print("=" * 60)
    print("Testing Improved AI Routing")
    print("=" * 60)
    
    # Test breathing
    test_routing(
        "Breathing Test",
        "I feel breathless at night and need help with breathing exercises",
        ['breath', 'breathing', 'night', 'exercises']
    )
    
    time.sleep(0.5)
    
    # Test speaking
    test_routing(
        "Speaking Test",
        "I have difficulty speaking clearly and communicating with my family",
        ['speak', 'communicat', 'family', 'difficulty']
    )
    
    time.sleep(0.5)
    
    # Test swallowing
    test_routing(
        "Swallowing Test",
        "I have trouble swallowing food and drinks, especially liquids",
        ['swallow', 'food', 'drinks', 'liquids', 'trouble']
    )
    
    time.sleep(0.5)
    
    # Test mobility
    test_routing(
        "Mobility Test",
        "I keep falling when I try to walk and need help with mobility",
        ['fall', 'walk', 'mobility', 'help']
    )
    
    time.sleep(0.5)
    
    # Test fatigue
    test_routing(
        "Fatigue Test",
        "I feel extremely tired all the time and have no energy",
        ['tired', 'energy', 'time', 'extremely']
    )
    
    time.sleep(0.5)
    
    # Test dimensions
    print("\n" + "=" * 60)
    print("Testing Dimension Routing")
    print("=" * 60)
    
    dimensions = [
        'Physiological', 'Safety', 'Love & Belonging', 'Esteem',
        'Self-Actualisation', 'Cognitive', 'Aesthetic', 'Transcendence'
    ]
    
    passed = 0
    for dim in dimensions:
        if test_dimension_routing(dim):
            passed += 1
        time.sleep(0.3)
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Dimension routing: {passed}/{len(dimensions)} passed")
    
    print("\nImproved AI Routing Features:")
    print("1. Keyword expansion from user input")
    print("2. Flexible PNM/term matching")
    print("3. Relevance scoring for question selection")
    print("4. Confidence scoring for routing quality")

if __name__ == "__main__":
    main()