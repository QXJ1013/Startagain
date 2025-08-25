#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug API step by step
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8002"

def debug_api():
    """Debug API step by step"""
    
    session_id = "debug-api-new"
    
    print("API Debug Test")
    print("=" * 50)
    
    # Step 1: Route
    print("Step 1: Routing...")
    route_response = requests.post(
        f"{BASE_URL}/chat/route",
        headers={
            "X-Session-Id": session_id,
            "Content-Type": "application/json"
        },
        json={"text": "I need help with emergency planning"}
    )
    
    print(f"Route status: {route_response.status_code}")
    if route_response.status_code == 200:
        route_data = route_response.json()
        print(f"Route data: {route_data}")
    else:
        print(f"Route error: {route_response.text}")
        return
    
    # Step 2: Check state
    print("\nStep 2: Checking state...")
    state_response = requests.get(
        f"{BASE_URL}/chat/state",
        headers={"X-Session-Id": session_id}
    )
    
    print(f"State status: {state_response.status_code}")
    if state_response.status_code == 200:
        state_data = state_response.json()
        print(f"State data: {json.dumps(state_data, indent=2)}")
    else:
        print(f"State error: {state_response.text}")
        return
    
    # Step 3: Get question
    print("\nStep 3: Getting question...")
    question_response = requests.get(
        f"{BASE_URL}/chat/question",
        headers={"X-Session-Id": session_id}
    )
    
    print(f"Question status: {question_response.status_code}")
    print(f"Question response: {question_response.text}")
    
    if question_response.status_code == 200:
        try:
            question_data = question_response.json()
            print(f"Question data: {json.dumps(question_data, indent=2)}")
        except:
            print("Failed to parse question JSON")
    
    # Step 4: Check question bank debug
    print("\nStep 4: Question bank debug...")
    debug_response = requests.get(f"{BASE_URL}/chat/debug-question-bank")
    print(f"Debug status: {debug_response.status_code}")
    if debug_response.status_code == 200:
        debug_data = debug_response.json()
        print(f"Total questions: {debug_data.get('total_questions')}")
        print(f"Sample question: {debug_data.get('first_question_sample')}")

if __name__ == "__main__":
    debug_api()