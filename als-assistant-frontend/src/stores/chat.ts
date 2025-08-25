import { defineStore } from "pinia";

interface Message {
  type: 'user' | 'assistant';
  content: string;
  options?: any[];
  multiSelect?: boolean;
  allowTextInput?: boolean;
  transition?: string | null;
  infoCards?: any[] | null;
  timestamp: Date;
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    messages: [] as Message[],
    currentConversationId: null as string | null,
    conversationType: 'general' as 'general' | 'dimension',
    dimensionName: null as string | null,
    questionsAsked: 0,
    maxQuestionsPerTerm: 5,
    currentTermIndex: 0,
    totalTerms: 0,
  }),
  
  actions: {
    addMessage(message: Message) {
      this.messages.push(message);
    },
    
    clearMessages() {
      this.messages = [];
      this.questionsAsked = 0;
      this.currentTermIndex = 0;
    },
    
    startNewConversation(type: 'general' | 'dimension' = 'general', dimension?: string) {
      this.clearMessages();
      this.conversationType = type;
      this.dimensionName = dimension || null;
      this.currentConversationId = `conv_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    },
    
    incrementQuestionCount() {
      this.questionsAsked++;
    },
    
    shouldContinueAssessment(): boolean {
      // Continue if we haven't reached the maximum questions for current term
      return this.questionsAsked < this.maxQuestionsPerTerm;
    },
    
    moveToNextTerm() {
      this.currentTermIndex++;
      this.questionsAsked = 0;
    },
    
    isAssessmentComplete(): boolean {
      return this.currentTermIndex >= this.totalTerms && 
             this.questionsAsked >= this.maxQuestionsPerTerm;
    }
  }
});