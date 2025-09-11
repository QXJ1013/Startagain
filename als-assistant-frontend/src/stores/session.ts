import { defineStore } from "pinia";

function getOrCreateSessionId(): string {
  const k = "als_session_id";
  let sid = localStorage.getItem(k);
  if (!sid) {
    // Prefer Web Crypto API
    sid = (crypto && "randomUUID" in crypto) ? crypto.randomUUID() :
      `sid_${Math.random().toString(36).slice(2)}_${Date.now()}`;
    localStorage.setItem(k, sid);
  }
  return sid;
}

export const useSessionStore = defineStore("session", {
  state: () => ({
    sessionId: getOrCreateSessionId(),
    currentPnm: null as string | null,
    currentTerm: null as string | null,
    fsmState: "ROUTE" as string,
    loading: false,
    error: null as string | null,
    dimensionFocus: null as string | null,
    message: null as string | null,
    dimensionTestSession: null as {
      sessionId: string;
      dimension: string;
      startedAt: Date;
    } | null,
  }),
  actions: {
    setState(pnm: string | null, term: string | null, fsm: string) {
      this.currentPnm = pnm;
      this.currentTerm = term;
      this.fsmState = fsm;
    },
    setError(msg: string | null) { this.error = msg; },
    setLoading(v: boolean) { this.loading = v; },
    setDimensionFocus(dimension: string | null) { this.dimensionFocus = dimension; },
    setMessage(msg: string | null) { 
      this.message = msg;
      // Auto-clear message after 3 seconds
      if (msg) {
        setTimeout(() => {
          if (this.message === msg) this.message = null;
        }, 3000);
      }
    },
    setDimensionTest(sessionId: string, dimension: string) {
      this.dimensionTestSession = {
        sessionId,
        dimension,
        startedAt: new Date()
      };
    },
    clearDimensionTest() {
      this.dimensionTestSession = null;
    },
    resetSession() {
      // Create a new session ID
      const newSid = (crypto && "randomUUID" in crypto) ? crypto.randomUUID() :
        `sid_${Math.random().toString(36).slice(2)}_${Date.now()}`;
      localStorage.setItem("als_session_id", newSid);
      this.sessionId = newSid;
      
      // Reset state
      this.currentPnm = null;
      this.currentTerm = null;
      this.fsmState = "ROUTE";
      this.dimensionFocus = null;
      this.error = null;
      this.message = null;
      this.dimensionTestSession = null;
    },
  }
});
