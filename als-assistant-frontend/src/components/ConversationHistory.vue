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

          <!-- Conversation List -->
          <div v-else class="conversation-list">
            <div 
              v-for="conv in conversations" 
              :key="conv.id"
              class="conversation-item"
              :class="{ 
                active: conv.status === 'active',
                selected: selectedConversation?.id === conv.id 
              }"
              @click="selectConversation(conv)"
            >
              <!-- Status Indicator -->
              <div class="status-indicator" :class="conv.status"></div>
              
              <!-- Conversation Info -->
              <div class="conv-info">
                <div class="conv-title-row">
                  <input 
                    v-if="editingId === conv.id"
                    v-model="editingTitle"
                    @keyup.enter="saveTitle(conv.id)"
                    @keyup.esc="cancelEdit"
                    @click.stop
                    class="title-input"
                    ref="titleInput"
                  />
                  <h4 v-else class="conv-title">
                    {{ conv.title || `Record ${conversations.indexOf(conv) + 1}` }}
                  </h4>
                  
                  <!-- Edit Button -->
                  <button 
                    v-if="editingId !== conv.id"
                    @click.stop="startEdit(conv)"
                    class="edit-btn"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                </div>
                
                <div class="conv-meta">
                  <span class="conv-type">
                    {{ conv.type === 'dimension' ? 
                       `Dimension: ${conv.dimension}` : 
                       conv.type === 'assessment' ? 'Assessment' :
                       'General Chat' }}
                  </span>
                  <span class="conv-date">
                    {{ formatDate(conv.updated_at || conv.created_at || '') }}
                  </span>
                </div>
                
                <div class="conv-stats">
                  <span>{{ conv.message_count || 0 }} messages</span>
                  <span v-if="(conv.info_card_count || 0) > 0">
                    {{ conv.info_card_count }} info cards
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Conversation Detail View -->
          <div v-if="selectedConversation" class="conversation-detail">
            <div class="detail-header">
              <button @click="selectedConversation = null" class="back-btn">
                ← Back to List
              </button>
              <h4>{{ selectedConversation.title || 'Conversation Detail' }}</h4>
            </div>

            <div class="detail-content">
              <!-- Messages -->
              <div v-if="conversationDetail.messages.length > 0" class="messages-section">
                <h5>Messages ({{ conversationDetail.messages.length }})</h5>
                <div 
                  v-for="(msg, idx) in conversationDetail.messages" 
                  :key="msg.id || idx"
                  class="message-item"
                  :class="msg.role"
                >
                  <div class="msg-role">{{ msg.role === 'user' ? 'You' : 'Assistant' }}</div>
                  <div class="msg-text">{{ msg.content || 'No content available' }}</div>
                  <div class="msg-time" v-if="msg.timestamp">{{ new Date(msg.timestamp).toLocaleString() }}</div>
                </div>
              </div>
              <div v-else class="empty-messages">
                <p>No messages in this conversation yet</p>
              </div>

              <!-- Info Cards -->
              <div v-if="conversationDetail.infoCards.length > 0" class="info-cards-section">
                <h5>Information Cards</h5>
                <div 
                  v-for="card in conversationDetail.infoCards" 
                  :key="card.id"
                  class="saved-info-card"
                >
                  <h6>{{ card.card_data.title }}</h6>
                  <ul>
                    <li v-for="(bullet, idx) in card.card_data.bullets" :key="idx">
                      {{ bullet }}
                    </li>
                  </ul>
                  <div v-if="card.card_data.url" class="card-link">
                    <a :href="card.card_data.url" target="_blank">Learn More →</a>
                  </div>
                </div>
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
// Removed unused useChatStore import
// import { conversationsApi } from '../services/api'; // Removed - endpoints no longer exist

const authStore = useAuthStore();
// Removed unused chatStore

const showHistory = ref(false);
const selectedConversation = ref<any>(null);
const editingId = ref<string | null>(null);
const editingTitle = ref('');
const conversations = ref<any[]>([]);
const loading = ref(false);
const conversationDetail = ref<{
  messages: any[];
  infoCards: any[];
}>({
  messages: [],
  infoCards: []
});

// Removed unused activeConvWarning computed

// Load conversations when panel opens
watch(showHistory, async (isOpen) => {
  if (isOpen && authStore.token) {
    await fetchConversations();
  }
});

// Load conversation details when selected
watch(selectedConversation, async (conv) => {
  if (conv && authStore.token) {
    try {
      // Note: Backend conversation endpoints were removed during simplification
      // Using fallback behavior for now
      console.log('Conversation history detail not available - backend endpoints removed');
      conversationDetail.value = {
        messages: [],
        infoCards: []
      };
    } catch (error) {
      console.error('Failed to load conversation detail:', error);
      conversationDetail.value = {
        messages: [],
        infoCards: []
      };
    }
  }
});

// Add missing functions
async function fetchConversations() {
  loading.value = true;
  try {
    // Note: Backend conversation endpoints were removed during simplification
    // Using empty conversation list for now
    console.log('Conversation history not available - backend endpoints removed');
    conversations.value = [];
  } catch (error) {
    console.error('Failed to fetch conversations:', error);
  } finally {
    loading.value = false;
  }
}

function selectConversation(conv: any) {
  selectedConversation.value = conv;
}

function startEdit(conv: any) {
  editingId.value = conv.id;
  editingTitle.value = conv.title || `Record ${conversations.value.indexOf(conv) + 1}`;
  nextTick(() => {
    const input = document.querySelector('.title-input') as HTMLInputElement;
    if (input) {
      input.focus();
      input.select();
    }
  });
}

function cancelEdit() {
  editingId.value = null;
  editingTitle.value = '';
}

async function saveTitle(conversationId: string) {
  if (editingTitle.value.trim() && authStore.token) {
    try {
      // Note: Backend conversation endpoints were removed during simplification
      // Title editing not available for now
      console.log('Conversation title editing not available - backend endpoints removed');
      // Update local state
      const conv = conversations.value.find(c => c.id === conversationId);
      if (conv) {
        conv.title = editingTitle.value.trim();
      }
    } catch (error) {
      console.error('Failed to update conversation title:', error);
    }
  }
  cancelEdit();
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
  gap: 12px;
}

.conversation-item {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  padding-left: 24px;
}

.conversation-item:hover {
  border-color: #0066ff;
  background: #f8f9ff;
}

.conversation-item.selected {
  border-color: #0066ff;
  background: #f0f5ff;
}

.status-indicator {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
}

.status-indicator.active {
  background: #00c851;
}

.status-indicator.completed {
  background: #0066ff;
}

.status-indicator.interrupted {
  background: #ff9800;
}

.conv-info {
  flex: 1;
}

.conv-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.conv-title {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  flex: 1;
}

.title-input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid #0066ff;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 500;
}

.edit-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.conversation-item:hover .edit-btn {
  opacity: 1;
}

.edit-btn svg {
  width: 16px;
  height: 16px;
  stroke: #999;
}

.edit-btn:hover svg {
  stroke: #0066ff;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 12px;
  color: #999;
}

.conv-stats {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  font-size: 13px;
  color: #666;
}

.conversation-detail {
  position: fixed;
  top: 0;
  right: 0;
  width: 600px;
  height: 100vh;
  background: white;
  box-shadow: -2px 0 10px rgba(0,0,0,0.15);
  z-index: 251;  /* Increased z-index */
  display: flex;
  flex-direction: column;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.back-btn {
  background: none;
  border: none;
  color: #0066ff;
  cursor: pointer;
  font-size: 14px;
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.messages-section,
.info-cards-section {
  margin-bottom: 30px;
}

.messages-section h5,
.info-cards-section h5 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
}

.message-item {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
  background: #f5f5f5;
}

.message-item.user {
  background: #e3f2ff;
}

.msg-role {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.msg-text {
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.msg-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.empty-messages {
  padding: 40px 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
}

.saved-info-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.saved-info-card h6 {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
}

.saved-info-card ul {
  margin: 0;
  padding-left: 20px;
}

.saved-info-card li {
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.card-link {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}

.card-link a {
  color: #0066ff;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
}

.card-link a:hover {
  text-decoration: underline;
}

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