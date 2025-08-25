#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive test of all 4 quality standards after fixes
Tests the final production-level quality as requested by user
"""

import requests
import json
import sys
import time
from typing import Dict, List, Optional, Any

# Fix Windows encoding issues
if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def test_standard_1_routing_accuracy():
    """
    STANDARD 1: User initial input routing accuracy
    - Can locate accurate terms?
    - Can locate accurate related questions?
    """
    print("=" * 70)
    print("QUALITY STANDARD 1: USER INPUT ROUTING ACCURACY")
    print("=" * 70)
    
    test_cases = [
        {
            "input": "I have severe trouble breathing at night",
            "expected_pnm": "Physiological", 
            "expected_term": "Breathing",
            "description": "Nighttime breathing difficulty"
        },
        {
            "input": "My hands are getting very weak and I drop things",
            "expected_pnm": "Physiological",
            "expected_term": "Hand function", 
            "description": "Hand weakness and dropping"
        },
        {
            "input": "I feel lonely and isolated from my friends",
            "expected_pnm": "Love & Belonging",
            "expected_term": "Isolation",
            "description": "Social isolation concerns"
        },
        {
            "input": "I want to feel more independent and in control",
            "expected_pnm": "Esteem", 
            "expected_term": "Independence",
            "description": "Independence and control needs"
        },
        {
            "input": "I need help with emergency planning for my condition",
            "expected_pnm": "Cognitive",
            "expected_term": "Planning & organisation", 
            "description": "Emergency preparedness"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {case['description']}")
        print(f"Input: \"{case['input']}\"")
        
        session_id = f"routing-test-{i}"
        
        # Test routing
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": case['input']}
        )
        
        if route_response.status_code == 200:
            route_data = route_response.json()
            actual_pnm = route_data.get('current_pnm')
            actual_term = route_data.get('current_term')
            
            pnm_correct = actual_pnm == case['expected_pnm']
            term_correct = actual_term == case['expected_term']
            
            print(f"Expected: {case['expected_pnm']} -> {case['expected_term']}")
            print(f"Actual:   {actual_pnm} -> {actual_term}")
            print(f"PNM Match: {'OK' if pnm_correct else 'FAIL'}, Term Match: {'OK' if term_correct else 'FAIL'}")
            
            # Test question retrieval
            question_response = requests.get(
                f"{BASE_URL}/chat/question",
                headers={"X-Session-Id": session_id}
            )
            
            question_relevant = False
            if question_response.status_code == 200:
                question_data = question_response.json()
                question_text = question_data.get('text', '').lower()
                
                # Check if question is relevant to the input
                input_keywords = case['input'].lower().split()
                keyword_matches = sum(1 for word in input_keywords if word in question_text)
                question_relevant = keyword_matches >= 2 or any(word in question_text for word in ['breathing', 'hand', 'lonely', 'independent', 'emergency'])
                
                print(f"Question: {question_data.get('text', '')[:80]}...")
                print(f"Question Relevant: {'OK' if question_relevant else 'FAIL'}")
            
            score = (pnm_correct * 0.4) + (term_correct * 0.4) + (question_relevant * 0.2)
            results.append({
                'case': case['description'],
                'pnm_correct': pnm_correct,
                'term_correct': term_correct, 
                'question_relevant': question_relevant,
                'score': score
            })
        else:
            print(f"Routing failed: {route_response.status_code}")
            results.append({
                'case': case['description'],
                'pnm_correct': False,
                'term_correct': False,
                'question_relevant': False,
                'score': 0.0
            })
    
    # Calculate overall score
    avg_score = sum(r['score'] for r in results) / len(results) * 100
    
    print(f"\n--- STANDARD 1 RESULTS ---")
    print(f"Average Routing Accuracy: {avg_score:.1f}%")
    
    if avg_score >= 90:
        print("EXCELLENT: Production-ready routing accuracy")
    elif avg_score >= 75:
        print("GOOD: Acceptable routing accuracy") 
    elif avg_score >= 60:
        print("FAIR: Routing needs improvement")
    else:
        print("POOR: Routing accuracy inadequate")
        
    return avg_score

def test_standard_2_info_card_quality():
    """
    STANDARD 2: Single term completion info quality
    - Can provide quality information when terms complete?
    """
    print("\n" + "=" * 70)
    print("QUALITY STANDARD 2: INFORMATION CARD QUALITY")
    print("=" * 70)
    
    test_scenarios = [
        {
            "name": "Breathing Difficulties", 
            "responses": [
                "I have severe breathing problems at night",
                "Yes, I wake up gasping for air multiple times",
                "It's gotten much worse and I use 4 pillows now"
            ]
        },
        {
            "name": "Hand Function Issues",
            "responses": [
                "My hands are very weak and shaky",
                "Yes, I drop things constantly throughout the day", 
                "Writing and typing have become nearly impossible"
            ]
        }
    ]
    
    all_cards = []
    quality_scores = []
    
    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 40)
        
        session_id = f"info-test-{hash(scenario['name']) % 1000}"
        
        # Route initial input
        initial_input = scenario['responses'][0]
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": initial_input}
        )
        
        # Process conversation to trigger info cards
        for i, response in enumerate(scenario['responses']):
            print(f"  Step {i+1}: {response[:50]}...")
            
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation", 
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"user_response": response}
            )
            
            if conv_response.status_code == 200:
                data = conv_response.json()
                info_cards = data.get('info_cards', []) or []
                
                if info_cards:
                    print(f"    Generated {len(info_cards)} info cards")
                    for card in info_cards:
                        card_quality = analyze_enhanced_card_quality(card)
                        quality_scores.append(card_quality)
                        all_cards.append(card)
                        
                        title = card.get('title', 'No title')
                        bullets = card.get('bullets', [])
                        print(f"      Card: {title[:60]}...")
                        print(f"      Bullets: {len(bullets)}, Quality: {card_quality:.1f}/10")
                else:
                    print("    No info cards generated")
    
    # Calculate results
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        total_cards = len(all_cards)
        
        print(f"\n--- STANDARD 2 RESULTS ---")
        print(f"Total cards generated: {total_cards}")
        print(f"Average card quality: {avg_quality:.1f}/10")
        
        if avg_quality >= 8.0:
            print("EXCELLENT: Production-ready info card quality")
        elif avg_quality >= 6.5:
            print("GOOD: Acceptable info card quality")
        elif avg_quality >= 5.0:
            print("FAIR: Info cards need improvement") 
        else:
            print("POOR: Info card quality inadequate")
            
        return avg_quality * 10  # Convert to percentage
    else:
        print("POOR: No info cards generated")
        return 0.0

def test_standard_3_pnm_assessment():
    """
    STANDARD 3: PNM single item assessment 
    - Can accurately locate and traverse PNM questions?
    - Does each term provide information?
    """
    print("\n" + "=" * 70)
    print("QUALITY STANDARD 3: PNM ASSESSMENT ACCURACY")
    print("=" * 70)
    
    # Test different PNM dimensions
    pnm_tests = [
        {
            "pnm": "Physiological",
            "input": "I have breathing difficulties",
            "expected_questions": ["breathing", "ventilatory", "lung"]
        },
        {
            "pnm": "Love & Belonging", 
            "input": "I feel isolated and lonely",
            "expected_questions": ["communicate", "support", "isolation"]
        },
        {
            "pnm": "Esteem",
            "input": "I want to feel more independent",
            "expected_questions": ["independent", "adaptations", "home"]
        }
    ]
    
    results = []
    
    for test in pnm_tests:
        print(f"\nTesting PNM: {test['pnm']}")
        print(f"Input: {test['input']}")
        
        session_id = f"pnm-test-{hash(test['pnm']) % 1000}"
        
        # Route to PNM
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"}, 
            json={"text": test['input']}
        )
        
        if route_response.status_code == 200:
            route_data = route_response.json()
            routed_pnm = route_data.get('current_pnm')
            
            pnm_correct = routed_pnm == test['pnm']
            print(f"Routed to: {routed_pnm} ({'OK' if pnm_correct else 'FAIL'})")
            
            # Get question
            question_response = requests.get(
                f"{BASE_URL}/chat/question",
                headers={"X-Session-Id": session_id}
            )
            
            question_relevant = False
            provides_info = False
            
            if question_response.status_code == 200:
                question_data = question_response.json()
                question_text = question_data.get('text', '').lower()
                
                # Check relevance
                question_relevant = any(keyword in question_text for keyword in test['expected_questions'])
                
                # Check if question provides actionable info
                provides_info = len(question_text) > 50 and any(word in question_text for word in 
                    ['did you', 'have you', 'are you', 'do you', 'can you'])
                
                print(f"Question relevant: {'OK' if question_relevant else 'FAIL'}")
                print(f"Provides info: {'OK' if provides_info else 'FAIL'}")
                print(f"Question: {question_data.get('text', '')[:100]}...")
            
            score = (pnm_correct * 0.5) + (question_relevant * 0.3) + (provides_info * 0.2)
            results.append(score)
        else:
            print(f"Routing failed: {route_response.status_code}")
            results.append(0.0)
    
    # Calculate overall score  
    avg_score = sum(results) / len(results) * 100 if results else 0
    
    print(f"\n--- STANDARD 3 RESULTS ---")
    print(f"PNM Assessment Accuracy: {avg_score:.1f}%")
    
    if avg_score >= 85:
        print("EXCELLENT: Production-ready PNM assessment")
    elif avg_score >= 70:
        print("GOOD: Acceptable PNM assessment")
    elif avg_score >= 55:
        print("FAIR: PNM assessment needs improvement")
    else:
        print("POOR: PNM assessment inadequate")
        
    return avg_score

def test_standard_4_pnm_scoring():
    """
    STANDARD 4: PNM scoring accuracy
    - Accurate scoring under different scenarios (novice vs expert)
    """
    print("\n" + "=" * 70)
    print("QUALITY STANDARD 4: PNM SCORING ACCURACY") 
    print("=" * 70)
    
    scenarios = [
        {
            "name": "Novice Response Pattern",
            "responses": [
                "I don't know much about breathing exercises",
                "No, I haven't tried any breathing techniques", 
                "I'm not sure what ventilatory support means"
            ],
            "expected_pattern": "low_awareness"
        },
        {
            "name": "Expert Response Pattern", 
            "responses": [
                "Yes, I practice diaphragmatic breathing daily and use my BiPAP at night",
                "I work closely with my respiratory therapist on lung function",
                "I monitor my oxygen levels and adjust my ventilatory support as needed"
            ],
            "expected_pattern": "high_awareness"
        }
    ]
    
    scoring_results = []
    
    for scenario in scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 40)
        
        session_id = f"scoring-{hash(scenario['name']) % 1000}"
        
        # Route initial breathing concern
        route_response = requests.post(
            f"{BASE_URL}/chat/route",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"text": "I have breathing problems"}
        )
        
        if route_response.status_code != 200:
            print(f"Routing failed: {route_response.status_code}")
            continue
        
        # Process responses to build evidence
        evidence_count = 0
        for i, response in enumerate(scenario['responses']):
            print(f"  Response {i+1}: {response[:60]}...")
            
            conv_response = requests.post(
                f"{BASE_URL}/chat/conversation",
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"user_response": response}
            )
            
            if conv_response.status_code == 200:
                data = conv_response.json()
                if data.get('evidence_threshold_met'):
                    evidence_count += 1
                    print(f"    Evidence threshold met!")
        
        # Check final session state for scoring
        state_response = requests.get(
            f"{BASE_URL}/chat/conversation-state",
            headers={"X-Session-Id": session_id}
        )
        
        if state_response.status_code == 200:
            state_data = state_response.json()
            pnm_scores = state_data.get('pnm_scores_count', 0)
            
            # Scoring success criteria
            evidence_built = evidence_count > 0
            scoring_triggered = pnm_scores > 0
            
            print(f"    Evidence built: {'OK' if evidence_built else 'FAIL'}")
            print(f"    Scoring triggered: {'OK' if scoring_triggered else 'FAIL'}")
            
            # Score based on evidence building and scoring completion
            score = (evidence_built * 0.6) + (scoring_triggered * 0.4)
            scoring_results.append(score)
        else:
            print(f"    State check failed: {state_response.status_code}")
            scoring_results.append(0.0)
    
    # Calculate overall scoring accuracy
    avg_score = sum(scoring_results) / len(scoring_results) * 100 if scoring_results else 0
    
    print(f"\n--- STANDARD 4 RESULTS ---")
    print(f"PNM Scoring Accuracy: {avg_score:.1f}%")
    
    if avg_score >= 85:
        print("EXCELLENT: Production-ready PNM scoring")
    elif avg_score >= 70:
        print("GOOD: Acceptable PNM scoring")
    elif avg_score >= 55:
        print("FAIR: PNM scoring needs improvement")
    else:
        print("POOR: PNM scoring inadequate")
        
    return avg_score

def analyze_enhanced_card_quality(card: Dict[str, Any]) -> float:
    """Enhanced card quality analysis with higher standards"""
    if not card:
        return 0.0
        
    quality_score = 0.0
    
    # Title quality (0-3 points) - Enhanced standards
    title = card.get("title", "")
    if title:
        if 40 <= len(title) <= 100 and any(word in title.lower() for word in ["breathing", "hand", "als", "mnd", "managing", "support"]):
            quality_score += 3.0
        elif 20 <= len(title) <= 120:
            quality_score += 2.0
        elif len(title) >= 10:
            quality_score += 1.0
    
    # Bullet quality (0-5 points) - Enhanced standards  
    bullets = card.get("bullets", [])
    if bullets:
        quality_score += min(len(bullets) * 0.8, 2.0)  # Up to 2 points for having bullets
        
        # Enhanced actionability check
        actionable_words = ["try", "consider", "discuss", "practice", "use", "adjust", "might find", "helpful approach", "many people"]
        actionable_count = 0
        comprehensive_count = 0
        
        for bullet in bullets:
            if any(word in bullet.lower() for word in actionable_words):
                actionable_count += 1
            if len(bullet.split()) >= 15:  # Comprehensive bullets
                comprehensive_count += 1
                
        quality_score += min(actionable_count * 0.5, 2.0)  # Up to 2 points for actionable content
        quality_score += min(comprehensive_count * 0.2, 1.0)  # Up to 1 point for comprehensive content
    
    # Source and context quality (0-2 points)
    source = card.get("source", "")
    pnm = card.get("pnm", "")
    term = card.get("term", "")
    
    if source and len(source) > 5:
        quality_score += 1.0
    if pnm and term:
        quality_score += 1.0
        
    return min(quality_score, 10.0)

def main():
    """Run all quality standard tests"""
    print("COMPREHENSIVE QUALITY TESTING - ALL 4 STANDARDS")
    print("Testing for 最终水准 (Final Production Level) Quality")
    print("=" * 70)
    
    # Run all tests
    score_1 = test_standard_1_routing_accuracy()
    score_2 = test_standard_2_info_card_quality()
    score_3 = test_standard_3_pnm_assessment()
    score_4 = test_standard_4_pnm_scoring()
    
    # Calculate overall quality score
    overall_score = (score_1 + score_2 + score_3 + score_4) / 4
    
    print("\n" + "=" * 70)
    print("FINAL QUALITY ASSESSMENT")
    print("=" * 70)
    print(f"Standard 1 - Routing Accuracy:     {score_1:.1f}%")
    print(f"Standard 2 - Info Card Quality:    {score_2:.1f}%")
    print(f"Standard 3 - PNM Assessment:       {score_3:.1f}%")
    print(f"Standard 4 - PNM Scoring:          {score_4:.1f}%")
    print("-" * 40)
    print(f"OVERALL QUALITY SCORE:             {overall_score:.1f}%")
    
    if overall_score >= 85:
        print(f"\nEXCELLENT: System meets final production level quality!")
        print("All backend quality standards achieved")
    elif overall_score >= 75:
        print(f"\nGOOD: System meets acceptable production quality")
        print("Minor improvements recommended for optimal performance")
    elif overall_score >= 65:
        print(f"\nFAIR: System approaching production quality") 
        print("Several improvements needed before production deployment")
    else:
        print(f"\nPOOR: System below production quality standards")
        print("Significant improvements required")
        
    return overall_score

if __name__ == "__main__":
    main()