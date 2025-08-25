#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complete scoring workflow including finish endpoint
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

def test_complete_scoring_workflow():
    """Test the complete scoring workflow from start to finish"""
    
    print("Testing Complete Scoring Workflow...")
    print("=" * 50)
    
    session_id = f"test-complete-{hash('complete') % 10000}"
    
    try:
        # Step 1: Route user input
        print("Step 1: Routing user input...")
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={
                "X-Session-Id": session_id,
                "Content-Type": "application/json"
            },
            json={"text": "I have trouble breathing at night"}
        )
        
        if route_response.status_code == 200:
            route_data = route_response.json()
            print(f"  Routed to: {route_data.get('current_pnm')} -> {route_data.get('current_term')}")
        else:
            print(f"  Route failed: {route_response.status_code}")
            return
            
        # Step 2: Answer several questions
        print("Step 2: Answering questions...")
        for i in range(5):
            # Get question
            question_response = requests.get(
                f"{BASE_URL}/chat/question",
                headers={"X-Session-Id": session_id}
            )
            
            if question_response.status_code == 200:
                question_data = question_response.json()
                print(f"  Q{i+1}: {question_data.get('text', '')[:50]}...")
                
                # Answer question
                answer_response = requests.post(
                    f"{BASE_URL}/chat/answer",
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": "Yes, this is a significant problem for me",
                        "meta": {"confidence": 2},
                        "request_info": True
                    }
                )
                
                if answer_response.status_code == 200:
                    answer_data = answer_response.json()
                    print(f"    Answer recorded, next state: {answer_data.get('next_state')}")
                    
                    # Check if we got a score
                    if answer_data.get("scored"):
                        print(f"    Term scored: {answer_data['scored'].get('score_0_7')}/7")
                else:
                    print(f"    Answer failed: {answer_response.status_code}")
                    break
            else:
                print(f"  Question failed: {question_response.status_code}")
                break
        
        # Step 3: Check current scores
        print("Step 3: Checking current scores...")
        scores_response = requests.get(
            f"{BASE_URL}/chat/scores",
            headers={"X-Session-Id": session_id}
        )
        
        if scores_response.status_code == 200:
            scores_data = scores_response.json()
            term_scores = scores_data.get("term_scores", [])
            dimension_scores = scores_data.get("dimension_scores", [])
            
            print(f"  Term scores: {len(term_scores)}")
            for score in term_scores:
                print(f"    {score.get('pnm')} -> {score.get('term')}: {score.get('score_0_7')}/7")
                
            print(f"  Dimension scores: {len(dimension_scores)}")
            for score in dimension_scores:
                print(f"    {score.get('pnm')}: {score.get('score_0_7')}/7")
        else:
            print(f"  Scores check failed: {scores_response.status_code}")
            
        # Step 4: Finish and commit final scores
        print("Step 4: Finishing conversation and committing scores...")
        finish_response = requests.post(
            f"{BASE_URL}/chat/finish",
            headers={
                "X-Session-Id": session_id,
                "Content-Type": "application/json"
            },
            json={"commit": True}
        )
        
        if finish_response.status_code == 200:
            finish_data = finish_response.json()
            results = finish_data.get("results", [])
            
            print(f"  Finish results: {len(results)} PNM dimensions")
            for result in results:
                print(f"    {result.get('pnm')}: Score {result.get('score_0_7')}/7")
                print(f"      Term scores: {len(result.get('term_scores', []))}")
                print(f"      Uncovered terms: {len(result.get('uncovered_terms', []))}")
        else:
            print(f"  Finish failed: {finish_response.status_code}")
            
    except Exception as e:
        print(f"Complete workflow error: {e}")

def test_multi_pnm_scoring():
    """Test scoring across multiple PNM dimensions"""
    
    print("\nTesting Multi-PNM Scoring...")
    print("=" * 50)
    
    # Test inputs for different PNMs
    test_inputs = [
        ("I have breathing problems", "Physiological"),
        ("I feel lonely", "Love & Belonging"), 
        ("I want to be independent", "Esteem"),
        ("I'm worried about safety", "Safety")
    ]
    
    for input_text, expected_pnm in test_inputs:
        session_id = f"test-multi-{hash(input_text) % 10000}"
        
        print(f"\nTesting: {input_text} -> {expected_pnm}")
        print("-" * 30)
        
        try:
            # Route input
            route_response = requests.post(
                f"{BASE_URL}/chat/route",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                },
                json={"text": input_text}
            )
            
            if route_response.status_code == 200:
                route_data = route_response.json()
                actual_pnm = route_data.get("current_pnm")
                actual_term = route_data.get("current_term")
                
                print(f"  Routed to: {actual_pnm} -> {actual_term}")
                
                if actual_pnm == expected_pnm:
                    print("  ✓ Correct PNM routing")
                else:
                    print(f"  ✗ Expected {expected_pnm}, got {actual_pnm}")
                    
                # Quick scoring test - answer 3 questions
                for i in range(3):
                    # Get question
                    question_response = requests.get(
                        f"{BASE_URL}/chat/question",
                        headers={"X-Session-Id": session_id}
                    )
                    
                    if question_response.status_code == 200:
                        # Answer with high need/low capability
                        answer_response = requests.post(
                            f"{BASE_URL}/chat/answer",
                            headers={
                                "X-Session-Id": session_id,
                                "Content-Type": "application/json"
                            },
                            json={
                                "text": "This is very difficult for me",
                                "meta": {"confidence": 1}
                            }
                        )
                        
                        if answer_response.status_code == 200:
                            answer_data = answer_response.json()
                            if answer_data.get("scored"):
                                score = answer_data["scored"].get("score_0_7")
                                print(f"    Term scored: {score}/7")
                    else:
                        break
                        
            else:
                print(f"  Route failed: {route_response.status_code}")
                
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    print("COMPLETE SCORING WORKFLOW TEST")
    print("=" * 60)
    
    # Test complete workflow
    test_complete_scoring_workflow()
    
    # Test multi-PNM scoring
    test_multi_pnm_scoring()