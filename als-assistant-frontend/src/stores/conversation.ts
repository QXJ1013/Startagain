import { defineStore } from "pinia";
import { conversationsApi } from "../services/api";

export interface Conversation {
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

export interface ConversationMessage {
  id: number;
  turn_index: number;
  role: string;
  text: string;
  meta: any;
  created_at: string;
}

export interface ConversationInfoCard {
  id: number;
  card_type: string;
  card_data: any;
  created_at: string;
}

interface ConversationState {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  currentConversationDetail: {
    conversation: Conversation | null;
    messages: ConversationMessage[];
    infoCards: ConversationInfoCard[];
  };
  loading: boolean;
  error: string | null;
  showInterruptWarning: boolean;
  pendingAction: (() => void) | null;
}

export const useConversationStore = defineStore("conversation", {
  state: (): ConversationState => ({
    conversations: [],
    activeConversation: null,
    currentConversationDetail: {
      conversation: null,
      messages: [],
      infoCards: []
    },
    loading: false,
    error: null,
    showInterruptWarning: false,
    pendingAction: null
  }),

  getters: {
    sortedConversations: (state) => {
      return [...state.conversations].sort((a, b) => {
        // Active conversations first
        if (a.status === 'active' && b.status !== 'active') return -1;
        if (a.status !== 'active' && b.status === 'active') return 1;
        // Then by last activity
        return new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime();
      });
    },

    hasActiveConversation: (state) => {
      return state.activeConversation !== null && state.activeConversation.status === 'active';
    }
  },

  actions: {
    async fetchConversations(token: string, status?: string) {
      this.loading = true;
      this.error = null;
      try {
        const conversations = await conversationsApi.getConversations(token, status);
        this.conversations = conversations;
        
        // Find active conversation
        const active = conversations.find(c => c.status === 'active');
        this.activeConversation = active || null;
      } catch (error: any) {
        this.error = error.message;
        console.error('Failed to fetch conversations:', error);
      } finally {
        this.loading = false;
      }
    },

    async fetchActiveConversation(token: string) {
      try {
        const active = await conversationsApi.getActiveConversation(token);
        this.activeConversation = active;
        return active;
      } catch (error) {
        console.error('Failed to fetch active conversation:', error);
        return null;
      }
    },

    async createConversation(
      token: string, 
      type: 'general' | 'dimension_specific' = 'general',
      dimensionName?: string,
      title?: string
    ) {
      this.loading = true;
      this.error = null;
      try {
        const conversation = await conversationsApi.createConversation(token, type, dimensionName, title);
        this.conversations.unshift(conversation);
        this.activeConversation = conversation;
        return conversation;
      } catch (error: any) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async checkAndWarnInterrupt(token: string, action: () => void) {
      try {
        const warning = await conversationsApi.checkInterruptWarning(token);
        
        if (warning.should_warn && warning.active_conversation) {
          // Store the pending action
          this.pendingAction = action;
          this.showInterruptWarning = true;
          
          // Return the warning details for UI display
          return warning.active_conversation;
        } else {
          // No warning needed, proceed directly
          action();
          return null;
        }
      } catch (error) {
        console.error('Failed to check interrupt warning:', error);
        // On error, proceed without warning
        action();
        return null;
      }
    },

    confirmInterrupt() {
      // Execute the pending action
      if (this.pendingAction) {
        this.pendingAction();
        this.pendingAction = null;
      }
      this.showInterruptWarning = false;
    },

    cancelInterrupt() {
      this.pendingAction = null;
      this.showInterruptWarning = false;
    },

    async updateConversationTitle(token: string, conversationId: string, title: string) {
      try {
        const updated = await conversationsApi.updateConversation(token, conversationId, { title });
        
        // Update in local state
        const index = this.conversations.findIndex(c => c.id === conversationId);
        if (index >= 0) {
          this.conversations[index] = updated;
        }
        
        if (this.activeConversation?.id === conversationId) {
          this.activeConversation = updated;
        }
        
        if (this.currentConversationDetail.conversation?.id === conversationId) {
          this.currentConversationDetail.conversation = updated;
        }
        
        return updated;
      } catch (error: any) {
        this.error = error.message;
        throw error;
      }
    },

    async loadConversationDetail(token: string, conversationId: string) {
      this.loading = true;
      this.error = null;
      try {
        const detail = await conversationsApi.getConversationDetail(token, conversationId);
        
        this.currentConversationDetail = {
          conversation: detail.conversation,
          messages: detail.messages || [],
          infoCards: detail.info_cards || []
        };
        
        return detail;
      } catch (error: any) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async completeConversation(token: string, conversationId: string) {
      try {
        const completed = await conversationsApi.completeConversation(token, conversationId);
        
        // Update in local state
        const index = this.conversations.findIndex(c => c.id === conversationId);
        if (index >= 0) {
          this.conversations[index] = completed;
        }
        
        if (this.activeConversation?.id === conversationId) {
          this.activeConversation = null;
        }
        
        return completed;
      } catch (error: any) {
        this.error = error.message;
        throw error;
      }
    },

    async interruptConversation(token: string, conversationId: string) {
      try {
        const interrupted = await conversationsApi.interruptConversation(token, conversationId);
        
        // Update in local state
        const index = this.conversations.findIndex(c => c.id === conversationId);
        if (index >= 0) {
          this.conversations[index] = interrupted;
        }
        
        if (this.activeConversation?.id === conversationId) {
          this.activeConversation = null;
        }
        
        return interrupted;
      } catch (error: any) {
        this.error = error.message;
        throw error;
      }
    },

    setActiveConversation(conversation: Conversation | null) {
      this.activeConversation = conversation;
    },

    clearCurrentDetail() {
      this.currentConversationDetail = {
        conversation: null,
        messages: [],
        infoCards: []
      };
    },
    
    clearAll() {
      this.conversations = [];
      this.activeConversation = null;
      this.currentConversationDetail = {
        conversation: null,
        messages: [],
        infoCards: []
      };
      this.loading = false;
      this.error = null;
      this.pendingAction = null;
      this.showInterruptWarning = false;
    }
  }
});