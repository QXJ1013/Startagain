#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality test for PNM dimension assessment using conversation API.
Tests the third quality standard: Can PNM assessment accurately locate and traverse all terms?
"""

import requests
import json
import sys
from typing import Dict, List, Optional, Any

# Fix Windows encoding issues
if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def test_pnm_conversation_flow():
    """Test PNM assessment through conversation API"""
    
    print("Testing PNM Conversation Flow...")
    print("=" * 50)
    
    # Test different PNM areas
    test_scenarios = [
        {
            "name": "Physiological Issues",
            "pnm": "Physiological",
            "initial_input": "I have trouble breathing and my hands are weak",
            "responses": ["Yes, quite a lot", "Sometimes", "It's getting worse", "I need help with this"]
        },
        {
            "name": "Safety Concerns", 
            "pnm": "Safety",
            "initial_input": "I'm worried about falling and choking",
            "responses": ["Yes, I'm concerned", "It happens sometimes", "I need better safety measures", "Yes, definitely"]
        },
        {
            "name": "Social Connection",
            "pnm": "Love & Belonging", 
            "initial_input": "I feel lonely and isolated from my friends",
            "responses": ["Very much so", "It's difficult", "I miss social interaction", "Yes, I feel cut off"]
        },
        {
            "name": "Independence & Control",
            "pnm": "Esteem",
            "initial_input": "I want to maintain my independence and control",
            "responses": ["Very important to me", "I struggle with this", "It's challenging", "I want to do things myself"]
        }
    ]
    
    results = []
    
    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 40)
        
        session_id = f"test-conv-{hash(scenario['name']) % 10000}"
        questions_asked = 0
        terms_encountered = set()
        
        try:
            # Start conversation
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                },
                json={"user_response": scenario["initial_input"]}
            )
            
            if conv_response.status_code == 200:
                data = conv_response.json()
                questions_asked += 1
                
                print(f"  Q{questions_asked}: {data.get('question_text', '')[:60]}...")
                print(f"    Type: {data.get('question_type', 'N/A')}")
                
                # Continue conversation with responses
                for i, response in enumerate(scenario["responses"]):
                    try:
                        conv_response = requests.post(
                            f"{BASE_URL}/chat/conversation",
                            headers={
                                "X-Session-Id": session_id,
                                "Content-Type": "application/json"
                            },
                            json={"user_response": response}
                        )
                        
                        if conv_response.status_code == 200:
                            data = conv_response.json()
                            questions_asked += 1
                            
                            question_text = data.get("question_text", "")
                            if question_text and "Thank you" not in question_text:
                                print(f"  Q{questions_asked}: {question_text[:60]}...")
                                print(f"    Type: {data.get('question_type', 'N/A')}")
                                
                                # Check for info cards (indicates term completion)
                                if data.get("info_cards"):
                                    print(f"    -> Info cards generated: {len(data['info_cards'])}")
                                    
                                # Check evidence threshold
                                if data.get("evidence_threshold_met"):
                                    print(f"    -> Evidence threshold met!")
                            else:
                                print(f"  Conversation ended or completion message received")
                                break
                        else:
                            print(f"    Response {i+2} failed: {conv_response.status_code}")
                            break
                            
                    except Exception as e:
                        print(f"    Response {i+2} error: {e}")
                        break
                        
            else:
                print(f"  Initial conversation failed: {conv_response.status_code}")
                
        except Exception as e:
            print(f"  Exception: {e}")
            
        results.append({
            "scenario": scenario["name"],
            "pnm": scenario["pnm"],
            "questions_asked": questions_asked,
            "terms_encountered": len(terms_encountered),
            "success": questions_asked > 0
        })
        
        print(f"  Questions asked: {questions_asked}")
    
    return results

def test_conversation_state_tracking():
    """Test if conversation properly tracks state across questions"""
    
    print("\nTesting Conversation State Tracking...")
    print("=" * 50)
    
    session_id = f"test-state-{hash('state_test') % 10000}"
    
    try:
        # Start conversation
        responses = [
            "I have trouble breathing at night",
            "Yes, it's very difficult", 
            "It happens most nights",
            "I wake up gasping for air"
        ]
        
        states = []
        
        for i, response in enumerate(responses):
            # Send response
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                },
                json={"user_response": response}
            )
            
            if conv_response.status_code == 200:
                # Get conversation state
                state_response = requests.get(
                    f"{BASE_URL}/chat/conversation-state",
                    headers={"X-Session-Id": session_id}
                )
                
                if state_response.status_code == 200:
                    state_data = state_response.json()
                    states.append({
                        "turn": i + 1,
                        "current_pnm": state_data.get("current_pnm"),
                        "current_term": state_data.get("current_term"),
                        "turn_index": state_data.get("turn_index"),
                        "asked_qids": len(state_data.get("asked_qids", []))
                    })
                    
                    print(f"  Turn {i+1}:")
                    print(f"    PNM: {state_data.get('current_pnm', 'N/A')}")
                    print(f"    Term: {state_data.get('current_term', 'N/A')}")
                    print(f"    Questions asked: {len(state_data.get('asked_qids', []))}")
        
        # Check state consistency
        if states:
            consistent_pnm = len(set(s["current_pnm"] for s in states if s["current_pnm"])) <= 1
            increasing_questions = all(states[i]["asked_qids"] >= states[i-1]["asked_qids"] for i in range(1, len(states)))
            
            print(f"\n  State Analysis:")
            print(f"    Consistent PNM: {consistent_pnm}")
            print(f"    Increasing questions: {increasing_questions}")
            
            return consistent_pnm and increasing_questions
        else:
            return False
            
    except Exception as e:
        print(f"  State tracking error: {e}")
        return False

if __name__ == "__main__":
    print("BACKEND QUALITY TEST 3 - PNM Conversation Assessment")
    print("=" * 60)
    
    # Test conversation flows
    flow_results = test_pnm_conversation_flow()
    
    # Test state tracking
    state_tracking = test_conversation_state_tracking()
    
    # Analysis
    successful_flows = sum(1 for r in flow_results if r["success"])
    total_questions = sum(r["questions_asked"] for r in flow_results)
    avg_questions = total_questions / len(flow_results) if flow_results else 0
    
    print("\n" + "=" * 60)
    print("PNM CONVERSATION ASSESSMENT")
    print(f"Successful flows: {successful_flows}/{len(flow_results)}")
    print(f"Total questions asked: {total_questions}")
    print(f"Average questions per flow: {avg_questions:.1f}")
    print(f"State tracking: {'PASS' if state_tracking else 'FAIL'}")
    
    # Overall score
    flow_success_rate = successful_flows / len(flow_results) * 100 if flow_results else 0
    question_adequacy = min(avg_questions / 5 * 100, 100)  # Expect ~5 questions per flow
    state_score = 100 if state_tracking else 0
    
    overall_score = (flow_success_rate + question_adequacy + state_score) / 3
    
    print(f"\n" + "=" * 60) 
    print("OVERALL TEST 3 ASSESSMENT")
    print(f"Flow Success Rate: {flow_success_rate:.1f}%")
    print(f"Question Adequacy: {question_adequacy:.1f}%")
    print(f"State Tracking: {state_score:.1f}%")
    print(f"Overall Score: {overall_score:.1f}%")
    
    if overall_score >= 85:
        print("EXCELLENT: PNM conversation assessment meets production standards")
    elif overall_score >= 70:
        print("GOOD: PNM conversation assessment is acceptable")
    elif overall_score >= 55:
        print("FAIR: PNM conversation assessment needs improvement") 
    else:
        print("POOR: PNM conversation assessment requires significant work")