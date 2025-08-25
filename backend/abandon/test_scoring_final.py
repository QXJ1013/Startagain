#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final test of the fixed PNM scoring system
"""

import requests
import json
import sys
import time

if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def test_scoring_final():
    """Test that PNM scores are now being persisted correctly"""
    
    print("=== FINAL TEST: FIXED PNM SCORING PERSISTENCE ===")
    
    session_id = "final-scoring-test"
    
    # Step 1: Route to start conversation
    print("1. Initial routing...")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have breathing difficulties and respiratory problems"}
    )
    
    if route_response.status_code != 200:
        print(f"Routing failed: {route_response.status_code}")
        return False
    
    print("Routing successful")
    
    # Step 2: Make responses that should trigger scoring
    print("\n2. Making responses that should trigger scoring...")
    
    responses = [
        "Yes, I use BiPAP machine every night for respiratory support",
        "I practice breathing exercises daily with my respiratory therapist",
        "I monitor my oxygen saturation levels regularly with a pulse oximeter",
    ]
    
    success_count = 0
    
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
            print(f"  Response processed successfully")
            print(f"  Evidence threshold met: {conv_data.get('evidence_threshold_met', False)}")
            print(f"  Info cards: {len(conv_data.get('info_cards', []) or [])}")
            
            # Check session state immediately
            state_response = requests.get(
                f"{BASE_URL}/chat/conversation-state",
                headers={"X-Session-Id": session_id}
            )
            
            if state_response.status_code == 200:
                state_data = state_response.json()
                scores_count = state_data.get('pnm_scores_count', 0)
                print(f"  PNM scores count: {scores_count}")
                
                if scores_count > 0:
                    print(f"  SUCCESS: Found {scores_count} persisted scores!")
                    success_count += 1
                else:
                    print(f"  ISSUE: No scores found in session state")
                    
                print(f"  Current context: {state_data.get('current_pnm')} -> {state_data.get('current_term')}")
            
            time.sleep(0.5)  # Small delay
            
        else:
            print(f"  Conversation failed: {conv_response.status_code}")
    
    # Step 3: Final comprehensive check
    print(f"\n3. FINAL VERIFICATION")
    print("-" * 50)
    
    # Check final session state
    final_state = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if final_state.status_code == 200:
        final_data = final_state.json()
        final_scores_count = final_data.get('pnm_scores_count', 0)
        print(f"Final PNM scores count: {final_scores_count}")
        
        if final_scores_count > 0:
            print(f"SUCCESS: Scoring system is working! {final_scores_count} scores persisted.")
        else:
            print("FAILURE: No scores found after all responses")
            return False
    
    # Check PNM profile
    profile_response = requests.get(
        f"{BASE_URL}/chat/pnm-profile",
        headers={"X-Session-Id": session_id}
    )
    
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        scores = profile_data.get('scores', [])
        profile = profile_data.get('profile')
        suggestions = profile_data.get('suggestions', [])
        
        print(f"\nPNM Profile Results:")
        print(f"  Total scores in profile: {len(scores)}")
        print(f"  Has awareness profile: {profile is not None}")
        print(f"  Number of suggestions: {len(suggestions)}")
        
        if scores:
            print("  Score details:")
            for score in scores:
                print(f"    {score.get('pnm_level')}:{score.get('domain')} = {score.get('total_score')}/16 ({score.get('percentage', 0):.1f}%)")
            
            return True
        else:
            print("  ERROR: No scores in profile despite session having scores")
            return False
    else:
        print(f"Profile check failed: {profile_response.status_code}")
        return False

if __name__ == "__main__":
    success = test_scoring_final()
    if success:
        print("\n" + "="*60)
        print("OVERALL RESULT: PNM SCORING SYSTEM IS NOW WORKING!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("OVERALL RESULT: PNM SCORING SYSTEM STILL HAS ISSUES")
        print("="*60)