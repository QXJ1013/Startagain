#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the improved fallback mechanism
"""

from app.deps import get_question_bank

def test_fallback_mechanism():
    """Test the improved smart fallback mechanism"""
    
    qb = get_question_bank()
    
    print("=== TESTING SMART FALLBACK MECHANISM ===")
    
    # Test different PNMs with the same non-existent term
    test_cases = [
        ("Physiological", "NonExistentTerm"),
        ("Safety", "NonExistentTerm"), 
        ("Love & Belonging", "NonExistentTerm"),
        ("Esteem", "NonExistentTerm"),
        ("Self-Actualisation", "NonExistentTerm"),
        ("Cognitive", "NonExistentTerm"),
        ("Aesthetic", "NonExistentTerm"),
        ("Transcendence", "NonExistentTerm")
    ]
    
    results = {}
    
    for pnm, term in test_cases:
        question = qb.choose_for_term(pnm, term, asked_ids=[])
        if question:
            results[pnm] = question.id
            print(f"{pnm:20} -> {question.id}")
        else:
            results[pnm] = None
            print(f"{pnm:20} -> NO QUESTION")
    
    print(f"\n=== FALLBACK ANALYSIS ===")
    unique_questions = set(q for q in results.values() if q)
    print(f"Unique questions returned: {len(unique_questions)}")
    print(f"Questions: {sorted(unique_questions)}")
    
    # Check if same question is being returned for multiple PNMs
    question_counts = {}
    for pnm, qid in results.items():
        if qid:
            if qid not in question_counts:
                question_counts[qid] = []
            question_counts[qid].append(pnm)
    
    print(f"\nQuestion usage:")
    for qid, pnms in question_counts.items():
        print(f"  {qid}: used by {len(pnms)} PNMs -> {', '.join(pnms)}")
        
    # Check if smart fallback is working
    if len(unique_questions) > 1:
        print(f"\nSUCCESS: Smart fallback is working - {len(unique_questions)} different questions")
        return True
    else:
        print(f"\nPROBLEM: All PNMs are getting the same question")
        return False

if __name__ == "__main__":
    test_fallback_mechanism()