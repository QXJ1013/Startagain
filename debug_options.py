#!/usr/bin/env python3
"""
Debug script to check question options structure
"""
import sys
import os
sys.path.append('/Users/xingjian.qin/Documents/Startagain/backend')

from app.services.question_bank import QuestionBank
from app.config import settings

def debug_options():
    print("=== Debug Question Options Structure ===")

    qb = QuestionBank(settings.QUESTION_BANK_PATH)

    # Get Aesthetic questions (smallest set)
    aesthetic_questions = qb.for_pnm("Aesthetic")

    print(f"Found {len(aesthetic_questions)} Aesthetic questions")

    for i, q in enumerate(aesthetic_questions[:2]):  # Check first 2 questions
        print(f"\n--- Question {i+1} ---")
        print(f"ID: {q.id}")
        print(f"Term: {q.term if hasattr(q, 'term') else 'No term'}")
        print(f"Main text: {q.main[:100] if q.main else 'No main text'}...")
        print(f"Options count: {len(q.options) if q.options else 0}")

        if q.options:
            print("Options structure:")
            for j, option in enumerate(q.options[:3]):  # Check first 3 options
                print(f"  Option {j}: {option}")
                if isinstance(option, dict):
                    print(f"    Keys: {list(option.keys())}")
                    if 'score' in option:
                        print(f"    Score: {option['score']}")
                    else:
                        print(f"    No score field!")

if __name__ == "__main__":
    debug_options()