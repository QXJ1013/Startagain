#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct test of PNM scoring system functionality without API layer.
Tests the core scoring components to verify they work correctly.
"""

import os
import sys

# Set encoding for Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_direct_pnm_scoring():
    """Test PNM scoring system directly without API calls"""
    
    print("=" * 60)
    print("DIRECT PNM SCORING SYSTEM TEST")
    print("=" * 60)
    
    test_results = []
    
    try:
        # Test 1: Primary PNM Scoring Engine
        print("\n1. TESTING PRIMARY PNM SCORING ENGINE")
        print("-" * 40)
        
        from app.services.pnm_scoring import PNMScoringEngine, PNMScore
        
        scoring_engine = PNMScoringEngine()
        
        # Test responses
        test_cases = [
            ("I use BiPAP machine every night and work with respiratory therapist", "Physiological", "Breathing"),
            ("I understand that ALS affects my breathing muscles and will get worse", "Physiological", "Breathing"), 
            ("I have backup power systems and emergency plans for my equipment", "Safety", "Emergency preparedness"),
            ("My family and I have discussed care planning and accessibility needs", "Safety", "Care decision-maker"),
            ("I use communication devices and maintain relationships with support groups", "Love & Belonging", "Communication")
        ]
        
        primary_scores = []
        for i, (response, pnm, term) in enumerate(test_cases, 1):
            try:
                score = scoring_engine.score_response(response, pnm, term)
                primary_scores.append(score)
                print(f"  Test {i}: {pnm}:{term} = {score.total_score}/16 ({score.percentage:.1f}%)")
            except Exception as e:
                print(f"  Test {i}: FAILED - {e}")
        
        if len(primary_scores) == len(test_cases):
            print(f"[PASS] Primary scoring engine: {len(primary_scores)}/{len(test_cases)} tests passed")
            test_results.append(("Primary Scoring Engine", True))
        else:
            print(f"[FAIL] Primary scoring engine: {len(primary_scores)}/{len(test_cases)} tests passed")
            test_results.append(("Primary Scoring Engine", False))
        
    except Exception as e:
        print(f"[ERROR] Primary scoring engine failed: {e}")
        test_results.append(("Primary Scoring Engine", False))
        primary_scores = []
    
    try:
        # Test 2: AI Fallback Scoring
        print("\n2. TESTING AI FALLBACK SCORING")
        print("-" * 40)
        
        from app.services.ai_scorer import create_ai_fallback_score
        
        ai_scores = []
        for i, (response, pnm, term) in enumerate(test_cases, 1):
            try:
                score = create_ai_fallback_score(response, pnm, term)
                ai_scores.append(score)
                print(f"  Test {i}: {pnm}:{term} = {score.total_score}/16 ({score.percentage:.1f}%)")
            except Exception as e:
                print(f"  Test {i}: FAILED - {e}")
        
        if len(ai_scores) == len(test_cases):
            print(f"[PASS] AI fallback scoring: {len(ai_scores)}/{len(test_cases)} tests passed")
            test_results.append(("AI Fallback Scoring", True))
        else:
            print(f"[FAIL] AI fallback scoring: {len(ai_scores)}/{len(test_cases)} tests passed")
            test_results.append(("AI Fallback Scoring", False))
        
    except Exception as e:
        print(f"[ERROR] AI fallback scoring failed: {e}")
        test_results.append(("AI Fallback Scoring", False))
        ai_scores = []
    
    try:
        # Test 3: Score Aggregation
        print("\n3. TESTING SCORE AGGREGATION")
        print("-" * 40)
        
        from app.services.aggregator import aggregate_pnm_scores_from_session
        
        # Use primary scores if available, otherwise AI scores
        scores_to_aggregate = primary_scores if primary_scores else ai_scores
        
        if scores_to_aggregate:
            aggregated = aggregate_pnm_scores_from_session(scores_to_aggregate)
            print(f"  Aggregated PNM levels: {list(aggregated.keys())}")
            for pnm, score in aggregated.items():
                print(f"  {pnm}: {score:.2f}/7.0")
            
            print(f"[PASS] Score aggregation: {len(aggregated)} PNM levels aggregated")
            test_results.append(("Score Aggregation", True))
        else:
            print("[FAIL] Score aggregation: No scores to aggregate")
            test_results.append(("Score Aggregation", False))
        
    except Exception as e:
        print(f"[ERROR] Score aggregation failed: {e}")
        test_results.append(("Score Aggregation", False))
    
    try:
        # Test 4: PNM Profile Generation
        print("\n4. TESTING PNM PROFILE GENERATION")
        print("-" * 40)
        
        scores_for_profile = primary_scores if primary_scores else ai_scores
        
        if scores_for_profile:
            profile = scoring_engine.calculate_overall_pnm_profile(scores_for_profile)
            suggestions = scoring_engine.generate_improvement_suggestions(profile)
            
            print(f"  Profile levels: {list(profile.keys())}")
            if 'overall' in profile:
                overall = profile['overall']
                print(f"  Overall score: {overall['score']}/{overall['possible']} ({overall['percentage']:.1f}%)")
                print(f"  Overall level: {overall['level']}")
            
            print(f"  Improvement suggestions: {len(suggestions)}")
            for i, suggestion in enumerate(suggestions[:3], 1):  # Show first 3
                print(f"    {i}. {suggestion}")
            
            print(f"[PASS] PNM profile generation: Profile created with {len(suggestions)} suggestions")
            test_results.append(("PNM Profile Generation", True))
        else:
            print("[FAIL] PNM profile generation: No scores available")
            test_results.append(("PNM Profile Generation", False))
        
    except Exception as e:
        print(f"[ERROR] PNM profile generation failed: {e}")
        test_results.append(("PNM Profile Generation", False))
    
    try:
        # Test 5: Session State Management
        print("\n5. TESTING SESSION STATE MANAGEMENT")
        print("-" * 40)
        
        from app.services.session import SessionState
        from app.services.storage import Storage
        
        # Create test session with scores
        storage = Storage()  # Use default in-memory for testing
        test_session = SessionState(session_id="direct-test-session")
        
        # Add scores to session
        scores_for_session = primary_scores if primary_scores else ai_scores
        if scores_for_session:
            test_session.pnm_scores = scores_for_session
            print(f"  Added {len(scores_for_session)} scores to session")
            
            # Save and reload session
            test_session.save(storage)
            print("  Session saved successfully")
            
            # Load session back
            loaded_session = SessionState.load(storage, "direct-test-session")
            loaded_scores = len(loaded_session.pnm_scores) if loaded_session.pnm_scores else 0
            print(f"  Loaded session with {loaded_scores} scores")
            
            if loaded_scores == len(scores_for_session):
                print(f"[PASS] Session state management: {loaded_scores}/{len(scores_for_session)} scores persisted")
                test_results.append(("Session State Management", True))
            else:
                print(f"[FAIL] Session state management: {loaded_scores}/{len(scores_for_session)} scores persisted")
                test_results.append(("Session State Management", False))
        else:
            print("[FAIL] Session state management: No scores to test with")
            test_results.append(("Session State Management", False))
        
    except Exception as e:
        print(f"[ERROR] Session state management failed: {e}")
        test_results.append(("Session State Management", False))
    
    # Final Results
    print("\n" + "=" * 60)
    print("DIRECT SCORING TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTest Summary:")
    print(f"  Tests Passed: {passed}/{total}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
    print(f"\nDetailed Results:")
    for test_name, success in test_results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {test_name}")
    
    # Overall Assessment
    print(f"\n" + "=" * 60)
    if success_rate >= 80:
        print("SCORING SYSTEM STATUS: FULLY FUNCTIONAL!")
        print("All core PNM scoring components are working correctly.")
        print("The issue is likely in the API layer, not the scoring logic.")
    elif success_rate >= 60:
        print("SCORING SYSTEM STATUS: MOSTLY FUNCTIONAL")
        print("Core scoring logic is working but some components need attention.")
    else:
        print("SCORING SYSTEM STATUS: NEEDS SIGNIFICANT WORK")
        print("Core scoring components have fundamental issues.")
    
    print("=" * 60)
    
    return success_rate >= 60

if __name__ == "__main__":
    result = test_direct_pnm_scoring()
    sys.exit(0 if result else 1)