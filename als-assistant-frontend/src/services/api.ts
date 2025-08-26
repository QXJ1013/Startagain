// Minimal API client using fetch; no axios needed.
const API_BASE = import.meta.env.VITE_API_BASE as string || 'http://localhost:8001';

function headers(sessionId: string, token?: string | null): HeadersInit {
  const hdrs: HeadersInit = {
    "Content-Type": "application/json",
    "X-Session-Id": sessionId
  };
  
  // Add authorization header if token is provided
  if (token) {
    hdrs["Authorization"] = `Bearer ${token}`;
  }
  
  return hdrs;
}

async function http<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText}: ${text || path}`);
  }
  return res.json() as Promise<T>;
}

// Updated API interface for PNM awareness assessment system
interface ConversationResponse {
  question_text: string;
  question_type: "main" | "followup";
  options: Array<{value: string; label: string}>;
  allow_text_input: boolean;
  transition_message?: string;
  info_cards?: Array<{title: string; bullets: string[]; url?: string; source?: string}>;
  evidence_threshold_met: boolean;
  current_pnm?: string;
  current_term?: string;
  fsm_state?: string;
}

interface PNMScore {
  pnm_level: string;
  domain: string;
  awareness_score: number;
  understanding_score: number;
  coping_score: number;
  action_score: number;
  total_score: number;
  percentage: number;
}

interface PNMProfile {
  overall: {
    score: number;
    possible: number;
    percentage: number;
    level: string;
    domains_assessed: number;
  };
  [key: string]: any;
}

export const api = {
  // Start or continue conversation
  getNextQuestion(sessionId: string, userResponse?: string, dimensionFocus?: string, token?: string | null) {
    const body: any = {};
    if (userResponse) body.user_response = userResponse;
    if (dimensionFocus) body.dimension_focus = dimensionFocus;
    
    return http<ConversationResponse>("/chat/conversation", {
      method: "POST", 
      headers: headers(sessionId, token),
      body: JSON.stringify(body)
    });
  },

  // Get current PNM awareness profile
  getPNMProfile(sessionId: string, token?: string | null) {
    return http<{
      profile: PNMProfile | null;
      suggestions: string[];
      scores: PNMScore[];
    }>("/chat/pnm-profile", {
      method: "GET",
      headers: headers(sessionId, token)
    });
  },

  // Legacy endpoints for backward compatibility
  route(sessionId: string, text: string, token?: string | null) {
    return http<{
      session_id: string, current_pnm: string|null, current_term: string|null
    }>("/chat/route", {
      method: "POST",
      headers: headers(sessionId, token),
      body: JSON.stringify({ text })
    });
  },

  getQuestion(sessionId: string, token?: string | null) {
    return http<{ id: string; type: "main"|"followup"; text: string; pnm?: string; term?: string; followups?: string[]; }>(
      "/chat/question", { method: "GET", headers: headers(sessionId, token) }
    );
  },

  answer(sessionId: string, text: string, token?: string | null) {
    return http<{
      next_state: "main"|"followup"|"scored"|"done";
      turn_index: number;
      current_pnm?: string|null;
      current_term?: string|null;
      scored?: any;
      info_cards?: Array<{title:string;bullets:string[];url?:string;source?:string;}>;
    }>("/chat/answer", {
      method: "POST",
      headers: headers(sessionId, token),
      body: JSON.stringify({ text, request_info: true })
    });
  },

  state(sessionId: string, token?: string | null) {
    return http<any>("/chat/state", { method: "GET", headers: headers(sessionId, token) });
  },

  scores(sessionId: string, token?: string | null) {
    return http<{ term_scores:any[]; dimension_scores:any[] }>(
      "/chat/scores", { method:"GET", headers: headers(sessionId, token) }
    );
  },

  finish(sessionId: string, token?: string | null) {
    return http<{ results: any[] }>(
      "/chat/finish", { method:"POST", headers: headers(sessionId, token), body: JSON.stringify({ commit: true }) }
    );
  },

  health() {
    return http<any>("/health/readyz", { method:"GET" });
  }
};

// Conversation history API
interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  conversation_type: string;
  dimension_name: string | null;
  status: string;
  session_id: string;
  started_at: string;
  completed_at: string | null;
  last_activity: string;
  message_count: number;
  info_card_count: number;
  summary: string | null;
  current_pnm?: string;
  current_term?: string;
}

interface Message {
  id: number;
  turn_index: number;
  role: string;
  text: string;
  meta: any;
  created_at: string;
}

interface InfoCard {
  id: number;
  card_type: string;
  card_data: any;
  created_at: string;
}

interface ConversationDetail {
  conversation: Conversation;
  messages?: Message[];
  info_cards?: InfoCard[];
}

interface InterruptWarning {
  should_warn: boolean;
  active_conversation?: {
    id: string;
    title: string;
    type: string;
    dimension: string | null;
    message_count: number;
  };
}

export const conversationsApi = {
  // Get user's conversation list
  getConversations(token: string, status?: string, limit = 50, offset = 0) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    
    return http<Conversation[]>(`/api/conversations?${params}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Create new conversation
  createConversation(token: string, type = 'general', dimensionName?: string, title?: string) {
    return http<Conversation>("/api/conversations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        conversation_type: type,
        dimension_name: dimensionName,
        title: title
      })
    });
  },

  // Get active conversation
  getActiveConversation(token: string) {
    return http<Conversation | null>("/api/conversations/active", {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Check interrupt warning
  checkInterruptWarning(token: string) {
    return http<InterruptWarning>("/api/conversations/check-interrupt", {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Get conversation details
  getConversationDetail(token: string, conversationId: string, includeMessages = true, includeCards = true) {
    const params = new URLSearchParams();
    params.append('include_messages', includeMessages.toString());
    params.append('include_cards', includeCards.toString());
    
    return http<ConversationDetail>(`/api/conversations/${conversationId}?${params}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Update conversation (e.g., edit title)
  updateConversation(token: string, conversationId: string, updates: { title?: string; status?: string }) {
    return http<Conversation>(`/api/conversations/${conversationId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(updates)
    });
  },

  // Complete conversation
  completeConversation(token: string, conversationId: string) {
    return http<Conversation>(`/api/conversations/${conversationId}/complete`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Interrupt conversation
  interruptConversation(token: string, conversationId: string) {
    return http<Conversation>(`/api/conversations/${conversationId}/interrupt`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Get conversation messages
  getConversationMessages(token: string, conversationId: string, limit?: number, offset = 0) {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    
    return http<Message[]>(`/api/conversations/${conversationId}/messages?${params}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Get conversation info cards
  getConversationInfoCards(token: string, conversationId: string) {
    return http<InfoCard[]>(`/api/conversations/${conversationId}/info-cards`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  },

  // Add message to conversation
  addMessage(token: string, conversationId: string, role: 'user' | 'assistant', text: string, meta: any = {}) {
    return http<any>(`/api/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        role,
        text,
        meta
      })
    });
  },

  // Add info card to conversation
  addInfoCard(token: string, conversationId: string, cardType: string, cardData: any) {
    return http<any>(`/api/conversations/${conversationId}/info-cards`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        card_type: cardType,
        card_data: cardData
      })
    });
  }
};
