#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality test for backend routing and question accuracy.
Tests the first quality standard: Can user input locate accurate terms and related questions?
"""

import requests
import json
import sys
from typing import Dict, List, Tuple

# Fix Windows encoding issues
if sys.platform == "win32":
    import locale
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')

BASE_URL = "http://127.0.0.1:8002"

def test_routing_accuracy():
    """Test if user inputs are routed to correct PNM and terms"""
    
    # Test cases: (user_input, expected_pnm, expected_term)
    test_cases = [
        # Physiological tests
        ("I have trouble breathing at night", "Physiological", "Breathing"),
        ("I can't walk properly anymore", "Physiological", "Mobility"), 
        ("My hands are getting weak", "Physiological", "Hand function"),
        ("I choke when drinking", "Physiological", "Swallowing"),
        ("My speech is slurred", "Physiological", "Speech"),
        ("I'm losing weight", "Physiological", "Nutrition & Weight"),
        ("I feel very tired all the time", "Physiological", "Fatigue"),
        ("I have muscle cramps", "Physiological", "Spasticity & Cramp"),
        ("I have pain in my joints", "Physiological", "Pain"),
        ("I drool a lot", "Physiological", "Saliva & Secretions"),
        ("I can't sleep well", "Physiological", "Sleep"),
        
        # Safety tests
        ("I'm worried about falling", "Safety", "Falls risk"),
        ("I'm afraid of choking", "Safety", "Choking risk"), 
        ("I need grab rails in bathroom", "Safety", "Home adaptations"),
        
        # Love & Belonging tests
        ("I feel lonely", "Love & Belonging", "Isolation"),
        ("I need help from my family", "Love & Belonging", "Social support"),
        ("I can't communicate with friends", "Love & Belonging", "Communication access"),
        
        # Esteem tests
        ("I want to be independent", "Esteem", "Independence"),
        ("I lost my job because of ALS", "Esteem", "Work & role"),
        ("I feel like I have no control", "Esteem", "Control & choice"),
        
        # Cognitive tests
        ("I'm forgetting things", "Cognitive", "Memory & attention"),
        ("I need to plan for the future", "Cognitive", "Planning & organisation"),
        ("I want to learn about ALS", "Cognitive", "Understanding ALS/MND"),
        
        # Transcendence tests
        ("What's the meaning of my life now?", "Transcendence", "Meaning & purpose"),
        ("I want to share my story", "Transcendence", "Legacy & sharing"),
    ]
    
    print("🧪 Testing Routing Accuracy...")
    print("=" * 50)
    
    correct = 0
    total = len(test_cases)
    results = []
    
    for user_input, expected_pnm, expected_term in test_cases:
        session_id = f"test-routing-{hash(user_input) % 10000}"
        
        try:
            # Test routing
            response = requests.post(
                f"{BASE_URL}/chat/route",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                },
                json={"text": user_input}
            )
            
            if response.status_code == 200:
                data = response.json()
                actual_pnm = data.get("current_pnm")
                actual_term = data.get("current_term")
                
                # Check accuracy
                pnm_correct = actual_pnm == expected_pnm
                term_correct = actual_term == expected_term
                is_correct = pnm_correct and term_correct
                
                if is_correct:
                    correct += 1
                    status = "✅"
                else:
                    status = "❌"
                
                results.append({
                    "input": user_input,
                    "expected": f"{expected_pnm} -> {expected_term}",
                    "actual": f"{actual_pnm} -> {actual_term}",
                    "correct": is_correct,
                    "pnm_correct": pnm_correct,
                    "term_correct": term_correct
                })
                
                print(f"{status} {user_input[:50]:<50}")
                if not is_correct:
                    print(f"   Expected: {expected_pnm} -> {expected_term}")
                    print(f"   Actual:   {actual_pnm} -> {actual_term}")
                
            else:
                print(f"❌ {user_input[:50]:<50} (HTTP {response.status_code})")
                results.append({
                    "input": user_input,
                    "expected": f"{expected_pnm} -> {expected_term}",
                    "actual": f"ERROR: {response.status_code}",
                    "correct": False
                })
                
        except Exception as e:
            print(f"❌ {user_input[:50]:<50} (Exception: {e})")
            results.append({
                "input": user_input,
                "expected": f"{expected_pnm} -> {expected_term}",
                "actual": f"EXCEPTION: {e}",
                "correct": False
            })
    
    # Summary
    accuracy = (correct / total) * 100
    print("\n" + "=" * 50)
    print(f"📊 ROUTING ACCURACY RESULTS")
    print(f"✅ Correct: {correct}/{total} ({accuracy:.1f}%)")
    print(f"❌ Incorrect: {total-correct}/{total} ({100-accuracy:.1f}%)")
    
    # Detailed breakdown
    pnm_correct = sum(1 for r in results if r.get("pnm_correct", False))
    term_correct = sum(1 for r in results if r.get("term_correct", False))
    
    print(f"\n📈 BREAKDOWN:")
    print(f"PNM Accuracy: {pnm_correct}/{total} ({pnm_correct/total*100:.1f}%)")
    print(f"Term Accuracy: {term_correct}/{total} ({term_correct/total*100:.1f}%)")
    
    # Quality assessment
    if accuracy >= 90:
        print(f"\n🏆 EXCELLENT: Routing quality meets production standards")
    elif accuracy >= 75:
        print(f"\n✅ GOOD: Routing quality is acceptable but could be improved")
    elif accuracy >= 50:
        print(f"\n⚠️  FAIR: Routing quality needs significant improvement")
    else:
        print(f"\n🚨 POOR: Routing quality is below acceptable standards")
    
    return results, accuracy

def test_question_retrieval():
    """Test if we can get relevant questions after routing"""
    
    print("\n🧪 Testing Question Retrieval...")
    print("=" * 50)
    
    test_cases = [
        ("I have trouble breathing at night", "Physiological", "Breathing"),
        ("My hands are weak", "Physiological", "Hand function"),
        ("I feel lonely", "Love & Belonging", "Isolation"),
    ]
    
    success = 0
    total = len(test_cases)
    
    for user_input, expected_pnm, expected_term in test_cases:
        session_id = f"test-question-{hash(user_input) % 10000}"
        
        try:
            # 1. Route first
            route_response = requests.post(
                f"{BASE_URL}/chat/route",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                },
                json={"text": user_input}
            )
            
            if route_response.status_code == 200:
                # 2. Get question
                question_response = requests.get(
                    f"{BASE_URL}/chat/question",
                    headers={"X-Session-Id": session_id}
                )
                
                if question_response.status_code == 200:
                    question_data = question_response.json()
                    question_text = question_data.get("text", "")
                    question_pnm = question_data.get("pnm")
                    question_term = question_data.get("term")
                    
                    # Validate question is relevant
                    if question_pnm == expected_pnm and question_term == expected_term and question_text:
                        success += 1
                        print(f"✅ {user_input[:30]:<30} -> Got relevant question")
                        print(f"   Question: {question_text[:80]}...")
                    else:
                        print(f"❌ {user_input[:30]:<30} -> Question mismatch")
                        print(f"   Expected: {expected_pnm}/{expected_term}")
                        print(f"   Got: {question_pnm}/{question_term}")
                else:
                    print(f"❌ {user_input[:30]:<30} -> Question retrieval failed ({question_response.status_code})")
            else:
                print(f"❌ {user_input[:30]:<30} -> Routing failed ({route_response.status_code})")
                
        except Exception as e:
            print(f"❌ {user_input[:30]:<30} -> Exception: {e}")
    
    question_accuracy = (success / total) * 100
    print(f"\n📊 QUESTION RETRIEVAL RESULTS")
    print(f"✅ Success: {success}/{total} ({question_accuracy:.1f}%)")
    print(f"❌ Failed: {total-success}/{total} ({100-question_accuracy:.1f}%)")
    
    return question_accuracy

if __name__ == "__main__":
    print("🚀 BACKEND QUALITY TEST - Routing & Questions")
    print("=" * 60)
    
    # Test 1: Routing accuracy
    results, routing_accuracy = test_routing_accuracy()
    
    # Test 2: Question retrieval
    question_accuracy = test_question_retrieval()
    
    # Overall assessment
    overall_score = (routing_accuracy + question_accuracy) / 2
    
    print("\n" + "=" * 60)
    print(f"🎯 OVERALL QUALITY ASSESSMENT")
    print(f"Routing Accuracy: {routing_accuracy:.1f}%")
    print(f"Question Accuracy: {question_accuracy:.1f}%") 
    print(f"Overall Score: {overall_score:.1f}%")
    
    if overall_score >= 85:
        print(f"🏆 RESULT: EXCELLENT - Ready for production")
    elif overall_score >= 70:
        print(f"✅ RESULT: GOOD - Minor improvements needed")
    elif overall_score >= 55:
        print(f"⚠️  RESULT: FAIR - Significant improvements needed")
    else:
        print(f"🚨 RESULT: POOR - Major rework required")