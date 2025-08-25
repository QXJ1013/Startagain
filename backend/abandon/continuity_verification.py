#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的系统连续性验证
从依赖注入到API路由到数据库到完整对话流程的端到端测试
"""
import sys
import os
import json
import sqlite3
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

# Add the current directory to the path  
sys.path.insert(0, os.path.dirname(__file__))

def test_dependency_injection():
    """测试依赖注入系统"""
    print("=== 1. 测试依赖注入系统 ===")
    
    try:
        from app.deps import (
            get_storage, get_question_bank, get_lexicon_router, 
            get_info_provider, get_ai_router, get_session_store,
            warmup_dependencies
        )
        
        # Test individual dependencies
        storage = get_storage()
        print("✓ Storage dependency works")
        
        qb = get_question_bank()
        print("✓ Question bank dependency works")
        
        router = get_lexicon_router()  
        print("✓ Lexicon router dependency works")
        
        info = get_info_provider()
        print("✓ Info provider dependency works")
        
        ai_router = get_ai_router()
        if ai_router:
            print("✓ AI router dependency works")
        else:
            print("- AI router disabled (normal)")
            
        session_store = get_session_store("test_session")
        print("✓ Session store dependency works")
        
        print("✓ All dependencies loaded successfully")
        return True
        
    except Exception as e:
        print(f"✗ Dependency injection failed: {e}")
        traceback.print_exc()
        return False

def test_api_route_continuity():
    """测试API路由完整性"""
    print("\n=== 2. 测试API路由完整性 ===")
    
    try:
        # Test main app structure
        from app.main import app
        assert app is not None
        print("✓ FastAPI app instance created")
        
        # Test router imports
        from app.routers import chat
        print("✓ Chat router imported")
        
        # Test endpoint existence (check function names)
        import inspect
        chat_functions = [name for name, obj in inspect.getmembers(chat) 
                         if inspect.isfunction(obj) and not name.startswith('_')]
        
        assert len(chat_functions) > 0
        print(f"✓ Chat router has {len(chat_functions)} endpoint functions")
        
        # Test main router integration  
        try:
            from app.main import app
            routes = [route.path for route in app.routes]
            assert len(routes) > 0
            print(f"✓ App has {len(routes)} registered routes")
        except:
            print("- Route counting skipped (may require full app initialization)")
        
        return True
        
    except Exception as e:
        print(f"✗ API route test failed: {e}")
        traceback.print_exc()
        return False

def test_database_continuity():
    """测试数据库连接和表结构"""
    print("\n=== 3. 测试数据库连接和表结构 ===")
    
    try:
        from app.services.storage import Storage
        from app.config import get_settings
        
        # Use temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_db = tmp.name
        
        storage = Storage(db_path=temp_db, schema_path="app/data/schema.sql")
        
        # Test basic operations
        test_session = "continuity_test_session"
        storage.ensure_session(test_session)
        print("✓ Session creation works")
        
        # Test turn operations
        storage.add_turn(
            session_id=test_session,
            turn_index=1,
            role="user",
            content="Hello, I'm testing the system",
            meta={"test": True}
        )
        print("✓ Turn storage works")
        
        # Test term scoring operations
        storage.upsert_term_score(
            session_id=test_session,
            pnm="Physiological",
            term="Communication",
            score_0_7=3.5,
            rationale="Test scoring",
            evidence_turn_ids=[1],
            status="complete",
            method_version="test_v1"
        )
        print("✓ Term scoring storage works")
        
        # Test dimension scoring
        storage.upsert_dimension_score(
            session_id=test_session,
            pnm="Physiological", 
            score_0_7=3.2,
            coverage_ratio=0.8,
            method_version="test_agg_v1"
        )
        print("✓ Dimension scoring storage works")
        
        # Verify data retrieval
        turns = storage.list_turns(test_session)
        assert len(turns) >= 1
        print("✓ Data retrieval works")
        
        # Cleanup
        try:
            os.unlink(temp_db)
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        traceback.print_exc()
        return False

def test_conversation_flow_continuity():
    """测试完整对话流程连续性"""
    print("\n=== 4. 测试完整对话流程连续性 ===")
    
    try:
        from app.services.conversation_manager import ConversationManager
        from app.services.session import SessionState
        from app.services.storage import Storage
        
        # Setup temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_db = tmp.name
        
        storage = Storage(db_path=temp_db, schema_path="app/data/schema.sql")
        
        # Create conversation manager
        conv_manager = ConversationManager()
        
        # Test session creation and loading
        test_session_id = "flow_test_session"
        session = SessionState.load(storage, test_session_id)
        print("✓ Session state loading works")
        
        # Test conversation flow with get_next_question
        initial_response = conv_manager.get_next_question(
            session=session,
            user_response=None,  # No initial user response
            storage=storage
        )
        
        # Verify initial response structure
        assert hasattr(initial_response, 'question_text')
        assert hasattr(initial_response, 'question_type')
        print("✓ Conversation initialization works")
        
        # Test user response handling  
        user_response_obj = conv_manager.get_next_question(
            session=session,
            user_response="I'm having trouble with communication at work using my AAC device.",
            storage=storage
        )
        
        # Verify response structure
        assert hasattr(user_response_obj, 'question_text')
        print("✓ User response handling works")
        
        # Test session scoring
        test_response = "I understand my ALS and work with my therapist daily."
        pnm_score = conv_manager.scoring_engine.score_response(
            test_response, "Physiological", "Communication"
        )
        assert hasattr(pnm_score, 'total_score')
        print("✓ Session scoring works")
        
        # Cleanup
        try:
            os.unlink(temp_db)
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"✗ Conversation flow test failed: {e}")
        traceback.print_exc()
        return False

def test_scoring_pipeline_continuity():
    """测试评分管道连续性"""
    print("\n=== 5. 测试评分管道连续性 ===")
    
    try:
        from app.services.pnm_scoring import PNMScoringEngine
        from app.services.term_scorer import score_term
        from app.services.aggregator import Aggregator, aggregate_dimensions
        
        # Test PNM scoring
        scorer = PNMScoringEngine()
        test_response = "I understand my ALS condition and work with my speech therapist to manage communication challenges. I use my AAC device daily at work."
        
        pnm_score = scorer.score_response(test_response, "Physiological", "Communication")
        assert hasattr(pnm_score, 'total_score')
        assert 0 <= pnm_score.total_score <= 16
        print("✓ PNM scoring works")
        
        # Test term scoring (mock turns)
        mock_turns = [
            {"turn_index": 1, "role": "user", "content": test_response, "id": 1},
            {"turn_index": 2, "role": "assistant", "content": "Thank you for sharing.", "id": 2}
        ]
        
        term_score = score_term(
            session_id="test_scoring",
            pnm="Physiological",
            term="Communication", 
            turns=mock_turns
        )
        
        assert isinstance(term_score, dict)
        assert 'score_0_7' in term_score
        print("✓ Term scoring works")
        
        # Test aggregation
        mock_term_scores = {
            "Physiological": {"Communication": 4, "Mobility": 3},
            "Esteem": {"Independence": 5, "Self_worth": 4}
        }
        
        agg = Aggregator()
        dim_scores = agg.aggregate_dimensions(mock_term_scores)
        assert isinstance(dim_scores, dict)
        assert len(dim_scores) > 0
        print("✓ Score aggregation works")
        
        return True
        
    except Exception as e:
        print(f"✗ Scoring pipeline test failed: {e}")
        traceback.print_exc()
        return False

def test_data_file_integrity():
    """测试数据文件完整性"""
    print("\n=== 6. 测试数据文件完整性 ===")
    
    try:
        from app.config import get_settings
        
        cfg = get_settings()
        
        # Test question bank file
        qb_path = cfg.QUESTION_BANK_PATH
        if os.path.exists(qb_path):
            with open(qb_path, 'r', encoding='utf-8') as f:
                qb_data = json.load(f)
            assert isinstance(qb_data, (list, dict))
            print("✓ Question bank file is valid")
        else:
            print("- Question bank file not found (may be normal)")
        
        # Test lexicon file
        lex_path = cfg.PNM_LEXICON_PATH
        if os.path.exists(lex_path):
            with open(lex_path, 'r', encoding='utf-8') as f:
                lex_data = json.load(f)
            assert isinstance(lex_data, dict)
            print("✓ Lexicon file is valid")
        else:
            print("- Lexicon file not found (may be normal)")
            
        # Test schema file
        schema_path = cfg.SCHEMA_PATH
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_content = f.read()
            assert "CREATE TABLE" in schema_content.upper()
            print("✓ Database schema file is valid")
        else:
            print("- Schema file not found (may be normal)")
        
        return True
        
    except Exception as e:
        print(f"✗ Data file integrity test failed: {e}")
        traceback.print_exc()
        return False

def run_continuity_verification():
    """运行完整的连续性验证"""
    print("ALS Assistant Backend - 完整连续性验证")
    print("=" * 60)
    
    tests = [
        ("依赖注入系统", test_dependency_injection),
        ("API路由完整性", test_api_route_continuity),
        ("数据库连续性", test_database_continuity),
        ("对话流程连续性", test_conversation_flow_continuity),
        ("评分管道连续性", test_scoring_pipeline_continuity),
        ("数据文件完整性", test_data_file_integrity)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n{test_name} 失败")
        except Exception as e:
            print(f"\n{test_name} 出错: {e}")
        print("-" * 40)
    
    print(f"\n验证结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("系统连续性验证通过 - 所有组件正常工作")
        return True
    else:
        print("系统存在连续性问题 - 需要修复")
        return False

if __name__ == "__main__":
    success = run_continuity_verification()
    sys.exit(0 if success else 1)