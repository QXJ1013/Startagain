#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test PNM routing diversity - check if different PNM dimensions route to different questions
"""

import requests
import json
import random

BASE_URL = "http://127.0.0.1:8002"

def test_pnm_routing_diversity():
    """Test that different PNM dimensions route to different questions"""
    
    print("=== TESTING PNM ROUTING DIVERSITY ===")
    print("Testing if 8 different PNM dimensions route to different questions")
    print("=" * 70)
    
    # Test cases for each PNM dimension
    test_cases = [
        ("Physiological", ["I have trouble breathing", "I'm having pain", "I can't move well"]),
        ("Safety", ["I'm worried about my safety", "I need help with accessibility", "I'm concerned about emergency planning"]),
        ("Love & Belonging", ["I feel lonely", "I need social support", "I want to connect with others"]),
        ("Esteem", ["I want to feel independent", "I need respect from others", "I want to maintain my dignity"]),
        ("Self-Actualisation", ["I want to pursue my goals", "I need to express creativity", "I want personal growth"]),
        ("Cognitive", ["I need to understand my condition", "I want to learn more", "I need information about treatment"]),
        ("Aesthetic", ["I want beauty in my environment", "I need pleasant surroundings", "I care about how things look"]),
        ("Transcendence", ["I'm seeking spiritual meaning", "I want to help others", "I need purpose beyond myself"])
    ]
    
    results = {}
    
    for pnm_name, test_phrases in test_cases:
        print(f"\nTesting {pnm_name} PNM:")
        
        # Try each test phrase for this PNM
        pnm_questions = set()
        
        for phrase in test_phrases:
            session_id = f"test-{pnm_name.lower().replace(' ', '-')}-{random.randint(1000, 9999)}"
            
            try:
                # Route the phrase
                route_response = requests.post(
                    f"{BASE_URL}/chat/route",
                    headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                    json={"text": phrase}
                )
                
                if route_response.status_code == 200:
                    route_data = route_response.json()
                    routed_pnm = route_data.get('current_pnm')
                    routed_term = route_data.get('current_term')
                    
                    # Get the question
                    question_response = requests.get(
                        f"{BASE_URL}/chat/question",
                        headers={"X-Session-Id": session_id}
                    )
                    
                    if question_response.status_code == 200:
                        question_data = question_response.json()
                        question_id = question_data.get('id')
                        question_text = question_data.get('text', '')[:50] + "..."
                        
                        pnm_questions.add(question_id)
                        
                        print(f"  Phrase: '{phrase}'")
                        print(f"    Routed: {routed_pnm} -> {routed_term}")
                        print(f"    Question: {question_id} - {question_text}")
                        
                        if routed_pnm != pnm_name:
                            print(f"    WARNING: Expected {pnm_name} but got {routed_pnm}")
                    else:
                        print(f"  Phrase: '{phrase}' - Question failed: {question_response.status_code}")
                else:
                    print(f"  Phrase: '{phrase}' - Route failed: {route_response.status_code}")
                    
            except Exception as e:
                print(f"  Phrase: '{phrase}' - Error: {e}")
        
        results[pnm_name] = pnm_questions
        print(f"  {pnm_name} unique questions: {len(pnm_questions)}")
        if len(pnm_questions) > 0:
            print(f"    Question IDs: {', '.join(sorted(pnm_questions))}")
    
    # Analyze results
    print(f"\n=== DIVERSITY ANALYSIS ===")
    
    all_questions = set()
    for pnm_name, questions in results.items():
        all_questions.update(questions)
        
    print(f"Total unique questions across all PNMs: {len(all_questions)}")
    print(f"Question IDs: {', '.join(sorted(all_questions))}")
    
    # Check for the "same question" problem
    same_question_issue = False
    dominant_question = None
    
    if len(all_questions) <= 2:  # If only 1-2 questions for all 8 PNMs, that's the problem
        print(f"\nPROBLEM DETECTED: Only {len(all_questions)} unique questions for 8 PNM dimensions!")
        same_question_issue = True
        
        # Find the most common question
        question_counts = {}
        for questions in results.values():
            for q in questions:
                question_counts[q] = question_counts.get(q, 0) + 1
        
        if question_counts:
            dominant_question = max(question_counts.items(), key=lambda x: x[1])
            print(f"Dominant question: {dominant_question[0]} appears {dominant_question[1]} times")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    for pnm_name, questions in results.items():
        status = "OK" if len(questions) > 0 else "FAILED"
        print(f"{pnm_name}: {len(questions)} questions - {status}")
    
    if same_question_issue:
        print(f"\nISSUE CONFIRMED: Eight PNM dimensions are routing to too few unique questions")
        print(f"Expected: 8 different PNM dimensions should route to diverse questions")
        print(f"Actual: Only {len(all_questions)} unique questions found")
        return False
    else:
        print(f"\nSUCCESS: Good diversity in PNM routing")
        return True

if __name__ == "__main__":
    success = test_pnm_routing_diversity()
    if not success:
        print(f"\nACTION NEEDED: Fix PNM routing diversity issue")
    else:
        print(f"\nPNM routing diversity is working correctly")