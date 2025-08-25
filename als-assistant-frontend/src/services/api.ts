// Minimal API client using fetch; no axios needed.
const API_BASE = import.meta.env.VITE_API_BASE as string || 'http://localhost:8000';

function headers(sessionId: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Session-Id": sessionId
  };
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
  getNextQuestion(sessionId: string, userResponse?: string) {
    const body = userResponse ? { user_response: userResponse } : {};
    return http<ConversationResponse>("/chat/conversation", {
      method: "POST", 
      headers: headers(sessionId),
      body: JSON.stringify(body)
    });
  },

  // Get current PNM awareness profile
  getPNMProfile(sessionId: string) {
    return http<{
      profile: PNMProfile | null;
      suggestions: string[];
      scores: PNMScore[];
    }>("/chat/pnm-profile", {
      method: "GET",
      headers: headers(sessionId)
    });
  },

  // Legacy endpoints for backward compatibility
  route(sessionId: string, text: string) {
    return http<{
      session_id: string, current_pnm: string|null, current_term: string|null
    }>("/chat/route", {
      method: "POST",
      headers: headers(sessionId),
      body: JSON.stringify({ text })
    });
  },

  getQuestion(sessionId: string) {
    return http<{ id: string; type: "main"|"followup"; text: string; pnm?: string; term?: string; followups?: string[]; }>(
      "/chat/question", { method: "GET", headers: headers(sessionId) }
    );
  },

  answer(sessionId: string, text: string) {
    return http<{
      next_state: "main"|"followup"|"scored"|"done";
      turn_index: number;
      current_pnm?: string|null;
      current_term?: string|null;
      scored?: any;
      info_cards?: Array<{title:string;bullets:string[];url?:string;source?:string;}>;
    }>("/chat/answer", {
      method: "POST",
      headers: headers(sessionId),
      body: JSON.stringify({ text, request_info: true })
    });
  },

  state(sessionId: string) {
    return http<any>("/chat/state", { method: "GET", headers: headers(sessionId) });
  },

  scores(sessionId: string) {
    return http<{ term_scores:any[]; dimension_scores:any[] }>(
      "/chat/scores", { method:"GET", headers: headers(sessionId) }
    );
  },

  finish(sessionId: string) {
    return http<{ results: any[] }>(
      "/chat/finish", { method:"POST", headers: headers(sessionId), body: JSON.stringify({ commit: true }) }
    );
  },

  health() {
    return http<any>("/health/readyz", { method:"GET" });
  }
};
