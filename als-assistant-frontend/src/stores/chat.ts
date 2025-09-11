import { defineStore } from "pinia";

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type: string;
  timestamp: string;
  metadata?: any;
  options?: any[];
  multiSelect?: boolean;
  allowTextInput?: boolean;
  transition?: string | null;
  infoCards?: any[] | null;
  isDialogue?: boolean;
}

interface ConversationState {
  id: string;
  title?: string;
  type: string;
  dimension?: string;
  status: string;
  created_at: string;
  updated_at: string;
  current_pnm?: string;
  current_term?: string;
  fsm_state?: string;
}

interface AssessmentProgress {
  current_pnm?: string;
  current_term?: string;
  fsm_state: string;
  completed_terms: string[];
  completed_dimensions: number;
  total_messages: number;
  can_switch_dimension: boolean;
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    // Conversation Management
    currentConversationId: null as string | null,
    conversations: [] as ConversationState[],
    
    // Messages
    messages: [] as Message[],
    
    // Conversation Type & Settings
    conversationType: 'assessment' as 'assessment' | 'general_chat' | 'dimension',
    dimensionName: null as string | null,
    
    // Assessment Progress
    progress: {
      current_pnm: undefined,
      current_term: undefined,
      fsm_state: 'ROUTE',
      completed_terms: [],
      completed_dimensions: 0,
      total_messages: 0,
      can_switch_dimension: true
    } as AssessmentProgress,
    
    // UI State
    isDialogueMode: false,
    isLoading: false,
    error: null as string | null,
    
    // Legacy compatibility
    questionsAsked: 0,
    maxQuestionsPerTerm: 5,
    currentTermIndex: 0,
    totalTerms: 0,
  }),
  
  getters: {
    // Conversation getters
    activeConversation: (state) => 
      state.conversations.find(c => c.id === state.currentConversationId) || null,
    
    hasActiveConversation: (state) => 
      state.currentConversationId !== null,
    
    // Messages getters
    messageCount: (state) => state.messages.length,
    
    userMessages: (state) => 
      state.messages.filter(m => m.role === 'user'),
    
    assistantMessages: (state) => 
      state.messages.filter(m => m.role === 'assistant'),
    
    // Assessment getters
    assessmentProgress: (state) => {
      const total = state.progress.completed_terms.length + (state.progress.current_term ? 1 : 0);
      return {
        current_pnm: state.progress.current_pnm,
        current_term: state.progress.current_term,
        completed_count: state.progress.completed_terms.length,
        total_count: total,
        progress_percentage: total > 0 ? (state.progress.completed_terms.length / total) * 100 : 0,
        can_switch: state.progress.can_switch_dimension
      };
    },
    
    isAssessmentMode: (state) => 
      state.conversationType === 'assessment' || state.conversationType === 'dimension',
    
    // Legacy compatibility
    questionCount: (state) => state.questionsAsked,
  },
  
  actions: {
    // Conversation Management
    setCurrentConversation(conversationId: string | null) {
      this.currentConversationId = conversationId;
      if (conversationId) {
        // Clear messages when switching conversations
        this.messages = [];
        this.error = null;
      }
    },
    
    addConversation(conversation: ConversationState) {
      const existing = this.conversations.findIndex(c => c.id === conversation.id);
      if (existing >= 0) {
        this.conversations[existing] = conversation;
      } else {
        this.conversations.push(conversation);
      }
    },
    
    updateConversation(conversationId: string, updates: Partial<ConversationState>) {
      const conversation = this.conversations.find(c => c.id === conversationId);
      if (conversation) {
        Object.assign(conversation, updates);
      }
    },
    
    startNewConversation(type: 'assessment' | 'general_chat' | 'dimension' = 'assessment', dimension?: string) {
      this.clearMessages();
      this.conversationType = type;
      this.dimensionName = dimension || null;
      this.currentConversationId = null; // Will be set by API response
      this.resetProgress();
      this.error = null;
    },
    
    // Message Management
    addMessage(message: Message) {
      // Ensure message has required fields
      const fullMessage: Message = {
        id: message.id || this.messages.length + 1,
        role: message.role,
        content: message.content,
        type: message.type || 'response',
        timestamp: message.timestamp || new Date().toISOString(),
        metadata: message.metadata || {}
      };
      
      this.messages.push(fullMessage);
      this.progress.total_messages = this.messages.length;
    },
    
    clearMessages() {
      this.messages = [];
      this.progress.total_messages = 0;
      this.questionsAsked = 0;
      this.currentTermIndex = 0;
    },
    
    updateLastMessage(updates: Partial<Message>) {
      if (this.messages.length > 0) {
        const lastMessage = this.messages[this.messages.length - 1];
        Object.assign(lastMessage, updates);
      }
    },
    
    // Progress Management
    updateProgress(progress: Partial<AssessmentProgress>) {
      Object.assign(this.progress, progress);
      
      // Update legacy fields for compatibility
      if (progress.current_pnm) {
        this.questionsAsked = this.messages.filter(m => 
          m.role === 'user' && m.type === 'answer'
        ).length;
      }
    },
    
    resetProgress() {
      this.progress = {
        current_pnm: undefined,
        current_term: undefined,
        fsm_state: 'ROUTE',
        completed_terms: [],
        completed_dimensions: 0,
        total_messages: 0,
        can_switch_dimension: true
      };
      this.questionsAsked = 0;
      this.currentTermIndex = 0;
    },
    
    // Assessment State
    setAssessmentState(pnm: string | undefined, term: string | undefined, fsmState: string = 'ASK_QUESTION') {
      this.progress.current_pnm = pnm;
      this.progress.current_term = term;
      this.progress.fsm_state = fsmState;
    },
    
    markTermCompleted(term: string) {
      if (!this.progress.completed_terms.includes(term)) {
        this.progress.completed_terms.push(term);
      }
    },
    
    // UI State Management
    setLoading(loading: boolean) {
      this.isLoading = loading;
    },
    
    setError(error: string | null) {
      this.error = error;
    },
    
    setDialogueMode(isDialogue: boolean) {
      this.isDialogueMode = isDialogue;
    },
    
    // Legacy compatibility methods
    incrementQuestionCount() {
      this.questionsAsked++;
    },
    
    shouldContinueAssessment(): boolean {
      return this.questionsAsked < this.maxQuestionsPerTerm;
    },
    
    moveToNextTerm() {
      this.currentTermIndex++;
      this.questionsAsked = 0;
    },
    
    isAssessmentComplete(): boolean {
      return this.currentTermIndex >= this.totalTerms && 
             this.questionsAsked >= this.maxQuestionsPerTerm;
    },
    
    // Utility methods
    getConversationById(id: string): ConversationState | null {
      return this.conversations.find(c => c.id === id) || null;
    },
    
    canSwitchDimension(): boolean {
      return this.progress.can_switch_dimension && !this.isLoading;
    },
    
    getMessagesByType(type: string): Message[] {
      return this.messages.filter(m => m.type === type);
    },
    
    // Batch operations
    loadConversationData(data: {
      conversation: ConversationState;
      messages: Message[];
      progress?: Partial<AssessmentProgress>;
    }) {
      this.addConversation(data.conversation);
      this.setCurrentConversation(data.conversation.id);
      this.messages = data.messages || [];
      
      if (data.progress) {
        this.updateProgress(data.progress);
      }
      
      // Update conversation type based on loaded data
      this.conversationType = data.conversation.type as any;
      this.dimensionName = data.conversation.dimension || null;
    },
    
    // Reset store to initial state
    reset() {
      this.currentConversationId = null;
      this.conversations = [];
      this.clearMessages();
      this.conversationType = 'assessment';
      this.dimensionName = null;
      this.resetProgress();
      this.isDialogueMode = false;
      this.isLoading = false;
      this.error = null;
    }
  }
});