# ALS Assistant Frontend Issues - Solution Summary

## Problems Identified

### 1. Frontend Routing Issue (CRITICAL)
**Problem**: When user types "I feel breathless" or other symptoms, wrong questions are returned.
**Root Cause**: The frontend was checking `messages.value.length === 1` to determine if it's the first message, but a welcome message is added on mount, so the count is already 2.
**Solution**: Changed to check `userMessages.filter(m => m.type === 'user').length === 1`

### 2. Session Persistence Issue  
**Problem**: Sessions persist in the database, causing routing to be skipped on subsequent requests.
**Root Cause**: Backend checks if `current_qid` exists to determine if routing is needed, but persistent sessions already have this set.
**Solution**: Changed routing logic to check `turn_index == 0` or `!current_pnm` instead.

### 3. Question Selection Not Using Routed PNM/Term
**Problem**: Even when routing sets correct PNM/term, wrong questions are selected.
**Suspected Cause**: The question bank might not have matching questions, or the selection logic has bugs.

## Frontend Changes Made

### Chat.vue
```javascript
// Fixed first message detection
const userMessages = messages.value.filter(m => m.type === 'user')
if (userMessages.length === 1) {
    await startConversationWithInput(messageText)
}

// Reset session for new conversations
async function startConversationWithInput(userMessage: string) {
    sessionStore.resetSession()  // Added this
    // ...
}
```

### API Service
```javascript
// Added dimension_focus parameter support
getNextQuestion(sessionId: string, userResponse?: string, dimensionFocus?: string) {
    const body: any = {};
    if (userResponse) body.user_response = userResponse;
    if (dimensionFocus) body.dimension_focus = dimensionFocus;
    // ...
}
```

## Backend Changes Made

### conversation_manager.py
```python
# Improved routing logic
should_route = (
    dimension_focus is not None or
    (user_response and (session.turn_index == 0 or not session.current_pnm))
)

# Added proper term mappings for question bank
dimension_term_map = {
    'Physiological': 'Breathing exercises',
    'Safety': 'Emergency preparedness',
    'Love & Belonging': 'Communication with support network',
    # etc...
}

# Fixed keyword matching for speaking/swallowing
elif any(word in response_lower for word in ['speak', 'talk', 'voice', 'communicat', 'speech']):
    session.current_pnm = 'Love & Belonging'
    session.current_term = 'Communication with support network'
```

## Remaining Issues

1. **Speaking/Swallowing Still Not Working**: Despite routing correctly, wrong questions are returned
2. **Dimension Selection Broken**: All 8 dimensions return the same emergency preparedness question
3. **Scoring Variation**: Confirmed working (not always 5-6)

## Next Steps to Fix

1. **Check Question Bank Content**: Verify questions exist for all PNM/term combinations
2. **Debug Question Selection**: Add more logging to understand why wrong questions are selected
3. **Consider Session Reset**: May need to fully reset session for each new conversation
4. **Test Direct API Calls**: Bypass frontend to isolate backend issues

## Testing Commands

```bash
# Test breathing (WORKS)
curl -X POST http://localhost:8000/chat/conversation \
  -H "X-Session-Id: test_breath" \
  -d '{"user_response": "I feel breathless"}'

# Test speaking (BROKEN)  
curl -X POST http://localhost:8000/chat/conversation \
  -H "X-Session-Id: test_speak" \
  -d '{"user_response": "I have trouble speaking"}'

# Test dimension (BROKEN)
curl -X POST http://localhost:8000/chat/conversation \
  -H "X-Session-Id: test_dim" \
  -d '{"dimension_focus": "Safety"}'
```

## Critical Discovery

The issue appears to be that the question selection logic (`_select_next_question`) is being called but not finding matching questions for the routed PNM/term combinations, causing it to fall back to any available question (which is always the first one - emergency preparedness).

This suggests either:
1. The question bank doesn't have questions for these PNM/term combinations
2. The PNM/term strings don't match exactly (case sensitivity, spaces, etc.)
3. The questions are already marked as "asked" in the session