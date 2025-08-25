#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed debugging of PNM scoring system
"""

import requests
import json
import sys
import time

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def debug_scoring_system():
    """Debug the complete scoring flow step by step"""
    
    print("=== DETAILED PNM SCORING SYSTEM DEBUG ===")
    
    session_id = "debug-scoring-detailed"
    
    print("1. INITIAL SETUP")
    print("-" * 40)
    
    # Step 1: Route user input
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have severe breathing problems"}
    )
    
    if route_response.status_code == 200:
        route_data = route_response.json()
        print(f"Routed to PNM: {route_data.get('current_pnm')}")
        print(f"Routed to Term: {route_data.get('current_term')}")
    else:
        print(f"Routing failed: {route_response.status_code}")
        return
    
    # Check initial session state
    state_response = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        print(f"Initial session state:")
        print(f"  PNM: {state_data.get('current_pnm')}")
        print(f"  Term: {state_data.get('current_term')}")
        print(f"  Turn index: {state_data.get('turn_index')}")
        print(f"  Evidence count: {state_data.get('evidence_count')}")
        print(f"  PNM scores count: {state_data.get('pnm_scores_count')}")
    
    print("\n2. EVIDENCE BUILDING PHASE")
    print("-" * 40)
    
    # Build evidence with expert responses
    expert_responses = [
        "Yes, I practice diaphragmatic breathing daily and use my BiPAP at night",
        "I work closely with my respiratory therapist on lung function monitoring", 
        "I monitor my oxygen levels and adjust my ventilatory support as needed",
        "I have a comprehensive breathing plan with multiple backup strategies"
    ]
    
    for i, response in enumerate(expert_responses, 1):
        print(f"\nTurn {i}: {response[:60]}...")
        
        conv_response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"user_response": response}
        )
        
        if conv_response.status_code == 200:
            conv_data = conv_response.json()
            evidence_met = conv_data.get('evidence_threshold_met', False)
            info_cards = conv_data.get('info_cards', []) or []
            
            print(f"  Evidence threshold met: {evidence_met}")
            print(f"  Info cards generated: {len(info_cards)}")
            
            # Check session state after each turn
            state_response = requests.get(
                f"{BASE_URL}/chat/conversation-state",
                headers={"X-Session-Id": session_id}
            )
            
            if state_response.status_code == 200:
                state_data = state_response.json()
                print(f"  Turn index: {state_data.get('turn_index')}")
                print(f"  Evidence count: {state_data.get('evidence_count')}")
                print(f"  PNM scores count: {state_data.get('pnm_scores_count')}")
                print(f"  Current QID: {state_data.get('current_qid')}")
                print(f"  FSM state: {state_data.get('fsm_state', 'Not available')}")
                
                # Check if scoring was triggered
                if state_data.get('pnm_scores_count', 0) > 0:
                    print("  --> SCORING WAS TRIGGERED!")
                    break
            
            # If evidence threshold is met, let's see what happens next
            if evidence_met:
                print("  --> Evidence threshold met, checking if scoring occurs...")
                time.sleep(1)  # Give system time to process
        else:
            print(f"  Conversation error: {conv_response.status_code}")
            if conv_response.status_code == 500:
                print(f"  Error details: {conv_response.text}")
    
    print("\n3. FINAL SCORING CHECK")
    print("-" * 40)
    
    # Check final state
    final_state_response = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if final_state_response.status_code == 200:
        final_state = final_state_response.json()
        print(f"Final session state:")
        for key, value in final_state.items():
            print(f"  {key}: {value}")
    
    # Try to get PNM profile
    print("\n4. PNM PROFILE CHECK")
    print("-" * 40)
    
    profile_response = requests.get(
        f"{BASE_URL}/chat/pnm-profile",
        headers={"X-Session-Id": session_id}
    )
    
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        print(f"Profile exists: {profile_data.get('profile') is not None}")
        print(f"Scores count: {len(profile_data.get('scores', []))}")
        print(f"Suggestions count: {len(profile_data.get('suggestions', []))}")
        
        if profile_data.get('scores'):
            print("Scores found:")
            for score in profile_data.get('scores', []):
                print(f"  Domain: {score.get('domain')}")
                print(f"  Awareness: {score.get('awareness_score')}")
                print(f"  Total: {score.get('total_score')}")
    else:
        print(f"Profile request failed: {profile_response.status_code}")
    
    print("\n5. DIRECT SCORING TEST")
    print("-" * 40)
    
    # Try triggering scoring directly if possible
    # This helps identify if the issue is in the trigger mechanism
    try:
        # Make one more conversation call to see if anything changes
        final_response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"user_response": "I want to continue with the assessment"}
        )
        
        if final_response.status_code == 200:
            final_data = final_response.json()
            print(f"Final conversation response:")
            print(f"  Evidence threshold: {final_data.get('evidence_threshold_met')}")
            print(f"  Info cards: {len(final_data.get('info_cards', []) or [])}")
        
        # Check state one more time
        last_state_response = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if last_state_response.status_code == 200:
            last_state = last_state_response.json()
            print(f"  Final PNM scores count: {last_state.get('pnm_scores_count')}")
            
    except Exception as e:
        print(f"Direct scoring test failed: {e}")

def check_scoring_configuration():
    """Check if scoring system is properly configured"""
    
    print("\n=== SCORING CONFIGURATION CHECK ===")
    
    # Check question bank
    qb_response = requests.get(f"{BASE_URL}/chat/debug-question-bank")
    
    if qb_response.status_code == 200:
        qb_data = qb_response.json()
        print(f"Question bank status:")
        print(f"  Total questions: {qb_data.get('total_questions')}")
        print(f"  Question bank path: {qb_data.get('question_bank_path')}")
        
        if qb_data.get('first_question_sample'):
            sample = qb_data['first_question_sample']
            print(f"  Sample question: {sample.get('id')} - {sample.get('pnm')}")
    else:
        print(f"Question bank check failed: {qb_response.status_code}")

if __name__ == "__main__":
    debug_scoring_system()
    check_scoring_configuration()