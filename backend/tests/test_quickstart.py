# scripts/quick_start.py
"""
Quick start script to verify system is working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Settings
from app.services.storage import Storage
from app.services.session import SessionState
from app.services.lexicon_router import LexiconRouter
from app.services.question_bank import QuestionBank
from app.services.fsm import DialogueFSM


def test_basic_flow():
    """Test basic conversation flow"""
    print("🚀 Testing ALS Assistant System...")
    
    # Initialize
    print("1. Initializing components...")
    settings = Settings()
    storage = Storage()
    
    # Load data
    print("2. Loading lexicon and questions...")
    lexicon_router = LexiconRouter()
    question_bank = QuestionBank(settings.QUESTION_BANK_PATH)
    
    # Create session
    print("3. Creating session...")
    session = SessionState(session_id="test-quickstart")
    
    # Create FSM
    fsm = DialogueFSM(
        store=storage,
        qb=question_bank,
        router=lexicon_router,
        session=session
    )
    
    # Test routing
    print("\n4. Testing routing...")
    test_inputs = [
        "breathing exercises",
        "I need help walking",
        "emergency planning"
    ]
    
    for input_text in test_inputs:
        pnm, term = fsm.route_intent(input_text)
        print(f"   '{input_text}' -> PNM: {pnm}, Term: {term}")
    
    print("\n✅ System is working!")
    return True


if __name__ == "__main__":
    try:
        success = test_basic_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)