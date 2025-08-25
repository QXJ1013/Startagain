#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix term mapping between lexicon and question bank to test scoring
"""

import json
from pathlib import Path

def analyze_term_mismatch():
    """Analyze the mismatch between lexicon and question bank terms"""
    
    # Load lexicon
    lexicon_path = Path("app/data/pnm_lexicon.json")
    question_bank_path = Path("app/data/pnm_questions_v2_full.json")
    
    with open(lexicon_path, 'r', encoding='utf-8') as f:
        lexicon = json.load(f)
    
    with open(question_bank_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print("TERM MAPPING ANALYSIS")
    print("=" * 60)
    
    # Get lexicon terms by PNM
    lexicon_terms = {}
    for pnm, data in lexicon.items():
        lexicon_terms[pnm] = list(data.get("terms", {}).keys())
    
    # Get question bank terms by PNM
    qb_terms = {}
    for q in questions:
        routing = q.get("routing", {})
        pnm = routing.get("pnm")
        term = routing.get("term")
        if pnm and term:
            if pnm not in qb_terms:
                qb_terms[pnm] = set()
            qb_terms[pnm].add(term)
    
    # Convert sets to lists for printing
    for pnm in qb_terms:
        qb_terms[pnm] = list(qb_terms[pnm])
    
    print("\nLEXICON TERMS vs QUESTION BANK TERMS:")
    print("-" * 60)
    
    for pnm in sorted(lexicon_terms.keys()):
        print(f"\n{pnm}:")
        print(f"  Lexicon: {lexicon_terms[pnm]}")
        print(f"  Question Bank: {qb_terms.get(pnm, [])}")
        
        # Check matches
        lexicon_set = set(lexicon_terms[pnm])
        qb_set = set(qb_terms.get(pnm, []))
        matches = lexicon_set.intersection(qb_set)
        
        if matches:
            print(f"  MATCHES: {list(matches)}")
        else:
            print(f"  NO MATCHES")
    
    return lexicon_terms, qb_terms

def create_term_mapping():
    """Create a mapping file to bridge lexicon and question bank terms"""
    
    # This is a manual mapping based on semantic similarity
    term_mapping = {
        "Physiological": {
            "Breathing": "Breathing comfort without devices",
            "Hand function": "Hand weakness mitigation strategies", 
            "Speech": "Communication aids access",
            "Swallowing": "Eating safely strategies",
            "Mobility": "Walking aids setup",
            # Add more mappings as needed
        },
        "Safety": {
            "Falls risk": "Fall risk assessment",
            "Home adaptations": "Accessibility of key places",
        },
        "Love & Belonging": {
            "Social support": "Social connection coping",
            "Isolation": "Social connection coping",
        },
        "Esteem": {
            "Independence": "Independence support finding",
        },
        "Cognitive": {
            "Planning & organisation": "Emergency preparedness",
            "Memory & attention": "Emergency preparedness", 
            "Understanding ALS/MND": "Clinical trials information seeking",
        },
        "Aesthetic": {
            "Personal appearance": "Personal aesthetics",
        },
        "Transcendence": {
            "Meaning & purpose": "Legacy projects initiation",
        }
    }
    
    # Save mapping
    with open("app/data/term_mapping.json", 'w', encoding='utf-8') as f:
        json.dump(term_mapping, f, indent=2, ensure_ascii=False)
    
    print("\nTERM MAPPING CREATED")
    print("=" * 60)
    print("Saved to: app/data/term_mapping.json")
    
    return term_mapping

if __name__ == "__main__":
    lexicon_terms, qb_terms = analyze_term_mismatch()
    mapping = create_term_mapping()
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("Term mapping file created to bridge lexicon and question bank")
    print("This will help resolve 'No question text available' errors")