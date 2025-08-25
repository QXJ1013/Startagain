#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test that demonstrates complete scoring system working
"""

import requests
import json
import random
from app.services.storage import Storage

BASE_URL = "http://127.0.0.1:8002"

def test_complete_scoring_success():
    """Comprehensive test showing the scoring system works end-to-end"""
    
    session_id = f"scoring-success-{random.randint(10000, 99999)}"
    
    print(f"=== COMPLETE SCORING SUCCESS TEST ===")
    print(f"Session ID: {session_id}")
    print("=" * 60)
    
    # Step 1: Route user input
    print("Step 1: Route breathing problem...")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have trouble breathing"}
    )
    
    if route_response.status_code != 200:
        print(f"  FAILED: Route error {route_response.status_code}")
        return False
        
    route_data = route_response.json()
    print(f"  SUCCESS: Routed to {route_data.get('current_pnm')} -> {route_data.get('current_term')}")
    
    # Step 2: Complete question-answer cycle until scoring
    questions_answered = 0
    
    while questions_answered < 10:  # Safety limit
        questions_answered += 1
        
        print(f"\nStep 2.{questions_answered}: Get question...")
        question_response = requests.get(
            f"{BASE_URL}/chat/question",
            headers={"X-Session-Id": session_id}
        )
        
        if question_response.status_code != 200:
            print(f"  Question failed: {question_response.status_code}")
            break
            
        question_data = question_response.json()
        print(f"  Question {question_data.get('id')} ({question_data.get('type')}): {question_data.get('text', '')[:80]}...")
        
        # Answer the question
        print(f"Step 2.{questions_answered}: Answer question...")
        answer_response = requests.post(
            f"{BASE_URL}/chat/answer",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "Yes, this is a significant issue for me", "meta": {"confidence": 4}}
        )
        
        if answer_response.status_code != 200:
            print(f"  FAILED: Answer error {answer_response.status_code}")
            return False
            
        answer_data = answer_response.json()
        next_state = answer_data.get('next_state')
        print(f"  Answer success: next_state = {next_state}")
        
        # Check if scoring happened
        if next_state == 'scored':
            print(f"\nSCORING ACHIEVED!")
            scored_obj = answer_data.get('scored')
            if scored_obj:
                print(f"   Term: {scored_obj.get('term')}")
                print(f"   Score: {scored_obj.get('score_0_7')}/7")
                print(f"   Rationale: {scored_obj.get('rationale', '')[:100]}...")
                print(f"   Method: {scored_obj.get('method_version')}")
            break
        elif next_state == 'done':
            print(f"  Flow completed without scoring")
            break
        elif next_state in ['followup', 'main']:
            print(f"  Continuing with more questions...")
            continue
        else:
            print(f"  Unknown state: {next_state}")
            break
    
    # Step 3: Verify database contains scores
    print(f"\nStep 3: Verify database scores...")
    storage = Storage()
    
    term_scores = storage.list_term_scores(session_id)
    dimension_scores = storage.list_dimension_scores(session_id)
    
    print(f"  Term scores: {len(term_scores)}")
    print(f"  Dimension scores: {len(dimension_scores)}")
    
    if term_scores:
        for score in term_scores:
            print(f"    Term: {score.get('pnm')}/{score.get('term')} = {score.get('score_0_7')}/7")
        print(f"  SUCCESS: Term scoring system works!")
        return True
    else:
        print(f"  FAILED: No term scores found in database")
        return False

if __name__ == "__main__":
    success = test_complete_scoring_success()
    if success:
        print(f"\nALL TESTS PASSED: PNM scoring system is fully functional!")
    else:
        print(f"\nTEST FAILED: There are still issues with the scoring system")