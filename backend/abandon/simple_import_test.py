#!/usr/bin/env python3
"""
Simple test to identify import or initialization problems.
"""

try:
    print("Testing basic imports...")
    
    print("1. Testing app.main import...")
    from app.main import app
    print("   [OK] app.main imported successfully")
    
    print("2. Testing conversation manager import...")
    from app.services.conversation_manager import ConversationManager
    print("   [OK] ConversationManager imported successfully")
    
    print("3. Testing PNM scoring import...")
    from app.services.pnm_scoring import PNMScoringEngine, PNMScore
    print("   [OK] PNM scoring imported successfully")
    
    print("4. Testing session management...")
    from app.services.session import SessionState
    print("   [OK] Session management imported successfully")
    
    print("5. Testing storage...")
    from app.services.storage import Storage
    print("   [OK] Storage imported successfully")
    
    print("6. Testing AI scorer...")
    from app.services.ai_scorer import AIScorer
    print("   [OK] AI scorer imported successfully")
    
    print("7. Creating ConversationManager instance...")
    cm = ConversationManager()
    print("   [OK] ConversationManager created successfully")
    
    print("\nAll imports successful! The error is likely in the API routing layer.")
    
except Exception as e:
    print(f"\nERROR during import test: {e}")
    import traceback
    traceback.print_exc()