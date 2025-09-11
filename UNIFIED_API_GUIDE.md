# ALS Assistant - Unified API Guide

## Overview

The ALS Assistant now uses a **unified simple conversation API** that replaces the complex multi-endpoint approach with a single, chat-like interface.

## Patient Needs Framework (PNM)

The system assesses patients across 8 dimensions based on Maslow's hierarchy:

- **Physiological** (2 questions) - Basic physical needs
- **Safety** (6 questions) - Security and safety concerns  
- **Love & Belonging** (6 questions) - Social connections
- **Esteem** (16 questions) - Self-worth and confidence
- **Cognitive** (14 questions) - Understanding and decision-making
- **Aesthetic** (2 questions) - Beauty and harmony needs
- **Self-actualisation** (5 questions) - Personal growth
- **Transcendence** (1 question) - Spiritual needs

**Total: 92 questions across 25 specific terms**

## API Endpoints

### Authentication
```
POST /api/auth/register  - Register new user
POST /api/auth/login     - User login
GET  /api/auth/me        - Get current user
POST /api/auth/verify    - Verify token
```

### Unified Conversation
```
POST /chat/conversation  - Main conversation endpoint (replaces all chat endpoints)
GET  /chat/health        - API health check
```

### Conversation Management
```
GET    /api/conversations           - List user conversations
POST   /api/conversations           - Create new conversation
GET    /api/conversations/{id}      - Get conversation details
PUT    /api/conversations/{id}      - Update conversation
DELETE /api/conversations/{id}      - Delete conversation
```

## Main Conversation API

### Request Format
```typescript
POST /chat/conversation
Headers:
  Authorization: Bearer <token>
  X-Conversation-Id: <optional-conversation-id>
  
Body:
{
  "user_response": "I'm concerned about my symptoms",
  "dimension_focus": "Safety",        // optional
  "request_info": true               // request info cards
}
```

### Response Format
```typescript
{
  // Core response
  "question_text": "How are you managing with daily activities?",
  "question_type": "main",
  "options": [
    {"value": "good", "label": "Managing well"},
    {"value": "difficult", "label": "Having difficulties"}
  ],
  "allow_text_input": true,
  
  // Optional fields
  "transition_message": "Let's explore this further...",
  "info_cards": [
    {
      "title": "ALS Support Information",
      "bullets": ["Connect with support groups", "Discuss with healthcare team"]
    }
  ],
  
  // State tracking
  "current_pnm": "Safety",
  "current_term": "Daily activities",
  "fsm_state": "ASK_QUESTION",
  "turn_index": 3,
  
  // Dialogue mode
  "dialogue_mode": true,
  "dialogue_content": "I understand your concerns...",
  "should_continue_dialogue": true,
  
  // Metadata
  "conversation_id": "conv_20231201_abc123",
  "next_state": "continue"
}
```

## Frontend Integration

The frontend should only use the unified conversation endpoint:

### Before (Complex)
```typescript
// Multiple endpoints causing confusion
api.route(conversationId, text, token)
api.getQuestion(conversationId, token)  
api.answer(conversationId, text, requestInfo, token)
api.getNextQuestion(conversationId, userResponse, dimensionFocus, token)
```

### After (Simple)
```typescript
// Single unified endpoint
api.conversation(conversationId, userResponse, dimensionFocus, token)
```

## Key Features

### 1. **Simple Chat-Like Interface**
- Single endpoint for all conversation needs
- Natural request/response flow
- Automatic conversation management

### 2. **Dual Mode Support**
- **Dialogue Mode (80%)**: Natural conversation flow
- **Assessment Mode (20%)**: Structured questions with options

### 3. **Automatic State Management**
- Turn tracking
- PNM/term progression
- FSM state transitions
- Score accumulation

### 4. **Smart Response Generation**
- Context-aware question selection
- Info card integration
- Natural dialogue responses

## Migration Guide

### Backend Changes
1. ✅ Created `chat_unified.py` with single `/chat/conversation` endpoint
2. ✅ Updated `main.py` to use unified router
3. ✅ Simplified conversation logic

### Frontend Changes Needed
1. Update `api.ts` to use unified endpoint
2. Simplify Chat.vue conversation logic
3. Remove unused API methods
4. Update error handling

### Database
- ✅ Uses existing DocumentStorage
- ✅ Compatible with current schema
- ✅ Maintains conversation history

## Testing

Test the API with:
```bash
cd backend
python test_conversation_flow.py
```

Expected flow:
1. Register user → Get token
2. POST /chat/conversation → Get first question
3. Continue conversation → Get responses
4. Automatic mode switching (dialogue ↔ assessment)

## Benefits

1. **Simplified Architecture**: One endpoint instead of many
2. **Reduced Frontend Complexity**: No more routing confusion
3. **Better UX**: Natural chat-like experience
4. **Maintainable**: Easier to debug and extend
5. **Unified State**: Consistent conversation management

## Next Steps

1. Update frontend to use unified API
2. Test complete user journey
3. Add advanced dialogue features
4. Implement scoring integration
5. Add comprehensive logging

The unified API provides a much simpler, more maintainable approach that feels like a natural conversation while maintaining the sophisticated assessment capabilities.