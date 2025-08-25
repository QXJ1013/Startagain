#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug session state tracking
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8002"

def debug_session_state():
    """Debug session state step by step"""
    
    import random
    session_id = f"debug-new-{random.randint(10000, 99999)}"
    
    print(f"Debugging session state: {session_id}")
    print("=" * 50)
    
    # Step 1: Route
    print("Step 1: Routing...")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={
            "X-Session-Id": session_id,
            "Content-Type": "application/json"
        },
        json={"text": "I have trouble breathing"}
    )
    
    if route_response.status_code == 200:
        print("  Route success")
        
        # Check state after routing
        state_response = requests.get(
            f"{BASE_URL}/chat/state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            print(f"  After routing:")
            print(f"    fsm_state: {state_data.get('fsm_state')}")
            print(f"    current_qid: {state_data.get('current_qid')}")
            print(f"    asked_qids: {state_data.get('asked_qids')}")
        
        print("\nStep 2: Getting question...")
        question_response = requests.get(
            f"{BASE_URL}/chat/question",
            headers={"X-Session-Id": session_id}
        )
        
        if question_response.status_code == 200:
            question_data = question_response.json()
            print(f"  Question received:")
            print(f"    id: {question_data.get('id')}")
            print(f"    type: {question_data.get('type')}")
            print(f"    text: {question_data.get('text', '')[:50]}...")
            
            # Check state after getting question
            state_response = requests.get(
                f"{BASE_URL}/chat/state",
                headers={"X-Session-Id": session_id}
            )
            
            if state_response.status_code == 200:
                state_data = state_response.json()
                print(f"  After getting question:")
                print(f"    fsm_state: {state_data.get('fsm_state')}")
                print(f"    current_qid: {state_data.get('current_qid')}")
                print(f"    asked_qids: {state_data.get('asked_qids')}")
                print(f"    followup_ptr: {state_data.get('followup_ptr')}")
                
                # Now check if we can answer
                if state_data.get('current_qid'):
                    print("\nStep 3: Current QID is set, trying to answer...")
                    answer_response = requests.post(
                        f"{BASE_URL}/chat/answer",
                        headers={
                            "X-Session-Id": session_id,
                            "Content-Type": "application/json"
                        },
                        json={
                            "text": "Yes, this is a problem for me",
                            "meta": {"confidence": 4}
                        }
                    )
                    
                    print(f"  Answer status: {answer_response.status_code}")
                    if answer_response.status_code == 200:
                        answer_data = answer_response.json()
                        print(f"  Answer success: {answer_data.get('next_state')}")
                        if answer_data.get('scored'):
                            print(f"  Term scored: {answer_data['scored'].get('score_0_7')}/7")
                    else:
                        print(f"  Answer error: {answer_response.text}")
                else:
                    print("\nStep 3: Current QID is NOT set - this is the problem!")
        else:
            print(f"  Question failed: {question_response.status_code}")
            print(f"  Response: {question_response.text}")
    else:
        print(f"  Route failed: {route_response.status_code}")

if __name__ == "__main__":
    debug_session_state()