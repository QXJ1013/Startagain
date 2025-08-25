#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test with completely fresh session to debug issues
"""

import requests
import json
import sys
import random

# Fix Windows encoding issues
if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def test_fresh_session():
    """Test with fresh session"""
    
    # Generate completely unique session ID
    session_id = f"fresh-test-{random.randint(100000, 999999)}"
    
    print(f"Testing with fresh session: {session_id}")
    print("=" * 50)
    
    try:
        # Step 1: Route to a simpler term
        print("Step 1: Routing to emergency planning...")
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={
                "X-Session-Id": session_id,
                "Content-Type": "application/json"
            },
            json={"text": "I have trouble breathing"}
        )
        
        if route_response.status_code == 200:
            route_data = route_response.json()
            print(f"  -> Routed to: {route_data.get('current_pnm')} -> {route_data.get('current_term')}")
        else:
            print(f"  -> Route failed: {route_response.status_code}")
            return False
            
        # Step 2: Check if session was created correctly
        state_response = requests.get(
            f"{BASE_URL}/chat/state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            print(f"  -> FSM State: {state_data.get('fsm_state')}")
            print(f"  -> Asked QIDs: {state_data.get('asked_qids')}")
            print(f"  -> Followup pointer: {state_data.get('followup_ptr')}")
        else:
            print(f"  -> State check failed: {state_response.status_code}")
            return False
        
        # Step 3: Get the first question
        print("\nStep 2: Getting first question...")
        question_response = requests.get(
            f"{BASE_URL}/chat/question",
            headers={"X-Session-Id": session_id}
        )
        
        if question_response.status_code == 200:
            question_data = question_response.json()
            question_text = question_data.get("text", "")
            question_type = question_data.get("type", "")
            print(f"  -> Question type: {question_type}")
            print(f"  -> Question text: {question_text[:80]}...")
            
            if "No question text available" in question_text:
                print("  -> ERROR: Still getting 'No question text available'")
                return False
            
            # Step 4: Answer the question
            print("\nStep 3: Answering question...")
            answer_response = requests.post(
                f"{BASE_URL}/chat/answer",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                },
                json={
                    "text": "Yes, I have a comprehensive emergency plan in place",
                    "meta": {"confidence": 5},
                    "request_info": False
                }
            )
            
            if answer_response.status_code == 200:
                answer_data = answer_response.json()
                next_state = answer_data.get("next_state")
                print(f"  -> Answer recorded, next state: {next_state}")
                
                # Check if scoring occurred
                if answer_data.get("scored"):
                    score = answer_data["scored"].get("score_0_7")
                    print(f"  -> Term scored immediately: {score}/7")
                    return True
                
                # Try a few more questions to trigger scoring
                print("\nStep 4: Continuing conversation...")
                for i in range(3):
                    question_response = requests.get(
                        f"{BASE_URL}/chat/question",
                        headers={"X-Session-Id": session_id}
                    )
                    
                    if question_response.status_code == 200:
                        question_data = question_response.json()
                        question_text = question_data.get("text", "")
                        print(f"  Q{i+2}: {question_text[:60]}...")
                        
                        # Answer with varying responses
                        answers = ["Sometimes", "Usually yes", "Not really"]
                        answer_response = requests.post(
                            f"{BASE_URL}/chat/answer",
                            headers={
                                "X-Session-Id": session_id,
                                "Content-Type": "application/json"
                            },
                            json={
                                "text": answers[i],
                                "meta": {"confidence": 3}
                            }
                        )
                        
                        if answer_response.status_code == 200:
                            answer_data = answer_response.json()
                            next_state = answer_data.get("next_state")
                            print(f"    -> Next state: {next_state}")
                            
                            if answer_data.get("scored"):
                                score = answer_data["scored"].get("score_0_7")
                                print(f"    -> Term scored: {score}/7")
                                return True
                                
                            if next_state == "done":
                                break
                    else:
                        break
                
                return False
            else:
                print(f"  -> Answer failed: {answer_response.status_code}")
                print(f"  -> Error details: {answer_response.text}")
                return False
        else:
            print(f"  -> Question failed: {question_response.status_code}")
            print(f"  -> Response: {question_response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    print("FRESH SESSION TEST")
    print("=" * 60)
    
    success = test_fresh_session()
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: Scoring system is working!")
    else:
        print("FAILURE: Still have issues to fix")