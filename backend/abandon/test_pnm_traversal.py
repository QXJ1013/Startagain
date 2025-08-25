#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality test for PNM dimension assessment accuracy and complete traversal.
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

# Expected terms for each PNM dimension based on lexicon
PNM_EXPECTED_TERMS = {
    "Physiological": [
        "Breathing", "Mobility", "Hand function", "Swallowing", "Speech", 
        "Nutrition & Weight", "Fatigue", "Spasticity & Cramp", "Pain", 
        "Saliva & Secretions", "Sleep", "Bowel & Bladder"
    ],
    "Safety": [
        "Falls risk", "Choking risk", "Pressure care", "Equipment safety", "Home adaptations"
    ],
    "Love & Belonging": [
        "Social support", "Communication access", "Relationship & intimacy", "Isolation"
    ],
    "Esteem": [
        "Independence", "Work & role", "Confidence", "Control & choice"
    ],
    "Self-Actualisation": [
        "Hobbies & goals", "Learning & skills", "Contribute & advocacy"
    ],
    "Cognitive": [
        "Memory & attention", "Planning & organisation", "Understanding ALS/MND", "Decision making"
    ],
    "Aesthetic": [
        "Personal appearance", "Comfortable environment"
    ],
    "Transcendence": [
        "Meaning & purpose", "Spirituality & faith", "Legacy & sharing", "Gratitude & reflection"
    ]
}

def test_pnm_dimension_traversal():
    """Test if we can systematically traverse all terms in each PNM dimension"""
    
    print("Testing PNM Dimension Traversal...")
    print("=" * 50)
    
    results = []
    
    for pnm, expected_terms in PNM_EXPECTED_TERMS.items():
        print(f"\nTesting PNM: {pnm}")
        print(f"Expected terms: {len(expected_terms)}")
        print("-" * 40)
        
        session_id = f"test-pnm-{hash(pnm) % 10000}"
        visited_terms = set()
        questions_asked = 0
        
        try:
            # Test routing to this PNM using representative input
            pnm_inputs = {
                "Physiological": "I have breathing problems",
                "Safety": "I'm worried about falling",
                "Love & Belonging": "I feel lonely",
                "Esteem": "I want to be independent", 
                "Self-Actualisation": "I want to pursue my hobbies",
                "Cognitive": "I'm forgetting things",
                "Aesthetic": "I care about my appearance",
                "Transcendence": "What's the meaning of my life?"
            }
            
            initial_input = pnm_inputs.get(pnm, "I need help")
            
            # Route to PNM
            route_response = requests.post(
                f"{BASE_URL}/chat/route",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                },
                json={"text": initial_input}
            )
            
            if route_response.status_code == 200:
                route_data = route_response.json()
                actual_pnm = route_data.get("current_pnm")
                actual_term = route_data.get("current_term")
                
                print(f"  Routed to: {actual_pnm} -> {actual_term}")
                
                if actual_pnm == pnm:
                    visited_terms.add(actual_term)
                    
                    # Try to traverse through multiple questions
                    for attempt in range(20):  # Max 20 attempts to avoid infinite loop
                        try:
                            # Get question
                            question_response = requests.get(
                                f"{BASE_URL}/chat/question",
                                headers={"X-Session-Id": session_id}
                            )
                            
                            if question_response.status_code == 200:
                                question_data = question_response.json()
                                question_text = question_data.get("text", "")
                                question_pnm = question_data.get("pnm")
                                question_term = question_data.get("term")
                                
                                if question_pnm == pnm:
                                    visited_terms.add(question_term)
                                    questions_asked += 1
                                    
                                    print(f"    Q{questions_asked}: {question_term} - {question_text[:50]}...")
                                    
                                    # Answer with moderate response
                                    answer_response = requests.post(
                                        f"{BASE_URL}/chat/answer",
                                        headers={
                                            "X-Session-Id": session_id,
                                            "Content-Type": "application/json"  
                                        },
                                        json={
                                            "text": "Sometimes, it depends on the situation",
                                            "meta": {"confidence": 3}
                                        }
                                    )
                                    
                                    if answer_response.status_code != 200:
                                        print(f"      Answer failed: {answer_response.status_code}")
                                        break
                                        
                                else:
                                    print(f"    Question PNM mismatch: expected {pnm}, got {question_pnm}")
                                    break
                                    
                            elif question_response.status_code == 404:
                                print("    No more questions available")
                                break
                            else:
                                print(f"    Question failed: {question_response.status_code}")
                                break
                                
                        except Exception as e:
                            print(f"    Question loop error: {e}")
                            break
                            
                else:
                    print(f"  Routing failed: expected {pnm}, got {actual_pnm}")
                    
            else:
                print(f"  Route failed: {route_response.status_code}")
                
        except Exception as e:
            print(f"  Exception: {e}")
            
        # Calculate coverage
        coverage = len(visited_terms) / len(expected_terms) * 100
        missing_terms = set(expected_terms) - visited_terms
        
        results.append({
            "pnm": pnm,
            "expected_terms": len(expected_terms),
            "visited_terms": len(visited_terms),
            "coverage": coverage,
            "questions_asked": questions_asked,
            "missing_terms": list(missing_terms),
            "visited": list(visited_terms)
        })
        
        print(f"  Coverage: {len(visited_terms)}/{len(expected_terms)} ({coverage:.1f}%)")
        if missing_terms:
            print(f"  Missing: {', '.join(list(missing_terms)[:3])}{'...' if len(missing_terms) > 3 else ''}")
    
    return results

def test_term_question_availability():
    """Test if questions are available for all expected terms"""
    
    print("\nTesting Term Question Availability...")
    print("=" * 50)
    
    # Use question bank debug endpoint to check coverage
    try:
        debug_response = requests.get(f"{BASE_URL}/chat/debug-question-bank")
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            total_questions = debug_data.get("total_questions", 0)
            print(f"Total questions in bank: {total_questions}")
            
            # Calculate expected vs available
            total_expected_terms = sum(len(terms) for terms in PNM_EXPECTED_TERMS.values())
            print(f"Total expected terms: {total_expected_terms}")
            
            if total_questions > 0:
                coverage_ratio = min(total_questions / total_expected_terms, 1.0)
                print(f"Question coverage estimate: {coverage_ratio*100:.1f}%")
                return coverage_ratio
            else:
                print("No questions found in bank!")
                return 0.0
        else:
            print(f"Debug endpoint failed: {debug_response.status_code}")
            return 0.0
            
    except Exception as e:
        print(f"Question availability test failed: {e}")
        return 0.0

def analyze_traversal_results(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Analyze the traversal results and calculate metrics"""
    
    if not results:
        return {"avg_coverage": 0.0, "total_questions": 0, "success_rate": 0.0}
    
    total_coverage = sum(r["coverage"] for r in results)
    avg_coverage = total_coverage / len(results)
    
    total_questions = sum(r["questions_asked"] for r in results)
    
    # Success rate: PNMs with >50% coverage
    successful_pnms = sum(1 for r in results if r["coverage"] > 50.0)
    success_rate = successful_pnms / len(results) * 100
    
    return {
        "avg_coverage": avg_coverage,
        "total_questions": total_questions,
        "success_rate": success_rate,
        "successful_pnms": successful_pnms
    }

if __name__ == "__main__":
    print("BACKEND QUALITY TEST 3 - PNM Dimension Traversal")
    print("=" * 60)
    
    # Test PNM traversal
    traversal_results = test_pnm_dimension_traversal()
    
    # Test question availability
    question_coverage = test_term_question_availability()
    
    # Analyze results
    analysis = analyze_traversal_results(traversal_results)
    
    print("\n" + "=" * 60)
    print("PNM TRAVERSAL ANALYSIS")
    print(f"Average term coverage: {analysis['avg_coverage']:.1f}%")
    print(f"Total questions asked: {analysis['total_questions']}")
    print(f"PNM success rate: {analysis['success_rate']:.1f}% ({analysis['successful_pnms']}/{len(traversal_results)})")
    print(f"Question bank coverage: {question_coverage*100:.1f}%")
    
    # Detailed breakdown
    print(f"\nPNM COVERAGE BREAKDOWN:")
    for result in traversal_results:
        status = "GOOD" if result["coverage"] > 70 else "FAIR" if result["coverage"] > 50 else "POOR"
        print(f"  {result['pnm']}: {result['coverage']:.1f}% ({status})")
    
    # Overall assessment
    overall_score = (analysis['avg_coverage'] + analysis['success_rate'] + question_coverage*100) / 3
    
    print(f"\n" + "=" * 60)
    print("OVERALL TEST 3 ASSESSMENT")  
    print(f"Term Coverage: {analysis['avg_coverage']:.1f}%")
    print(f"PNM Success Rate: {analysis['success_rate']:.1f}%")
    print(f"Question Availability: {question_coverage*100:.1f}%")
    print(f"Overall Score: {overall_score:.1f}%")
    
    if overall_score >= 85:
        print("EXCELLENT: PNM traversal meets production standards")
    elif overall_score >= 70:
        print("GOOD: PNM traversal is acceptable")
    elif overall_score >= 55:
        print("FAIR: PNM traversal needs improvement")
    else:
        print("POOR: PNM traversal requires significant work")