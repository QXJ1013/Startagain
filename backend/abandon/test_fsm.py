#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test FSM directly to debug question selection issues
"""

import sys
import logging
from app.services.question_bank import QuestionBank
from app.services.lexicon_router import LexiconRouter
from app.services.session import SessionState
from app.services.storage import Storage
from app.services.fsm import DialogueFSM
from app.config import get_settings

# Set up logging
logging.basicConfig(level=logging.DEBUG)

def test_fsm():
    """Test FSM functionality"""
    
    cfg = get_settings()
    storage = Storage()
    qb = QuestionBank(cfg.QUESTION_BANK_PATH)
    router = LexiconRouter(cfg.PNM_LEXICON_PATH)
    
    # Create session state
    session = SessionState("test-fsm-debug")
    session.current_pnm = "Cognitive"
    session.current_term = "Planning & organisation" 
    session.fsm_state = "ASK_MAIN"
    session.asked_qids = []
    
    print("FSM Test")
    print(f"Session: {session.session_id}")
    print(f"Current: {session.current_pnm} -> {session.current_term}")
    print(f"FSM State: {session.fsm_state}")
    
    # Create FSM
    fsm = DialogueFSM(storage, qb, router, session)
    
    # Try to get current question
    print(f"\nTrying to get current question...")
    question = fsm.get_current_question()
    
    print(f"Question result: {question}")
    if question:
        print(f"  ID: {question.get('id')}")
        print(f"  Type: {question.get('type')}")
        print(f"  Text: {question.get('text', '')[:80]}...")
        
        # Test answering
        print(f"\nAnswering question...")
        next_state = fsm.receive_answer("Yes, I have a good emergency plan", {"confidence": 4})
        print(f"Next state: {next_state}")
        
        # Try to get next question
        question2 = fsm.get_current_question()
        print(f"\nSecond question: {question2}")
        if question2:
            print(f"  ID: {question2.get('id')}")
            print(f"  Type: {question2.get('type')}")
            print(f"  Text: {question2.get('text', '')[:80]}...")
    
    return question is not None

if __name__ == "__main__":
    success = test_fsm()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")