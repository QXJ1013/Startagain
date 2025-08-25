#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple analysis of lexicon vs question bank mapping
"""

import json

def main():
    # Load files
    with open("app/data/pnm_lexicon.json", 'r', encoding='utf-8') as f:
        lexicon = json.load(f)
    
    with open("app/data/pnm_questions_v2_full.json", 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print("=== MAPPING ANALYSIS ===")
    
    # Get terms from question bank
    qb_terms = {}
    for q in questions:
        if "routing" in q:
            pnm = q["routing"].get("pnm")
            term = q["routing"].get("term")
            if pnm and term:
                if pnm not in qb_terms:
                    qb_terms[pnm] = set()
                qb_terms[pnm].add(term)
    
    # Get terms from lexicon
    lex_terms = {}
    for pnm, data in lexicon.items():
        if "terms" in data:
            lex_terms[pnm] = set(data["terms"].keys())
    
    # Compare
    print("PROBLEM CASES:")
    
    all_pnms = set(lex_terms.keys()) | set(qb_terms.keys())
    
    for pnm in sorted(all_pnms):
        lex_set = lex_terms.get(pnm, set())
        qb_set = qb_terms.get(pnm, set())
        
        # Terms in lexicon but missing in QB
        missing = lex_set - qb_set
        if missing:
            print(f"\n{pnm} - Terms in lexicon but NO questions:")
            for term in sorted(missing):
                print(f"  '{term}' -> NO QUESTIONS")
                
        # Check if PNM has no questions at all
        if not qb_set:
            print(f"\n{pnm} - COMPLETELY MISSING from question bank!")
            print(f"  Lexicon terms: {sorted(lex_set)}")
    
    print(f"\nQUESTION BANK COVERAGE:")
    for pnm in sorted(qb_terms.keys()):
        print(f"  {pnm}: {len(qb_terms[pnm])} questions")

if __name__ == "__main__":
    main()