#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality test for information card generation when terms complete.
Tests the second quality standard: Can term completion provide quality information?
"""

import requests
import json
import sys
from typing import Dict, List, Optional, Any

# Fix Windows encoding issues
if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://127.0.0.1:8002"

def test_info_card_generation():
    """Test if information cards are generated when terms complete"""
    
    print("Testing Information Card Generation...")
    print("=" * 50)
    
    # Test cases for triggering information cards
    test_scenarios = [
        {
            "name": "Breathing Term Completion",
            "pnm": "Physiological",
            "term": "Breathing", 
            "user_responses": [
                "I have trouble breathing at night",
                "Yes, I wake up breathless",
                "It's gotten worse over the past month",
                "I need to use more pillows to sleep"
            ]
        },
        {
            "name": "Hand Function Term Completion",
            "pnm": "Physiological", 
            "term": "Hand function",
            "user_responses": [
                "My hands are getting weak",
                "I can't grip things properly anymore",
                "Yes, I drop things frequently",
                "Writing has become very difficult"
            ]
        },
        {
            "name": "Isolation Term Completion",
            "pnm": "Love & Belonging",
            "term": "Isolation", 
            "user_responses": [
                "I feel very lonely",
                "My friends don't visit as much anymore",
                "Yes, I feel cut off from everyone",
                "It's hard to maintain relationships"
            ]
        }
    ]
    
    results = []
    
    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 30)
        
        session_id = f"test-info-{hash(scenario['name']) % 10000}"
        
        try:
            # Simulate conversation flow to trigger info cards
            info_cards_generated = []
            
            for i, response in enumerate(scenario['user_responses']):
                print(f"  Step {i+1}: {response[:50]}...")
                
                # Send user response to conversation endpoint
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
                    
                    # Check if info cards were generated
                    if data.get("info_cards"):
                        info_cards_generated.extend(data["info_cards"])
                        print(f"    -> Generated {len(data['info_cards'])} info cards")
                        
                        # Analyze card quality
                        for card in data["info_cards"]:
                            quality_score = analyze_card_quality(card)
                            print(f"       Card quality: {quality_score:.1f}/10")
                    else:
                        print("    -> No info cards generated")
                        
                    # Check if evidence threshold met
                    if data.get("evidence_threshold_met"):
                        print("    -> Evidence threshold met!")
                else:
                    print(f"    -> Error: {conv_response.status_code}")
                    
            results.append({
                "scenario": scenario["name"],
                "cards_generated": len(info_cards_generated),
                "cards": info_cards_generated,
                "success": len(info_cards_generated) > 0
            })
            
        except Exception as e:
            print(f"  Exception: {e}")
            results.append({
                "scenario": scenario["name"], 
                "cards_generated": 0,
                "cards": [],
                "success": False,
                "error": str(e)
            })
    
    # Summary
    successful_scenarios = sum(1 for r in results if r["success"])
    total_cards = sum(r["cards_generated"] for r in results)
    
    print("\n" + "=" * 50)
    print("INFO CARD GENERATION RESULTS")
    print(f"Successful scenarios: {successful_scenarios}/{len(test_scenarios)}")
    print(f"Total info cards generated: {total_cards}")
    print(f"Success rate: {successful_scenarios/len(test_scenarios)*100:.1f}%")
    
    return results

def analyze_card_quality(card: Dict[str, Any]) -> float:
    """Analyze the quality of an individual info card"""
    
    if not card:
        return 0.0
        
    quality_score = 0.0
    max_score = 10.0
    
    # Check title quality (0-2 points)
    title = card.get("title", "")
    if title:
        if len(title) > 10 and any(word in title.lower() for word in ["als", "mnd", "breathing", "hand", "speech", "swallow"]):
            quality_score += 2.0
        elif len(title) > 5:
            quality_score += 1.0
    
    # Check bullet points quality (0-4 points) 
    bullets = card.get("bullets", [])
    if bullets:
        quality_score += min(len(bullets) * 0.5, 2.0)  # Up to 2 points for having bullets
        
        # Check for actionable content
        actionable_words = ["can", "should", "try", "consider", "ask", "speak", "contact", "use", "practice"]
        actionable_bullets = sum(1 for bullet in bullets if any(word in bullet.lower() for word in actionable_words))
        quality_score += min(actionable_bullets * 0.5, 2.0)  # Up to 2 points for actionable content
    
    # Check source quality (0-2 points)
    source = card.get("source", "")
    if source and len(source) > 10:
        quality_score += 2.0
    elif source:
        quality_score += 1.0
        
    # Check overall relevance (0-2 points)
    content_text = f"{title} {' '.join(bullets)} {source}".lower()
    relevant_terms = ["als", "mnd", "motor neuron", "breathing", "speech", "swallow", "hand", "mobility", "patient", "care"]
    relevance_count = sum(1 for term in relevant_terms if term in content_text)
    if relevance_count >= 3:
        quality_score += 2.0
    elif relevance_count >= 1:
        quality_score += 1.0
    
    return min(quality_score, max_score)

def test_info_card_content_quality():
    """Test the content quality of generated info cards"""
    
    print("\nTesting Information Card Content Quality...")
    print("=" * 50)
    
    # Generate some info cards first
    session_id = f"test-quality-{hash('quality_test') % 10000}"
    
    quality_scores = []
    
    try:
        # Trigger conversation to get info cards
        responses = [
            "I have severe breathing problems at night",
            "Yes, I wake up gasping for air",
            "It happens almost every night now", 
            "I'm using 3 pillows but it's not enough"
        ]
        
        for response in responses:
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
                    for card in data["info_cards"]:
                        quality_score = analyze_card_quality(card)
                        quality_scores.append(quality_score)
                        
                        print(f"Info Card Analysis:")
                        print(f"  Title: {card.get('title', 'N/A')}")
                        print(f"  Bullets: {len(card.get('bullets', []))}")
                        print(f"  Source: {card.get('source', 'N/A')[:50]}...")
                        print(f"  Quality Score: {quality_score:.1f}/10")
                        print()
        
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            print(f"Average Info Card Quality: {avg_quality:.1f}/10")
            
            if avg_quality >= 8.0:
                print("EXCELLENT: Info cards meet high quality standards")
            elif avg_quality >= 6.0:
                print("GOOD: Info cards are acceptable quality")  
            elif avg_quality >= 4.0:
                print("FAIR: Info cards need improvement")
            else:
                print("POOR: Info cards are low quality")
                
            return avg_quality
        else:
            print("No info cards generated for quality analysis")
            return 0.0
            
    except Exception as e:
        print(f"Quality analysis failed: {e}")
        return 0.0

if __name__ == "__main__":
    print("BACKEND QUALITY TEST 2 - Information Card Generation")
    print("=" * 60)
    
    # Test info card generation
    generation_results = test_info_card_generation()
    
    # Test info card quality 
    quality_score = test_info_card_content_quality()
    
    # Overall assessment
    generation_success_rate = sum(1 for r in generation_results if r["success"]) / len(generation_results) * 100
    
    print("\n" + "=" * 60)
    print("OVERALL TEST 2 ASSESSMENT")
    print(f"Info Card Generation: {generation_success_rate:.1f}%")
    print(f"Info Card Quality: {quality_score:.1f}/10")
    
    overall_score = (generation_success_rate + quality_score * 10) / 2
    
    if overall_score >= 85:
        print(f"EXCELLENT: Term completion info quality meets production standards ({overall_score:.1f}%)")
    elif overall_score >= 70:
        print(f"GOOD: Term completion info quality is acceptable ({overall_score:.1f}%)")
    elif overall_score >= 55:
        print(f"FAIR: Term completion info quality needs improvement ({overall_score:.1f}%)")
    else:
        print(f"POOR: Term completion info quality is inadequate ({overall_score:.1f}%)")