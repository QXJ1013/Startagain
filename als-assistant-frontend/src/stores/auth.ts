import { defineStore } from "pinia";
import { useChatStore } from './chat';
import { useSessionStore } from './session';
// Removed unused conversation store import

interface User {
  id: string;
  email: string;
  display_name: string;
  created_at?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    token: localStorage.getItem("auth_token"),
    isAuthenticated: !!localStorage.getItem("auth_token"),
    loading: false,
    error: null
  }),

  getters: {
    currentUser: (state) => state.user,
    authToken: (state) => state.token,
    userId: (state) => state.user?.id || null,
    userEmail: (state) => state.user?.email || null,
    displayName: (state) => state.user?.display_name || null,
  },

  actions: {
    async login(email: string, password: string) {
      this.loading = true;
      this.error = null;
      
      try {
        const url = `${import.meta.env.VITE_API_BASE || ''}/api/auth/login`;
        console.log('[AUTH] Logging in at:', url);
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password })
        });

        console.log('[AUTH] Login response status:', response.status);

        if (!response.ok) {
          let errorMessage = 'Login failed';
          try {
            const error = await response.json();
            errorMessage = error.detail || errorMessage;
            console.error('[AUTH] Login error response:', error);
          } catch (e) {
            errorMessage = `Login failed: ${response.status} ${response.statusText}`;
          }
          throw new Error(errorMessage);
        }

        const data = await response.json();
        
        this.token = data.access_token;
        this.user = {
          id: data.user_id,
          email: data.email,
          display_name: data.display_name,
          created_at: data.created_at
        };
        this.isAuthenticated = true;
        
        // Save token to localStorage
        localStorage.setItem("auth_token", data.access_token);
        
        // Clear old session data and create new user-specific session
        const sessionStore = useSessionStore();
        const chatStore = useChatStore();
        
        // Clear any old session data from localStorage
        const oldKeys = Object.keys(localStorage).filter(k => k.startsWith('als_session'));
        oldKeys.forEach(k => {
          if (!k.includes(data.user_id)) {
            localStorage.removeItem(k);
          }
        });
        
        // Reset session with new user context
        sessionStore.resetSession();
        chatStore.clearMessages();
        
        return data;
      } catch (error: any) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async register(email: string, password: string, displayName?: string) {
      this.loading = true;
      this.error = null;
      
      try {
        const url = `${import.meta.env.VITE_API_BASE || ''}/api/auth/register`;
        console.log('[AUTH] Registering at:', url);
        console.log('[AUTH] Request body:', { email, password: '***', display_name: displayName || email.split('@')[0] });
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            email, 
            password, 
            display_name: displayName || email.split('@')[0]
          })
        });

        console.log('[AUTH] Response status:', response.status);
        console.log('[AUTH] Response ok:', response.ok);

        if (!response.ok) {
          let errorMessage = 'Registration failed';
          try {
            const error = await response.json();
            errorMessage = error.detail || errorMessage;
            console.error('[AUTH] Error response:', error);
          } catch (e) {
            console.error('[AUTH] Could not parse error response:', e);
            errorMessage = `Registration failed: ${response.status} ${response.statusText}`;
          }
          throw new Error(errorMessage);
        }

        const data = await response.json();
        
        this.token = data.access_token;
        this.user = {
          id: data.user_id,
          email: data.email,
          display_name: data.display_name,
          created_at: data.created_at
        };
        this.isAuthenticated = true;
        
        // Save token to localStorage
        localStorage.setItem("auth_token", data.access_token);
        
        // Clear old session data and create new user-specific session
        const sessionStore = useSessionStore();
        const chatStore = useChatStore();
        
        // Clear any old session data from localStorage
        const oldKeys = Object.keys(localStorage).filter(k => k.startsWith('als_session'));
        oldKeys.forEach(k => {
          if (!k.includes(data.user_id)) {
            localStorage.removeItem(k);
          }
        });
        
        // Reset session with new user context
        sessionStore.resetSession();
        chatStore.clearMessages();
        
        return data;
      } catch (error: any) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchCurrentUser() {
      if (!this.token) return null;
      
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE || ''}/api/auth/me`, {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch user');
        }

        const data = await response.json();
        this.user = {
          id: data.user_id,
          email: data.email,
          display_name: data.display_name,
          created_at: data.created_at
        };
        
        return this.user;
      } catch (error) {
        console.error('Failed to fetch current user:', error);
        this.logout();
        return null;
      }
    },

    logout() {
      // Get current user ID before clearing
      const currentUserId = this.user?.id;
      
      this.user = null;
      this.token = null;
      this.isAuthenticated = false;
      localStorage.removeItem("auth_token");
      
      // Clear user-specific session data
      if (currentUserId) {
        localStorage.removeItem(`als_session_${currentUserId}`);
      }
      
      // Clear any old session keys
      const sessionKeys = Object.keys(localStorage).filter(k => k.startsWith('als_session'));
      sessionKeys.forEach(k => localStorage.removeItem(k));
      
      // Clear chat and session stores if they exist
      const chatStore = useChatStore();
      const sessionStore = useSessionStore();
      
      chatStore.clearMessages();
      sessionStore.resetSession();
    },

    async checkAuth() {
      const token = localStorage.getItem("auth_token");
      if (token) {
        this.token = token;
        this.isAuthenticated = true;
        await this.fetchCurrentUser();
      }
    }
  }
});