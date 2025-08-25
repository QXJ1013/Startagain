#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug the conversation manager directly
"""

import sys
import os

if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add the current directory to the path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.conversation_manager import ConversationManager
from app.services.session import SessionState
from app.services.storage import Storage

def test_conversation_manager_directly():
    """Test the conversation manager directly without the API"""
    
    print("=== TESTING CONVERSATION MANAGER DIRECTLY ===")
    
    # Create conversation manager
    print("1. Creating ConversationManager...")
    try:
        conv_manager = ConversationManager()
        print(f"  ConversationManager created successfully")
        print(f"  Has scoring_engine: {hasattr(conv_manager, 'scoring_engine')}")
        if hasattr(conv_manager, 'scoring_engine'):
            print(f"  Scoring engine type: {type(conv_manager.scoring_engine)}")
    except Exception as e:
        print(f"  ERROR creating ConversationManager: {e}")
        return False
    
    # Create a test session
    print("\n2. Creating test session...")
    try:
        storage = Storage()
        session = SessionState(session_id="direct-test-session")
        session.current_pnm = "Safety"
        session.current_term = "Equipment readiness and proficiency"
        # Save session to database first (required by _process_user_response)
        session.save(storage)
        print(f"  Session created and saved: {session.session_id}")
        print(f"  Current PNM: {session.current_pnm}")
        print(f"  Current Term: {session.current_term}")
        print(f"  Initial PNM scores: {len(getattr(session, 'pnm_scores', []))}")
    except Exception as e:
        print(f"  ERROR creating session: {e}")
        return False
    
    # Test scoring directly
    print("\n3. Testing direct scoring...")
    try:
        user_response = "Yes, I use BiPAP machine every night and monitor my oxygen levels"
        
        print(f"  User response: {user_response}")
        print(f"  Before scoring - session.pnm_scores: {getattr(session, 'pnm_scores', None)}")
        
        # Call the private method that should do the scoring
        if hasattr(conv_manager, '_process_user_response'):
            conv_manager._process_user_response(session, user_response, storage)
            print(f"  After scoring - session.pnm_scores: {getattr(session, 'pnm_scores', None)}")
            print(f"  PNM scores count: {len(getattr(session, 'pnm_scores', []))}")
        else:
            print(f"  ERROR: _process_user_response method not found")
            return False
            
        # Check if any scores were generated
        if hasattr(session, 'pnm_scores') and session.pnm_scores:
            print(f"  SUCCESS: {len(session.pnm_scores)} scores generated!")
            for i, score in enumerate(session.pnm_scores):
                print(f"    Score {i+1}: {score.pnm_level}:{score.domain} = {score.total_score}/16 ({score.percentage:.1f}%)")
        else:
            print(f"  ISSUE: No scores generated")
            
    except Exception as e:
        print(f"  ERROR during scoring test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test saving the session
    print("\n4. Testing session save...")
    try:
        session.save(storage)
        print(f"  Session saved successfully")
        
        # Try to load it back
        loaded_session = SessionState.load(storage, session.session_id)
        print(f"  Session loaded successfully")
        print(f"  Loaded PNM scores count: {len(getattr(loaded_session, 'pnm_scores', []))}")
        
        if hasattr(loaded_session, 'pnm_scores') and loaded_session.pnm_scores:
            print(f"  SUCCESS: Scores persisted and loaded correctly!")
            return True
        else:
            print(f"  ISSUE: Scores not persisted correctly")
            return False
            
    except Exception as e:
        print(f"  ERROR during save/load test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_conversation_manager_directly()
    if success:
        print(f"\nDIRECT TEST SUCCESSFUL: Scoring system works at the core level!")
    else:
        print(f"\nDIRECT TEST FAILED: Core scoring system has issues")