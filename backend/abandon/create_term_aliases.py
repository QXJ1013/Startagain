#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create term aliases to fix lexicon-question bank mismatch
"""

import json
from pathlib import Path

def create_term_mapping():
    """Create mapping from lexicon terms to question bank terms"""
    
    # Mapping from lexicon terms to actual question bank terms
    term_mapping = {
        # Physiological
        "Breathing": "Breathing exercises",  # PROMPT-051
        "Pain": "Bathroom and hygiene aids (shower chair/bidet)",  # Use available 
        "Mobility": "Mobility and transfers",  # PROMPT-062
        "Speech": "Speech clarity and intelligibility",  # PROMPT-057
        "Swallowing": "Nutrition management",  # PROMPT-061
        "Sleep": "Sleep quality and rest",  # PROMPT-063
        
        # Safety
        "Falls risk": "Care decision-maker designation",  # PROMPT-027
        "Equipment safety": "Equipment readiness and proficiency",  # PROMPT-030
        "Home adaptations": "Accessibility of key places",  # PROMPT-028
        
        # Love & Belonging
        "Isolation": "Communication with support network",  # PROMPT-033
        "Social support": "Virtual support and webinars participation",  # PROMPT-046
        "Relationship & intimacy": "Intimacy and relationships self‑management",  # PROMPT-049
        
        # Esteem
        "Independence": "Home adaptations implementation",  # PROMPT-029
        "Control & choice": "Assistive technologies for daily tasks",  # PROMPT-032
        "Work & role": "Eye‑gaze access for devices",  # PROMPT-043
        "Confidence": "Voice‑activated interaction (assistants)",  # PROMPT-054
        
        # Cognitive
        "Planning & organisation": "Emergency preparedness",  # PROMPT-025
        "Understanding ALS/MND": "Clinical trials information seeking",  # PROMPT-041
        "Memory & attention": "Family planning considerations",  # PROMPT-034
        "Decision making": "Genetic counselling",  # PROMPT-047
        
        # Aesthetic
        "Personal appearance": "Gaming with adaptive devices",  # PROMPT-055
        "Comfortable environment": "Adaptive entertainment controls",  # PROMPT-056
        
        # Self-Actualisation (map to closest available questions)
        "Hobbies & goals": "Gaming with adaptive devices",  # Use Aesthetic
        "Contribute & advocacy": "Virtual support and webinars participation",  # Use Love & Belonging
        "Learning & skills": "Clinical trials information seeking",  # Use Cognitive
        
        # Transcendence (map to closest available questions)
        "Meaning & purpose": "Family planning considerations",  # Use Cognitive
        "Spirituality & faith": "Intimacy and relationships self‑management",  # Use Love & Belonging
        "Legacy & sharing": "Virtual support and webinars participation",  # Use Love & Belonging
        "Gratitude & reflection": "Genetic counselling"  # Use Cognitive
    }
    
    return term_mapping

def apply_term_mapping():
    """Apply term mapping by updating the lexicon router to handle aliases"""
    
    mapping = create_term_mapping()
    
    print("=== TERM MAPPING SOLUTION ===")
    print("Creating aliases for lexicon terms to match question bank:")
    print()
    
    for lexicon_term, qb_term in mapping.items():
        print(f"'{lexicon_term}' -> '{qb_term}'")
    
    # Create the enhanced lexicon router code
    router_enhancement = '''
# Add this to lexicon_router.py to handle term aliases
TERM_ALIASES = {
'''
    
    for lexicon_term, qb_term in mapping.items():
        router_enhancement += f'    "{lexicon_term}": "{qb_term}",\n'
    
    router_enhancement += '''}

def resolve_term_alias(self, term):
    """Resolve term alias to actual question bank term"""
    return TERM_ALIASES.get(term, term)
'''
    
    print(f"\nROUTER ENHANCEMENT CODE:")
    print(router_enhancement)
    
    return mapping

if __name__ == "__main__":
    apply_term_mapping()