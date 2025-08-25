#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality test for PNM scoring accuracy under different scenarios.
Tests the fourth quality standard: Are PNM scores accurate for different user personas?
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

def test_novice_user_scoring():
    """Test PNM scoring for a novice user who knows little about ALS/MND"""
    
    print("Testing Novice User Scoring (Low Knowledge/Confidence)...")
    print("=" * 50)
    
    session_id = f"test-novice-{hash('novice') % 10000}"
    
    # Novice responses: low confidence, high need for help
    novice_responses = [
        "I don't know much about this",
        "I'm not sure what to do",
        "This is all very confusing to me",
        "I need a lot of help",
        "I have no idea how to handle this",
        "I'm completely overwhelmed",
        "I don't understand what's happening",
        "I feel lost and scared"
    ]
    
    return test_scoring_scenario(session_id, "Novice User", novice_responses, expected_score_range=(1, 3))

def test_expert_user_scoring():
    """Test PNM scoring for an expert user (healthcare professional or experienced patient)"""
    
    print("Testing Expert User Scoring (High Knowledge/Confidence)...")  
    print("=" * 50)
    
    session_id = f"test-expert-{hash('expert') % 10000}"
    
    # Expert responses: high confidence, good understanding
    expert_responses = [
        "I understand this very well",
        "I'm very familiar with these options",
        "I have good knowledge about this",
        "I'm confident in my approach",
        "I know exactly what to do",
        "This is well within my expertise", 
        "I'm very experienced with this",
        "I have excellent understanding of the situation"
    ]
    
    return test_scoring_scenario(session_id, "Expert User", expert_responses, expected_score_range=(5, 7))

def test_moderate_user_scoring():
    """Test PNM scoring for a moderate user (some knowledge, mixed confidence)"""
    
    print("Testing Moderate User Scoring (Medium Knowledge/Confidence)...")
    print("=" * 50)
    
    session_id = f"test-moderate-{hash('moderate') % 10000}"
    
    # Moderate responses: mixed confidence and understanding
    moderate_responses = [
        "I have some understanding of this",
        "Sometimes I know what to do",
        "It depends on the situation",
        "I'm moderately confident",
        "I understand some aspects",
        "I have mixed feelings about this",
        "I know a bit but not everything",
        "I'm somewhat prepared"
    ]
    
    return test_scoring_scenario(session_id, "Moderate User", moderate_responses, expected_score_range=(3, 5))

def test_scoring_scenario(session_id: str, scenario_name: str, responses: List[str], expected_score_range: tuple) -> Dict[str, Any]:
    """Test scoring for a specific user scenario"""
    
    questions_answered = 0
    scores_received = []
    
    try:
        # Start conversation 
        for i, response in enumerate(responses):
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
                questions_answered += 1
                
                question_text = data.get("question_text", "")
                print(f"  Q{questions_answered}: {question_text[:50]}...")
                print(f"    Response: {response}")
                
                # Check if scoring completed
                if data.get("evidence_threshold_met"):
                    print(f"    -> Evidence threshold met, checking scores...")
                    
                    # Get current scores
                    scores_response = requests.get(
                        f"{BASE_URL}/chat/scores",
                        headers={"X-Session-Id": session_id}
                    )
                    
                    if scores_response.status_code == 200:
                        scores_data = scores_response.json()
                        term_scores = scores_data.get("term_scores", [])
                        dimension_scores = scores_data.get("dimension_scores", [])
                        
                        for score in term_scores:
                            scores_received.append({
                                "type": "term",
                                "pnm": score.get("pnm"),
                                "term": score.get("term"),
                                "score": score.get("score_0_7")
                            })
                            print(f"      Term Score: {score.get('pnm')} -> {score.get('term')}: {score.get('score_0_7')}/7")
                        
                        for score in dimension_scores:
                            scores_received.append({
                                "type": "dimension", 
                                "pnm": score.get("pnm"),
                                "score": score.get("score_0_7")
                            })
                            print(f"      Dimension Score: {score.get('pnm')}: {score.get('score_0_7')}/7")
                            
                # Stop if we get completion message
                if "Thank you" in question_text or not question_text:
                    break
                    
            else:
                print(f"    Request failed: {conv_response.status_code}")
                break
                
        # Analyze scores
        term_scores = [s["score"] for s in scores_received if s["type"] == "term" and s["score"] is not None]
        dimension_scores = [s["score"] for s in scores_received if s["type"] == "dimension" and s["score"] is not None]
        
        avg_term_score = sum(term_scores) / len(term_scores) if term_scores else 0
        avg_dimension_score = sum(dimension_scores) / len(dimension_scores) if dimension_scores else 0
        
        # Check if scores are in expected range
        expected_min, expected_max = expected_score_range
        term_in_range = expected_min <= avg_term_score <= expected_max if avg_term_score > 0 else False
        dim_in_range = expected_min <= avg_dimension_score <= expected_max if avg_dimension_score > 0 else False
        
        print(f"\n  {scenario_name} Results:")
        print(f"    Questions answered: {questions_answered}")
        print(f"    Term scores received: {len(term_scores)}")
        print(f"    Average term score: {avg_term_score:.1f}/7")
        print(f"    Average dimension score: {avg_dimension_score:.1f}/7")
        print(f"    Expected range: {expected_min}-{expected_max}")
        print(f"    Term score in range: {'YES' if term_in_range else 'NO'}")
        print(f"    Dimension score in range: {'YES' if dim_in_range else 'NO'}")
        
        return {
            "scenario": scenario_name,
            "questions_answered": questions_answered,
            "term_scores": term_scores,
            "dimension_scores": dimension_scores,
            "avg_term_score": avg_term_score,
            "avg_dimension_score": avg_dimension_score,
            "expected_range": expected_score_range,
            "term_in_range": term_in_range,
            "dim_in_range": dim_in_range,
            "success": term_in_range or dim_in_range
        }
        
    except Exception as e:
        print(f"  Scenario error: {e}")
        return {
            "scenario": scenario_name,
            "success": False,
            "error": str(e)
        }

def test_edge_case_scoring():
    """Test scoring for edge cases"""
    
    print("Testing Edge Case Scoring...")
    print("=" * 50)
    
    # Test extreme responses
    edge_cases = [
        {
            "name": "All Maximum Responses",
            "responses": ["Definitely yes", "Absolutely", "Always", "Completely", "Perfect", "Excellent"],
            "expected_range": (6, 7)
        },
        {
            "name": "All Minimum Responses", 
            "responses": ["Definitely not", "Never", "Not at all", "None", "Terrible", "Impossible"],
            "expected_range": (0, 2)
        },
        {
            "name": "Mixed Extreme Responses",
            "responses": ["Definitely yes", "Definitely not", "Always", "Never", "Perfect", "Terrible"],
            "expected_range": (2, 5)
        }
    ]
    
    edge_results = []
    
    for case in edge_cases:
        session_id = f"test-edge-{hash(case['name']) % 10000}"
        result = test_scoring_scenario(session_id, case["name"], case["responses"], case["expected_range"])
        edge_results.append(result)
    
    return edge_results

def analyze_scoring_accuracy(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Analyze the accuracy of PNM scoring across all scenarios"""
    
    if not results:
        return {"accuracy": 0.0, "coverage": 0.0}
    
    successful_scenarios = sum(1 for r in results if r.get("success", False))
    total_scenarios = len(results)
    
    total_scores = sum(len(r.get("term_scores", [])) + len(r.get("dimension_scores", [])) for r in results)
    scenarios_with_scores = sum(1 for r in results if len(r.get("term_scores", [])) > 0 or len(r.get("dimension_scores", [])) > 0)
    
    accuracy = successful_scenarios / total_scenarios * 100
    coverage = scenarios_with_scores / total_scenarios * 100
    
    return {
        "accuracy": accuracy,
        "coverage": coverage,
        "successful_scenarios": successful_scenarios,
        "total_scenarios": total_scenarios,
        "total_scores": total_scores
    }

if __name__ == "__main__":
    print("BACKEND QUALITY TEST 4 - PNM Scoring Accuracy")
    print("=" * 60)
    
    # Test different user scenarios
    novice_result = test_novice_user_scoring()
    expert_result = test_expert_user_scoring()  
    moderate_result = test_moderate_user_scoring()
    
    # Test edge cases
    edge_results = test_edge_case_scoring()
    
    # Combine all results
    all_results = [novice_result, expert_result, moderate_result] + edge_results
    
    # Analyze accuracy
    analysis = analyze_scoring_accuracy(all_results)
    
    print("\n" + "=" * 60)
    print("PNM SCORING ACCURACY ANALYSIS")
    print(f"Successful scenarios: {analysis['successful_scenarios']}/{analysis['total_scenarios']}")
    print(f"Scoring accuracy: {analysis['accuracy']:.1f}%")
    print(f"Score coverage: {analysis['coverage']:.1f}%")
    print(f"Total scores generated: {analysis['total_scores']}")
    
    # Detailed breakdown
    print(f"\nSCENARIO BREAKDOWN:")
    for result in all_results:
        if not result.get("success"):
            status = "FAIL"
        elif result.get("term_in_range") and result.get("dim_in_range"):
            status = "EXCELLENT"
        elif result.get("term_in_range") or result.get("dim_in_range"):
            status = "GOOD"
        else:
            status = "POOR"
            
        print(f"  {result.get('scenario', 'Unknown')}: {status}")
        if result.get("avg_term_score"):
            print(f"    Avg Term: {result['avg_term_score']:.1f}/7, Avg Dim: {result.get('avg_dimension_score', 0):.1f}/7")
    
    # Overall assessment
    print(f"\n" + "=" * 60)
    print("OVERALL TEST 4 ASSESSMENT")
    print(f"Scoring Accuracy: {analysis['accuracy']:.1f}%")
    print(f"Score Coverage: {analysis['coverage']:.1f}%")
    
    overall_score = (analysis['accuracy'] + analysis['coverage']) / 2
    
    if overall_score >= 85:
        print(f"EXCELLENT: PNM scoring accuracy meets production standards ({overall_score:.1f}%)")
    elif overall_score >= 70:
        print(f"GOOD: PNM scoring accuracy is acceptable ({overall_score:.1f}%)")
    elif overall_score >= 55:
        print(f"FAIR: PNM scoring accuracy needs improvement ({overall_score:.1f}%)")
    else:
        print(f"POOR: PNM scoring accuracy requires significant work ({overall_score:.1f}%)")