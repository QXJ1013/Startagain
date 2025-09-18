// Fixed API client with correct endpoints and structures
const API_BASE = import.meta.env.VITE_API_BASE as string || '';

function headers(conversationId?: string, token?: string | null): HeadersInit {
  const hdrs: HeadersInit = {
    "Content-Type": "application/json"
  };
  
  // Add conversation ID header if provided
  if (conversationId) {
    hdrs["X-Conversation-Id"] = conversationId;
  }
  
  // Add authorization header if token is provided
  if (token) {
    hdrs["Authorization"] = `Bearer ${token}`;
  }
  
  return hdrs;
}

async function http<T>(path: string, init: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, init);
    
    // Log for debugging
    console.log(`[API] ${init.method || 'GET'} ${path} - Status: ${res.status}`);
    
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(`[API Error] ${path}:`, text);

      // Check if it's an authentication error with HTML response
      if ((res.status === 401 || res.status === 403) && text.includes('<')) {
        console.error(`[API Auth Error] Got HTML response for auth error on ${path}`);
        throw new Error(`Authentication failed - please refresh and login again`);
      }

      throw new Error(`HTTP ${res.status} ${res.statusText}: ${text || path}`);
    }
    
    const text = await res.text();
    console.log(`[API Raw Response] ${path}:`, text);

    try {
      const data = JSON.parse(text) as T;
      console.log(`[API Response] ${path}:`, data);
      return data;
    } catch (jsonError) {
      console.error(`[API JSON Parse Error] ${path}:`, jsonError);
      console.error(`[API Raw Text] ${path}:`, text);
      throw new Error(`Failed to parse JSON response: ${jsonError}`);
    }
  } catch (error) {
    console.error(`[API Fetch Error] ${path}:`, error);
    throw error;
  }
}

// API interface matching backend's ConversationResponse
interface ConversationResponse {
  // Essential response fields
  question_text: string;
  question_type?: string;
  options?: Array<{value: string; label: string}>;
  allow_text_input?: boolean;
  
  // Optional enhancement fields
  transition_message?: string;
  info_cards?: Array<{title: string; bullets: string[]; url?: string; source?: string}>;
  
  // State tracking
  current_pnm?: string;
  current_term?: string;
  fsm_state?: string;
  turn_index?: number;
  
  // Dialogue mode control
  dialogue_mode?: boolean;
  dialogue_content?: string;
  should_continue_dialogue?: boolean;
  
  // Conversation metadata
  conversation_id: string;
  next_state?: string;
}

export const api = {
  // Unified conversation endpoint - handles all chat interactions
  conversation(conversationId: string, userResponse?: string, dimensionFocus?: string, token?: string | null) {
    const body: any = {
      user_response: userResponse !== undefined ? userResponse : "",
      request_info: true  // Always request info cards
    };
    
    if (dimensionFocus) {
      body.dimension_focus = dimensionFocus;
    }
    
    return http<ConversationResponse>("/chat/conversation", {
      method: "POST",
      headers: headers(conversationId, token),
      body: JSON.stringify(body)
    });
  },

  // Backward compatibility alias
  getNextQuestion(conversationId: string, userResponse?: string, dimensionFocus?: string, token?: string | null) {
    return this.conversation(conversationId, userResponse, dimensionFocus, token);
  },

  // Health check for chat system
  chatHealth() {
    return http<{
      status: string;
      endpoint: string;
      features: string[];
    }>("/chat/health", {
      method: "GET",
      headers: {}
    });
  },

  // Health check
  health() {
    return fetch(`${API_BASE}/`).then(res => res.json());
  }
};

// Conversations API for conversation management (simplified - routes may not exist in backend)
export const conversationsApi = {
  // Create new conversation
  createConversation(token: string, type: 'assessment' | 'general_chat' | 'dimension' = 'assessment', dimension?: string, title?: string) {
    return http<{
      id: string;
      user_id: string;
      title: string;
      type: string;
      dimension?: string;
      status: string;
      created_at: string;
      updated_at: string;
    }>("/conversations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        type: type,
        dimension: dimension,
        title: title
      })
    });
  },

  // Get user's conversations
  getConversations(token: string, status?: string, limit: number = 20, offset: number = 0) {
    const queryParams = new URLSearchParams();
    if (status) queryParams.set('status', status);
    queryParams.set('limit', limit.toString());
    queryParams.set('offset', offset.toString());
    
    return http<{
      conversations: Array<{
        id: string;
        title: string;
        type: string;
        dimension?: string;
        status: string;
        created_at: string;
        updated_at: string;
        message_count: number;
        last_message_at?: string;
        current_pnm?: string;
        current_term?: string;
        fsm_state?: string;
      }>;
      total_count: number;
    }>(`/conversations?${queryParams}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Get active conversation
  getActiveConversation(token: string) {
    return http<{
      id: string;
      title: string;
      type: string;
      dimension?: string;
      status: string;
      created_at: string;
      updated_at: string;
      message_count: number;
      last_message_at?: string;
      current_pnm?: string;
      current_term?: string;
      fsm_state?: string;
    } | null>("/conversations/active", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Get conversation detail with messages
  getConversationDetail(token: string, conversationId: string) {
    return http<{
      id: string;
      user_id: string;
      title?: string;
      type: string;
      dimension?: string;
      status: string;
      created_at: string;
      updated_at: string;
      completed_at?: string;
      assessment_state: any;
      messages: Array<{
        id: number;
        role: 'user' | 'assistant' | 'system';
        content: string;
        type: string;
        timestamp: string;
        metadata?: any;
      }>;
      info_cards: Array<any>;
      metadata: any;
    }>(`/conversations/${conversationId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Add message to conversation
  addMessage(token: string, conversationId: string, role: 'user' | 'assistant' | 'system', content: string, type: string = 'response', metadata?: any) {
    return http<{ success: boolean }>(`/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        role,
        content,
        type,
        metadata: metadata || {}
      })
    });
  },

  // Add info card to conversation
  addInfoCard(token: string, conversationId: string, cardType: string, cardData: any) {
    return http<{ success: boolean }>(`/conversations/${conversationId}/info-cards`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        type: cardType,
        title: cardData.title || '',
        content: cardData
      })
    });
  },

  // Complete conversation
  completeConversation(token: string, conversationId: string) {
    return http<{ success: boolean }>(`/conversations/${conversationId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        status: 'completed'
      })
    });
  },

  // Check interrupt warning
  checkInterruptWarning(token: string) {
    return http<{
      should_warn: boolean;
      active_conversation: any | null;
    }>("/conversations/check-interrupt", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Update conversation (e.g., title)
  updateConversation(token: string, conversationId: string, updates: { title?: string; status?: string }) {
    return http<{
      id: string;
      title?: string;
      type: string;
      status: string;
      updated_at: string;
      message_count?: number;
    }>(`/conversations/${conversationId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(updates)
    });
  },

  // Interrupt conversation
  interruptConversation(token: string, conversationId: string) {
    return http<{
      id: string;
      title?: string;
      type: string;
      status: string;
      updated_at: string;
      message_count?: number;
    }>(`/conversations/${conversationId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        status: 'paused'
      })
    });
  },

  // Get user scores summary
  getUserScoresSummary(token: string) {
    return http<{
      dimensions: Array<{
        name: string;
        score: number;
        assessments_count: number;
      }>;
      term_scores: Array<{
        pnm: string;
        term: string;
        score: number;
        updated_at: string;
      }>;
      total_conversations: number;
      completed_assessments: number;
    }>("/conversations/scores/summary", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });
  }
};

export default api;