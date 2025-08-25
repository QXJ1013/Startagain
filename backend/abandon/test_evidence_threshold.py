#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test evidence threshold triggering for info cards
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8002"

def test_evidence_threshold():
    """Test evidence threshold to trigger info card generation"""
    
    session_id = "test-evidence-001"
    
    print("=== TESTING EVIDENCE THRESHOLD FOR INFO CARDS ===")
    
    # Step 1: Route user input
    print("1. INITIAL ROUTING")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
        json={"text": "I have severe trouble breathing at night"}
    )
    
    print(f"Routing: {route_response.status_code}")
    
    # Step 2: Simulate multiple conversation turns to trigger evidence threshold
    print("\n2. BUILDING EVIDENCE (Multiple conversation turns)")
    responses = [
        "Yes, I have severe breathing problems every night",
        "I wake up gasping for air multiple times",
        "It's gotten much worse over the past month", 
        "I'm using 4 pillows but it's still not enough"
    ]
    
    for i, response in enumerate(responses, 1):
        print(f"\nTurn {i}: {response[:50]}...")
        
        conv_response = requests.post(
            f"{BASE_URL}/chat/conversation",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"user_response": response}
        )
        
        if conv_response.status_code == 200:
            conv_data = conv_response.json()
            info_cards = conv_data.get('info_cards', []) or []
            threshold_met = conv_data.get('evidence_threshold_met', False)
            current_pnm = conv_data.get('current_pnm')
            current_term = conv_data.get('current_term')
            
            print(f"  PNM: {current_pnm}, Term: {current_term}")
            print(f"  Info cards: {len(info_cards)}")
            print(f"  Evidence threshold met: {threshold_met}")
            
            if info_cards:
                print("  INFO CARDS GENERATED:")
                for j, card in enumerate(info_cards, 1):
                    title = card.get('title', 'No title')
                    bullets = card.get('bullets', [])
                    pnm = card.get('pnm', 'No PNM')
                    term = card.get('term', 'No term')
                    
                    print(f"    Card {j}: {title}")
                    print(f"      PNM: {pnm}, Term: {term}")
                    print(f"      Bullets: {len(bullets)}")
                    if bullets:
                        print(f"      First bullet: {bullets[0][:80]}...")
                        
                # Break early if we got cards
                break
        else:
            print(f"  Error: {conv_response.status_code}")
    
    # Check final session state
    print("\n3. FINAL SESSION STATE")
    state_response = requests.get(
        f"{BASE_URL}/chat/conversation-state",
        headers={"X-Session-Id": session_id}
    )
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        print(f"Final PNM: {state_data.get('current_pnm')}")
        print(f"Final term: {state_data.get('current_term')}")
        print(f"Turn index: {state_data.get('turn_index')}")
        print(f"Evidence count: {state_data.get('evidence_count')}")

if __name__ == "__main__":
    test_evidence_threshold()