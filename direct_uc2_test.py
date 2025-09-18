#!/usr/bin/env python3
"""
Direct test of UC2 logic without web API
"""
import asyncio
import sys
sys.path.append('backend')

from app.services.enhanced_dialogue import ConversationModeManager, ConversationContext
from app.services.question_bank import QuestionBank
from app.services.ai_routing import AIRouter
from app.services.storage import DocumentStorage, ConversationDocument
from app.config import get_settings

async def test_uc2_direct():
    print("🔍 Direct UC2 Test")

    # Initialize components
    settings = get_settings()
    qb = QuestionBank(settings.QUESTION_BANK_PATH)
    ai_router = AIRouter()
    storage = DocumentStorage()

    # Create a conversation
    conv = ConversationDocument(
        id="test_conv",
        user_id="test_user",
        type="dimension",
        dimension="Aesthetic",
        status="active",
        title="Direct Test",
        messages=[],
        assessment_state={},
        created_at="2025-09-18",
        updated_at="2025-09-18"
    )

    # Initialize conversation mode manager
    mode_manager = ConversationModeManager(qb, ai_router)

    # Test the progression that causes the exception
    test_inputs = ["Start", "first", "second", "third"]

    for i, user_input in enumerate(test_inputs):
        print(f"\n=== Step {i+1}: {user_input} ===")

        try:
            # Create context
            context = ConversationContext(
                conversation=conv,
                user_input=user_input,
                turn_count=i+1,
                ai_router=ai_router
            )

            # Process with mode manager
            response = await mode_manager.process_conversation(context)

            print(f"✅ Response: type={response.response_type}, mode={response.mode}")
            print(f"   Current PNM: {response.current_pnm}")
            print(f"   Current term: {response.current_term}")
            print(f"   Content: {response.content[:60]}...")

        except Exception as e:
            print(f"❌ EXCEPTION at step {i+1}: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            break

    # Show final assessment state
    print(f"\n=== Final Assessment State ===")
    for key, value in conv.assessment_state.items():
        if 'Aesthetic' in key or 'temp_scores' in key or 'term' in key:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(test_uc2_direct())