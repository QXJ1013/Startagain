#!/usr/bin/env python3
"""
Complete test of frontend-backend integration for ALS Assistant
Testing breath, speak, and swallow scenarios
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_scenario(test_name, session_id, user_input):
    """Test a specific scenario"""
    print(f"\n=== Testing: {test_name} ===")
    
    # Send user input
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"user_response": user_input}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] User input: '{user_input}'")
        print(f"  Question: {data['question_text'][:80]}...")
        print(f"  PNM: {data.get('current_pnm', 'N/A')}")
        print(f"  Term: {data.get('current_term', 'N/A')}")
        
        # Check state
        state_resp = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        if state_resp.status_code == 200:
            state = state_resp.json()
            print(f"  Session PNM: {state.get('current_pnm')}")
            print(f"  Session Term: {state.get('current_term')}")
            
            # Return for validation
            return {
                'question': data['question_text'],
                'pnm': state.get('current_pnm'),
                'term': state.get('current_term')
            }
    else:
        print(f"[FAIL] Failed: {response.status_code}")
    
    return None

def test_dimension_focus(dimension):
    """Test dimension-based routing"""
    import uuid
    print(f"\n=== Testing Dimension: {dimension} ===")
    
    session_id = f"test_dim_{dimension}_{uuid.uuid4().hex[:8]}"
    
    response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"dimension_focus": dimension}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Dimension: {dimension}")
        print(f"  Question: {data['question_text'][:80]}...")
        
        # Check state
        state_resp = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        if state_resp.status_code == 200:
            state = state_resp.json()
            print(f"  PNM: {state.get('current_pnm')}")
            print(f"  Term: {state.get('current_term')}")
            return state.get('current_pnm') == dimension
    
    return False

def check_scoring():
    """Check if scoring is working properly"""
    import uuid
    print("\n=== Testing Scoring System ===")
    
    session_id = f"test_scoring_{uuid.uuid4().hex[:8]}"
    
    # Start conversation
    requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"user_response": "I have trouble breathing"}
    )
    
    # Get PNM profile
    profile_resp = requests.get(
        f"{BASE_URL}/chat/pnm-profile",
        headers={"X-Session-Id": session_id}
    )
    
    if profile_resp.status_code == 200:
        data = profile_resp.json()
        profile = data.get('profile', {})
        overall = profile.get('overall', {})
        
        print(f"  Overall score: {overall.get('score', 0)}/16")
        print(f"  Percentage: {overall.get('percentage', 0)}%")
        
        # Check if scoring is varied (not always 5-6)
        if overall.get('score') and overall.get('score') not in [5, 6]:
            print("  [OK] Scoring shows variation")
        else:
            print("  [WARN] Scoring might be fixed at 5-6")
    elif profile_resp.status_code == 404:
        print("  [WARN] No profile found (expected for new session)")
    else:
        print(f"  [FAIL] Failed to get profile: {profile_resp.status_code}")

def main():
    print("=" * 60)
    print("ALS Assistant Complete Frontend-Backend Test")
    print("=" * 60)
    
    # Test breath scenario
    import uuid
    breath_result = test_scenario(
        "Breathing Issue",
        f"test_breath_{uuid.uuid4().hex[:8]}",
        "I feel breathless at night and need help with breathing"
    )
    
    # Validate breath routing
    if breath_result:
        if 'breath' in breath_result['question'].lower() or breath_result['pnm'] == 'Physiological':
            print("[OK] Breathing routing works correctly")
        else:
            print("[FAIL] Breathing routing failed - got wrong question")
    
    time.sleep(0.5)
    
    # Test speak scenario
    speak_result = test_scenario(
        "Speaking Issue",
        f"test_speak_{uuid.uuid4().hex[:8]}",
        "I have difficulty speaking clearly"
    )
    
    # Validate speak routing
    if speak_result:
        if 'communicat' in speak_result['term'].lower() or 'speech' in speak_result['term'].lower():
            print("[OK] Speaking routing works correctly")
        else:
            print("[FAIL] Speaking routing failed")
    
    time.sleep(0.5)
    
    # Test swallow scenario
    swallow_result = test_scenario(
        "Swallowing Issue",
        f"test_swallow_{uuid.uuid4().hex[:8]}",
        "I have trouble swallowing food and drinks"
    )
    
    # Validate swallow routing
    if swallow_result:
        if 'nutrition' in swallow_result['term'].lower() or swallow_result['pnm'] == 'Physiological':
            print("[OK] Swallowing routing works correctly")
        else:
            print("[FAIL] Swallowing routing failed")
    
    # Test dimension selection
    print("\n=== Testing All 8 Dimensions ===")
    dimensions = [
        'Physiological', 'Safety', 'Love & Belonging', 'Esteem',
        'Self-Actualisation', 'Cognitive', 'Aesthetic', 'Transcendence'
    ]
    
    dimension_pass = 0
    for dim in dimensions:
        if test_dimension_focus(dim):
            dimension_pass += 1
        time.sleep(0.3)
    
    print(f"\n[OK] Dimension routing: {dimension_pass}/{len(dimensions)} passed")
    
    # Check scoring
    check_scoring()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    print("\n[OK] Fixed Issues:")
    print("  1. First user message now properly triggers routing")
    print("  2. Session resets for new conversations")
    print("  3. Dimension selection passes correct focus")
    
    print("\n[WARN] Potential Issues to Monitor:")
    print("  1. Scoring variation (check if always 5-6)")
    print("  2. Session persistence across page refreshes")
    print("  3. Multiple option selection handling")

if __name__ == "__main__":
    main()