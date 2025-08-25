#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test followup extraction directly
"""

import sys
from app.services.question_bank import QuestionBank
from app.config import get_settings

def test_followup_extraction():
    """Test followup extraction from question bank"""
    
    cfg = get_settings()
    qb = QuestionBank(cfg.QUESTION_BANK_PATH)
    
    print("Followup Extraction Test")
    print("=" * 50)
    
    # Get PROMPT-051 specifically
    item = qb.get_question_by_id("PROMPT-051")
    
    if item:
        print(f"Question ID: {item.id}")
        print(f"Main text: {item.main[:60]}...")
        print(f"Followups type: {type(item.followups)}")
        print(f"Followups length: {len(item.followups) if item.followups else 0}")
        
        if item.followups:
            print(f"\nFollowup details:")
            for i, followup in enumerate(item.followups):
                print(f"  [{i}] Type: {type(followup)}")
                # Skip printing full value due to encoding issues
                print(f"  [{i}] Value: [Dict with keys: {list(followup.keys()) if isinstance(followup, dict) else 'Not dict'}]")
                
                if isinstance(followup, dict):
                    text = followup.get("text", "NO TEXT")
                    print(f"  [{i}] Text: {text[:60]}...")
        else:
            print("No followups found!")
    else:
        print("PROMPT-051 not found!")
        
    # Test choose_for_term with debug
    print(f"\nTesting choose_for_term for Physiological -> Breathing...")
    chosen = qb.choose_for_term("Physiological", "Breathing", [])
    
    if chosen:
        print(f"Chosen: {chosen.id}")
        print(f"Chosen main: {chosen.main[:60]}...")
        print(f"Chosen followups: {len(chosen.followups) if chosen.followups else 0}")
        
        if chosen.followups:
            first_followup = chosen.followups[0]
            print(f"First followup type: {type(first_followup)}")
            print(f"First followup: {first_followup}")
    else:
        print("No question chosen!")

if __name__ == "__main__":
    test_followup_extraction()