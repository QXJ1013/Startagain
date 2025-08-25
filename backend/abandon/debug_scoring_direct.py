#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug scoring directly
"""

from app.deps import get_storage, get_question_bank, get_lexicon_router
from app.services.session import SessionState  
from app.services.fsm import DialogueFSM

def test_scoring_directly():
    """Test scoring logic directly"""
    
    storage = get_storage()
    qb = get_question_bank()
    router = get_lexicon_router()
    
    # Create a test session  
    import random
    session_id = f"test-direct-scoring-{random.randint(10000, 99999)}"
    session = SessionState.load(storage, session_id)
    session.current_pnm = "Physiological"
    session.current_term = "Breathing exercises"  # Use the term that actually works
    session.fsm_state = "SCORE_TERM"
    
    # Add some test turns
    storage.ensure_session(session_id)
    storage.add_turn(
        session_id=session_id,
        turn_index=1,
        role="user", 
        content="Yes, I do breathing exercises",
        meta={"confidence": 4}
    )
    storage.add_turn(
        session_id=session_id,
        turn_index=2,
        role="user", 
        content="I practice daily",
        meta={"confidence": 4}
    )
    
    session.turn_index = 2
    session.save(storage)
    
    # Create FSM and test scoring
    fsm = DialogueFSM(storage, qb, router, session)
    
    # Get the item for scoring
    item = qb.choose_for_term(
        pnm=session.current_pnm,
        term=session.current_term,
        asked_ids=[]
    )
    
    if not item:
        print("ERROR: No item found for scoring")
        return
        
    print(f"Testing scoring for: {item.pnm} / {item.term}")
    print(f"Item ID: {item.id}")
    
    try:
        # Call the scoring method directly
        fsm._score_current_term(item=item)
        print("Scoring method completed without error")
        
        # Check if score was created
        scores = storage.list_term_scores(session_id)
        print(f"Term scores created: {len(scores)}")
        
        if scores:
            for score in scores:
                print(f"  Score: {score.get('score_0_7')}/7")
                print(f"  Rationale: {score.get('rationale')}")
                print(f"  Method: {score.get('method_version')}")
        else:
            print("ERROR: No scores were created despite method completing")
            
    except Exception as e:
        print(f"ERROR in scoring method: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scoring_directly()