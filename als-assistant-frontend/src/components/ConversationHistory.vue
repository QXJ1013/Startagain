<template>
  <div class="conversation-history">
    <!-- History Button in top right -->
    <button 
      @click="showHistory = !showHistory"
      class="history-toggle-btn"
      :class="{ active: showHistory }"
    >
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      History
    </button>

    <!-- History Panel -->
    <Transition name="slide">
      <div v-if="showHistory" class="history-panel">
        <div class="panel-header">
          <h3>Conversation History</h3>
          <button @click="showHistory = false" class="close-btn">×</button>
        </div>

        <div class="panel-content">
          <!-- Loading State -->
          <div v-if="loading" class="loading">
            Loading conversations...
          </div>

          <!-- Empty State -->
          <div v-else-if="conversations.length === 0" class="empty-state">
            <p>No conversations yet</p>
            <p class="hint">Start a new conversation to begin</p>
          </div>

          <!-- Simplified Conversation List -->
          <div v-else class="conversation-list">
            <div
              v-for="conv in conversations"
              :key="conv.id"
              class="conversation-item"
              :class="conv.status"
              @click="openConversation(conv)"
            >
              <!-- Simple Item Layout -->
              <div class="conv-header">
                <div class="status-dot" :class="conv.status"></div>
                <h4 class="conv-title">
                  {{ conv.title || `Chat ${conversations.indexOf(conv) + 1}` }}
                </h4>
                <span class="conv-date">
                  {{ formatDate(conv.updated_at || conv.created_at || '') }}
                </span>
              </div>

              <div class="conv-meta">
                <span class="conv-type">
                  {{ conv.type === 'dimension' ? `${conv.dimension} Assessment` :
                     conv.type === 'assessment' ? 'Assessment' : 'General Chat' }}
                </span>
                <span class="conv-stats">
                  💬 {{ conv.message_count || 0 }}
                  <span v-if="conv.info_card_count">• 📋 {{ conv.info_card_count }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Interrupt dialog functionality moved to Data.vue -->
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { useAuthStore } from '../stores/auth';
import { conversationsApi } from '../services/api';

const authStore = useAuthStore();
// Removed unused chatStore

const showHistory = ref(false);
const conversations = ref<any[]>([]);
const loading = ref(false);

// Load conversations when panel opens
watch(showHistory, async (isOpen) => {
  if (isOpen && authStore.token) {
    await fetchConversations();
  }
});

// Add missing functions
async function fetchConversations() {
  loading.value = true;
  try {
    if (!authStore.token) {
      conversations.value = [];
      return;
    }

    // Fetch conversations from backend API
    const response = await conversationsApi.getConversations(
      authStore.token,
      undefined, // No status filter
      20,        // Limit
      0          // Offset
    );

    conversations.value = response.conversations.map(conv => ({
      id: conv.id,
      title: conv.title || `${conv.type === 'dimension' ? conv.dimension + ' Assessment' : 'General Chat'}`,
      type: conv.type,
      dimension: conv.dimension,
      status: conv.status,
      created_at: conv.created_at,
      updated_at: conv.updated_at,
      message_count: conv.message_count,
      last_message_at: conv.last_message_at,
      current_pnm: conv.current_pnm,
      current_term: conv.current_term
    }));

    console.log(`✅ Loaded ${conversations.value.length} conversations`);
  } catch (error) {
    console.error('Failed to fetch conversations:', error);
    conversations.value = [];
  } finally {
    loading.value = false;
  }
}

function openConversation(conv: any) {
  // Simple action - just emit or navigate to the conversation
  // This would typically emit an event to parent component or use router
  console.log('Opening conversation:', conv.id);
  // You could add router navigation here if needed
  // router.push(`/chat/${conv.id}`)
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  const now = new Date();
  const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
  
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffHours < 48) return 'Yesterday';
  if (diffHours < 168) return `${Math.floor(diffHours / 24)}d ago`;
  
  return date.toLocaleDateString();
}
</script>

<style scoped>
.conversation-history {
  position: relative;
}

.history-toggle-btn {
  position: fixed;
  top: 20px;
  right: 80px;  /* Moved left to avoid overlap with other icons */
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.3s ease;
  z-index: 150;  /* Increased z-index to ensure visibility */
}

.history-toggle-btn:hover {
  background: #f5f5f5;
  border-color: #0066ff;
}

.history-toggle-btn.active {
  background: #0066ff;
  color: white;
  border-color: #0066ff;
}

.history-toggle-btn svg {
  width: 20px;
  height: 20px;
}

.history-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 400px;
  height: 100vh;
  background: white;
  box-shadow: -2px 0 10px rgba(0,0,0,0.1);
  z-index: 250;  /* Increased z-index */
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.loading,
.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty-state .hint {
  font-size: 14px;
  margin-top: 10px;
  color: #ccc;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.conversation-item:hover {
  border-color: #3b82f6;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.conversation-item.active {
  border-color: #10b981;
  background: #f0fdf4;
}

.conversation-item.completed {
  border-color: #8b5cf6;
  background: #faf5ff;
}

.conv-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.active {
  background: #10b981;
}

.status-dot.completed {
  background: #8b5cf6;
}

.status-dot.paused {
  background: #f59e0b;
}

.conv-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  flex: 1;
}

.conv-date {
  font-size: 11px;
  color: #9ca3af;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.conv-type {
  color: #6b7280;
  font-weight: 500;
}

.conv-stats {
  color: #9ca3af;
}

/* Removed complex conversation detail view styles for simplicity */

/* Interrupt Warning Dialog */
.interrupt-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.interrupt-dialog {
  background: white;
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
}

.interrupt-dialog h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
}

.interrupt-dialog p {
  margin: 12px 0;
  line-height: 1.5;
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.dialog-actions button {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: white;
  border: 1px solid #ddd;
  color: #333;
}

.btn-cancel:hover {
  background: #f5f5f5;
}

.btn-confirm {
  background: #0066ff;
  border: 1px solid #0066ff;
  color: white;
}

.btn-confirm:hover {
  background: #0052d4;
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .history-panel {
    width: 100%;
  }
  
  .conversation-detail {
    width: 100%;
  }
}
</style>