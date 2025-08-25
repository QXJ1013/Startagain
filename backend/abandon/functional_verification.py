#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick functional verification after code cleanup
Tests key components to ensure nothing was broken
"""
import sys
import os
import sqlite3
import tempfile
from pathlib import Path

# Add the current directory to the path  
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all critical imports still work"""
    try:
        from app.config import get_settings
        from app.services.storage import Storage  
        from app.services.session import SessionState
        from app.services.lexicon_router import LexiconRouter
        from app.services.question_bank import QuestionBank
        from app.services.fsm import DialogueFSM
        from app.services.conversation_manager import ConversationManager
        from app.services.term_scorer import score_term
        from app.services.pnm_scoring import PNMScorer
        from app.services.aggregator import Aggregator
        print("✓ All critical imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_config_loading():
    """Test configuration loading"""
    try:
        from app.config import get_settings
        settings = get_settings()
        assert hasattr(settings, 'APP_NAME')
        assert hasattr(settings, 'CORS_ORIGINS')
        assert hasattr(settings, 'DB_PATH')
        print("✓ Configuration loading works")
        return True
    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        return False

def test_storage_operations():
    """Test basic storage operations"""
    try:
        from app.services.storage import Storage
        
        # Use temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_db = tmp.name
        
        # Create storage with temp DB
        storage = Storage(db_path=temp_db, schema_path="app/data/schema.sql")
        
        # Test session operations
        session_id = "test_session_123"
        storage.ensure_session(session_id)
        
        # Test turn operations
        storage.add_turn(
            session_id=session_id,
            turn_index=1,
            role="user", 
            content="Hello",
            meta={}
        )
        turns = storage.list_turns(session_id)
        assert len(turns) >= 1
        
        # Cleanup - try to delete, but don't fail if can't
        try:
            os.unlink(temp_db)
        except:
            pass  # File may be locked on Windows
        print("✓ Storage operations work")
        return True
    except Exception as e:
        print(f"✗ Storage test failed: {e}")
        return False

def test_pnm_scoring():
    """Test PNM scoring functionality"""
    try:
        from app.services.pnm_scoring import PNMScorer
        
        scorer = PNMScorer()
        
        # Test with sample responses
        test_responses = [
            "I'm struggling with communication using my AAC device at work",
            "I understand my condition and work with my speech therapist",
            "I'm learning about ALS and reading medical information"
        ]
        
        for response in test_responses:
            score = scorer.score_response(response, "Physiological", "Communication")
            assert hasattr(score, 'total_score')
            assert 0 <= score.total_score <= 16
        
        print("✓ PNM scoring functionality works")
        return True
    except Exception as e:
        print(f"✗ PNM scoring test failed: {e}")
        return False

def test_question_bank():
    """Test question bank loading and selection"""
    try:
        from app.services.question_bank import QuestionBank
        
        qb = QuestionBank("app/data/pnm_questions_v2_full.json")
        
        # Test question selection
        item = qb.choose_for_term("Physiological", "Communication", [])
        assert item is not None
        assert hasattr(item, 'main')
        assert hasattr(item, 'followups')
        
        print("✓ Question bank functionality works")
        return True
    except Exception as e:
        print(f"✗ Question bank test failed: {e}")
        return False

def run_verification():
    """Run all verification tests"""
    print("=== System Functional Verification ===")
    print("Testing core functionality after cleanup...")
    print()
    
    tests = [
        ("Critical Imports", test_imports),
        ("Configuration Loading", test_config_loading), 
        ("Storage Operations", test_storage_operations),
        ("PNM Scoring", test_pnm_scoring),
        ("Question Bank", test_question_bank)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                print(f"  Failed: {test_name}")
        except Exception as e:
            print(f"  Error in {test_name}: {e}")
        print()
    
    print("=== Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ ALL TESTS PASSED - System is functional after cleanup")
        return True
    else:
        print("✗ Some tests failed - Manual review needed")
        return False

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)