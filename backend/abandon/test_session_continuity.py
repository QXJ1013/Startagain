#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test session continuity across conversation calls
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8002"

def test_session_continuity():
    """Test that session state is maintained across calls"""
    
    session_id = "test-continuity-001"
    
    print("=== TESTING SESSION CONTINUITY ===")
    
    # Step 1: Route user input
    print("1. INITIAL ROUTING")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have severe trouble breathing at night"}
    )
    
    if route_response.status_code == 200:
        route_data = route_response.json()
        print(f"Routed to PNM: {route_data.get('current_pnm')}")
        print(f"Routed to Term: {route_data.get('current_term')}")
    
    # Step 2: Check conversation state immediately after routing
    print("\n2. STATE AFTER ROUTING")
    state_response = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        print(f"Session current_pnm: {state_data.get('current_pnm')}")
        print(f"Session current_term: {state_data.get('current_term')}")
        print(f"Session current_qid: {state_data.get('current_qid')}")
        print(f"Session fsm_state: {state_data.get('fsm_state')}")
        print(f"Session turn_index: {state_data.get('turn_index')}")
    
    # Step 3: Get question
    print("\n3. GET QUESTION")
    question_response = requests.get(
        f"{BASE_URL}/chat/question",
        headers={"X-Session-Id": session_id}
    )
    
    if question_response.status_code == 200:
        question_data = question_response.json()
        print(f"Question ID: {question_data.get('id')}")
        print(f"Question PNM: {question_data.get('pnm')}")
    
    # Step 4: Make conversation call
    print("\n4. CONVERSATION CALL")
    conv_response = requests.post(
        f"{BASE_URL}/chat/conversation",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"user_response": "Yes, I wake up gasping for air"}
    )
    
    if conv_response.status_code == 200:
        conv_data = conv_response.json()
        print(f"Conversation current_pnm: {conv_data.get('current_pnm')}")
        print(f"Conversation current_term: {conv_data.get('current_term')}")
        print(f"Conversation fsm_state: {conv_data.get('fsm_state')}")
        info_cards = conv_data.get('info_cards', []) or []
        print(f"Info cards: {len(info_cards)}")
        print(f"Evidence threshold: {conv_data.get('evidence_threshold_met')}")
    else:
        print(f"Conversation error: {conv_response.status_code}")
        print(f"Error: {conv_response.text}")
    
    # Step 5: Check state again after conversation
    print("\n5. STATE AFTER CONVERSATION")
    state_response2 = requests.get(
        f"{BASE_URL}/chat/conversation-state", 
        headers={"X-Session-Id": session_id}
    )
    
    if state_response2.status_code == 200:
        state_data2 = state_response2.json()
        print(f"Final current_pnm: {state_data2.get('current_pnm')}")
        print(f"Final current_term: {state_data2.get('current_term')}")
        print(f"Final turn_index: {state_data2.get('turn_index')}")
        print(f"Final evidence_count: {state_data2.get('evidence_count')}")

if __name__ == "__main__":
    test_session_continuity()