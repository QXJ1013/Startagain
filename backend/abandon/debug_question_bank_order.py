#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug question bank order and PNM coverage
"""

from app.deps import get_question_bank

def debug_question_bank_order():
    """Debug question bank order and coverage"""
    
    qb = get_question_bank()
    
    print("=== QUESTION BANK ORDER AND COVERAGE ===")
    print(f"Total questions: {len(qb._items)}")
    print()
    
    # Show first 10 questions
    print("First 10 questions in order:")
    for i, item in enumerate(qb._items[:10]):
        print(f"  {i+1}. {item.id} - {item.pnm}/{item.term}")
    print()
    
    # Check PNM coverage
    print("Questions by PNM:")
    pnm_counts = {}
    for item in qb._items:
        pnm = item.pnm
        if pnm not in pnm_counts:
            pnm_counts[pnm] = []
        pnm_counts[pnm].append(item.id)
    
    for pnm in sorted(pnm_counts.keys()):
        questions = pnm_counts[pnm]
        print(f"  {pnm}: {len(questions)} questions")
        print(f"    {', '.join(questions[:5])}" + ("..." if len(questions) > 5 else ""))
    
    # Check specific problematic terms
    print("\nChecking specific term mappings:")
    problematic_terms = [
        ("Safety", "Emergency preparedness"),
        ("Cognitive", "Planning & organisation"),
        ("Self-Actualisation", "Hobbies & goals"),
        ("Transcendence", "Meaning & purpose")
    ]
    
    for pnm, term in problematic_terms:
        item = qb.get(pnm, term)
        if item:
            print(f"  {pnm}/{term} -> {item.id}")
        else:
            print(f"  {pnm}/{term} -> NOT FOUND")
            # Try to find similar
            approx = qb.approx_by_term(pnm, term)
            if approx:
                print(f"    Approx matches: {[a.id for a in approx]}")
            else:
                pnm_items = qb.for_pnm(pnm)
                print(f"    Available in {pnm}: {[p.id for p in pnm_items[:3]]}")

if __name__ == "__main__":
    debug_question_bank_order()