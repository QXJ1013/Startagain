#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test question bank directly to debug issues
"""

import sys
import logging
from app.services.question_bank import QuestionBank
from app.config import get_settings

# Set up logging
logging.basicConfig(level=logging.DEBUG)

def test_question_bank():
    """Test question bank functionality"""
    
    cfg = get_settings()
    qb = QuestionBank(cfg.QUESTION_BANK_PATH)
    
    print(f"Question Bank Test")
    print(f"Total questions: {len(qb.questions)}")
    print(f"Question bank path: {cfg.QUESTION_BANK_PATH}")
    
    # Test PNM coverage
    pnms = set()
    for q in qb.questions:
        pnms.add(q.pnm)
    
    print(f"\nAvailable PNMs: {sorted(pnms)}")
    
    # Test term lookup
    test_cases = [
        ("Cognitive", "Planning & organisation"),
        ("Physiological", "Breathing"),
        ("Safety", "Falls risk"),
        ("Love & Belonging", "Isolation")
    ]
    
    for pnm, term in test_cases:
        print(f"\nTesting: {pnm} -> {term}")
        
        # Direct get
        item = qb.get(pnm, term)
        print(f"  Direct get: {item.id if item else None}")
        
        # PNM questions
        pnm_items = qb.for_pnm(pnm)
        print(f"  PNM {pnm} has {len(pnm_items)} questions")
        if pnm_items:
            print(f"    First question: {pnm_items[0].id} - {pnm_items[0].term}")
        
        # Choose for term
        chosen = qb.choose_for_term(pnm, term, [])
        print(f"  Choose for term: {chosen.id if chosen else None}")
        if chosen:
            print(f"    Chosen question: {chosen.main[:60]}...")
        
    return len(qb.questions) > 0

if __name__ == "__main__":
    success = test_question_bank()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")