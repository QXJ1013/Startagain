#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug specific question details
"""

from app.services.question_bank import QuestionBank

def debug_question_details():
    """Debug the specific question that's failing"""
    
    from app.config import get_settings
    cfg = get_settings()
    qb = QuestionBank(cfg.QUESTION_BANK_PATH)
    
    print("Debugging PROMPT-052...")
    print("=" * 50)
    
    # Find the specific item for different terms
    print("Checking term: 'Breathing'")
    item = qb.choose_for_term(pnm="Physiological", term="Breathing", asked_ids=[])
    if not item:
        print("  No item found for 'Breathing', trying other terms...")
        
        # Try other possible terms
        possible_terms = ["Ventilatory support", "Breathing exercises", "Respiratory support"]
        for term in possible_terms:
            print(f"  Trying term: '{term}'")
            item = qb.choose_for_term(pnm="Physiological", term=term, asked_ids=[])
            if item:
                print(f"  Found item for '{term}': {item.id}")
                break
        
        if not item:
            print("  Still no item found!")
            return
    
    if not item:
        print("No item found!")
        return
        
    print(f"Item ID: {item.id}")
    print(f"Item PNM: {item.pnm}")  
    print(f"Item Term: {item.term}")
    print(f"Main question: {item.main[:100]}...")
    print(f"Number of followups: {len(item.followups)}")
    
    print("\nFollowup details:")
    for idx, followup in enumerate(item.followups):
        print(f"  Followup {idx+1}:")
        print(f"    Type: {type(followup)}")
        if isinstance(followup, dict):
            print(f"    ID: {followup.get('id')}")
            print(f"    Text: {followup.get('text', '')[:100]}...")
            print(f"    Type field: {followup.get('type')}")
            print(f"    Options count: {len(followup.get('options', []))}")
        else:
            print(f"    Content: {str(followup)[:100]}...")
        print()

if __name__ == "__main__":
    debug_question_details()