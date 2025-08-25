#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug information card content and quality issues
"""

import requests
import json
import sys

# Fix Windows encoding issues
if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def analyze_card_content():
    """Get actual card content and analyze what's causing quality issues"""
    
    print("=== DEBUGGING INFO CARD CONTENT ===")
    
    session_id = "debug-info-cards"
    
    # Simulate a conversation that should trigger good info cards
    responses = [
        "I have severe trouble breathing at night",
        "Yes, I wake up gasping for air every night", 
        "It's gotten much worse and I'm using 4 pillows now"
    ]
    
    for i, response in enumerate(responses):
        print(f"\nStep {i+1}: {response}")
        
        conv_response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={
                "X-Session-Id": session_id,
                "Content-Type": "application/json"
            },
            json={"user_response": response}
        )
        
        if conv_response.status_code == 200:
            data = conv_response.json()
            
            if data.get("info_cards"):
                print(f"\nGenerated {len(data['info_cards'])} info cards:")
                
                for j, card in enumerate(data["info_cards"], 1):
                    print(f"\n--- CARD {j} ---")
                    print(f"Title: {card.get('title', 'N/A')}")
                    print(f"Source: {card.get('source', 'N/A')}")
                    print(f"PNM: {card.get('pnm', 'N/A')}")
                    print(f"Term: {card.get('term', 'N/A')}")
                    print(f"Score: {card.get('score', 'N/A')}")
                    
                    bullets = card.get('bullets', [])
                    print(f"Bullets ({len(bullets)}):")
                    for k, bullet in enumerate(bullets, 1):
                        print(f"  {k}. {bullet}")
                        # Analyze bullet quality
                        words = len(bullet.split()) if bullet else 0
                        chars = len(bullet) if bullet else 0
                        actionable = any(word in bullet.lower() for word in ['try', 'consider', 'use', 'ask', 'practice']) if bullet else False
                        specific = any(word in bullet.lower() for word in ['breathing', 'night', 'pillow', 'position', 'als', 'mnd']) if bullet else False
                        
                        print(f"     Words: {words}, Chars: {chars}, Actionable: {actionable}, Specific: {specific}")
                
                # Overall quality analysis
                print(f"\n--- QUALITY ANALYSIS ---")
                for card in data["info_cards"]:
                    title_quality = analyze_title_quality(card.get('title', ''))
                    bullet_quality = analyze_bullets_quality(card.get('bullets', []))
                    overall_quality = calculate_card_quality(card)
                    
                    print(f"Card: {card.get('title', 'Untitled')[:50]}...")
                    print(f"  Title Quality: {title_quality:.1f}/3")
                    print(f"  Bullet Quality: {bullet_quality:.1f}/7") 
                    print(f"  Overall: {overall_quality:.1f}/10")
            else:
                print("  No info cards generated")
        else:
            print(f"  Error: {conv_response.status_code}")

def analyze_title_quality(title: str) -> float:
    """Analyze title quality in detail"""
    if not title:
        return 0.0
        
    score = 0.0
    
    # Length check
    if 10 <= len(title) <= 70:
        score += 1.0
    elif 5 <= len(title) < 10:
        score += 0.5
        
    # Specificity check
    specific_words = ['breathing', 'night', 'pillow', 'als', 'mnd', 'manage', 'support', 'comfort']
    if any(word in title.lower() for word in specific_words):
        score += 1.0
    
    # Engagement check
    engaging_words = ['managing', 'improving', 'supporting', 'guidance', 'strategies', 'comfort']
    if any(word in title.lower() for word in engaging_words):
        score += 1.0
        
    return min(score, 3.0)

def analyze_bullets_quality(bullets: list) -> float:
    """Analyze bullets quality in detail"""
    if not bullets:
        return 0.0
        
    total_score = 0.0
    
    for bullet in bullets:
        if not bullet:
            continue
            
        bullet_score = 0.0
        
        # Length check (good bullets should be substantial)
        words = len(bullet.split())
        if 15 <= words <= 40:
            bullet_score += 1.0
        elif 8 <= words < 15:
            bullet_score += 0.5
            
        # Actionability check
        action_words = ['try', 'consider', 'use', 'practice', 'ask', 'discuss', 'might find', 'helpful']
        if any(word in bullet.lower() for word in action_words):
            bullet_score += 0.5
            
        # Specificity check
        specific_words = ['breathing', 'pillow', 'position', 'night', 'support', 'equipment', 'therapy']
        if any(word in bullet.lower() for word in specific_words):
            bullet_score += 0.5
            
        total_score += bullet_score
        
    return min(total_score, 7.0)

def calculate_card_quality(card: dict) -> float:
    """Calculate overall card quality"""
    title_score = analyze_title_quality(card.get('title', ''))
    bullet_score = analyze_bullets_quality(card.get('bullets', []))
    
    # Basic components
    source_score = 2.0 if card.get('source') else 0.0
    
    return min(title_score + bullet_score + source_score, 10.0)

if __name__ == "__main__":
    analyze_card_content()