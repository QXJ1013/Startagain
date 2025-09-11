<template>
  <div class="profile-container">
    <div class="profile-header">
      <h1>User Profile</h1>
    </div>
    
    <!-- User Information Card -->
    <div class="info-card">
      <h2>Account Information</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">User ID:</span>
          <span class="value">{{ authStore.userId || 'Not logged in' }}</span>
        </div>
        <div class="info-item">
          <span class="label">Email:</span>
          <span class="value">{{ authStore.userEmail || 'N/A' }}</span>
        </div>
        <div class="info-item">
          <span class="label">Display Name:</span>
          <span class="value">{{ authStore.displayName || 'User' }}</span>
        </div>
        <div class="info-item">
          <span class="label">Account Status:</span>
          <span class="value" :class="authStore.isAuthenticated ? 'status-active' : 'status-inactive'">
            {{ authStore.isAuthenticated ? 'Active' : 'Inactive' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Session Information Card -->
    <div class="info-card">
      <h2>Session Information</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">Session ID:</span>
          <code class="code-value">{{ sessionStore.sessionId }}</code>
        </div>
        <div class="info-item">
          <span class="label">Current PNM:</span>
          <span class="value">{{ sessionStore.currentPnm || 'None' }}</span>
        </div>
        <div class="info-item">
          <span class="label">Current Term:</span>
          <span class="value">{{ sessionStore.currentTerm || 'None' }}</span>
        </div>
        <div class="info-item">
          <span class="label">Questions Answered:</span>
          <span class="value">{{ chatStore.questionCount || 0 }}</span>
        </div>
      </div>
    </div>

    <!-- Conversation Statistics -->
    <div class="info-card">
      <h2>Conversation Statistics</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">Active Conversations:</span>
          <span class="value">{{ conversations.length }}</span>
        </div>
        <div class="info-item">
          <span class="label">Total Messages:</span>
          <span class="value">{{ chatStore.messages?.length || 0 }}</span>
        </div>
        <div class="info-item">
          <span class="label">Current Mode:</span>
          <span class="value">{{ chatStore.isDialogueMode ? 'Natural Dialogue' : 'Assessment' }}</span>
        </div>
        <div class="info-item">
          <span class="label">Last Activity:</span>
          <span class="value">{{ formatLastActivity() }}</span>
        </div>
      </div>
    </div>

    <!-- Assessment Scores -->
    <div class="info-card" v-if="hasScores">
      <h2>Assessment Scores</h2>
      <div class="scores-grid">
        <div v-for="(score, dimension) in dimensionScores" :key="dimension" class="score-item">
          <span class="dimension">{{ dimension }}:</span>
          <div class="score-bar">
            <div class="score-fill" :style="{width: `${(score/7)*100}%`}"></div>
          </div>
          <span class="score-value">{{ score.toFixed(1) }}/7</span>
        </div>
      </div>
    </div>

    <!-- System Status -->
    <div class="info-card">
      <h2>System Status</h2>
      <div class="status-grid">
        <div class="status-item">
          <span class="label">API Status:</span>
          <span class="status-indicator" :class="apiStatus.class">{{ apiStatus.text }}</span>
        </div>
        <div class="status-item">
          <span class="label">API Endpoint:</span>
          <code class="code-value">{{ apiEndpoint }}</code>
        </div>
        <div class="status-item">
          <span class="label">Connection:</span>
          <span class="status-indicator" :class="connectionStatus.class">{{ connectionStatus.text }}</span>
        </div>
      </div>
      
      <div class="action-buttons">
        <button class="btn btn-primary" @click="checkHealth">
          Check API Health
        </button>
        <button class="btn btn-secondary" @click="refreshProfile">
          Refresh Profile
        </button>
        <button class="btn btn-danger" @click="clearSession" v-if="authStore.isAuthenticated">
          Clear Session
        </button>
      </div>
    </div>

    <!-- Debug Information (collapsible) -->
    <div class="info-card">
      <div class="debug-header" @click="showDebug = !showDebug">
        <h2>Debug Information</h2>
        <span class="toggle-icon">{{ showDebug ? '▼' : '▶' }}</span>
      </div>
      <pre v-if="showDebug" class="debug-content">{{ debugInfo }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSessionStore } from '../stores/session'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'

// Store references
const sessionStore = useSessionStore()
const authStore = useAuthStore()
const chatStore = useChatStore()
const conversations = ref<any[]>([])

// Component state
const showDebug = ref(false)
const apiStatus = ref({ text: 'Checking...', class: 'status-checking' })
const connectionStatus = ref({ text: 'Unknown', class: 'status-unknown' })
const apiEndpoint = ref('http://localhost:8000')

// Mock dimension scores (replace with actual data)
const dimensionScores = ref({
  Physiological: 3.5,
  Safety: 4.2,
  'Love & Belonging': 2.8,
  Esteem: 3.0,
  'Self-Actualisation': 2.5,
  Cognitive: 2.0,
  Aesthetic: 3.8,
  Transcendence: 1.5
})

const hasScores = computed(() => {
  return Object.keys(dimensionScores.value).length > 0
})

const debugInfo = computed(() => {
  return JSON.stringify({
    auth: {
      isAuthenticated: authStore.isAuthenticated,
      hasToken: !!authStore.token,
      userId: authStore.userId,
      email: authStore.userEmail
    },
    session: {
      sessionId: sessionStore.sessionId,
      currentPnm: sessionStore.currentPnm,
      currentTerm: sessionStore.currentTerm
    },
    chat: {
      messageCount: chatStore.messages?.length || 0,
      questionCount: chatStore.questionCount,
      isDialogueMode: chatStore.isDialogueMode
    },
    conversations: {
      count: conversations.value.length,
      activeId: chatStore.currentConversationId
    }
  }, null, 2)
})

function formatLastActivity() {
  if (chatStore.messages && chatStore.messages.length > 0) {
    const lastMessage = chatStore.messages[chatStore.messages.length - 1]
    if (lastMessage.timestamp) {
      const date = new Date(lastMessage.timestamp)
      return date.toLocaleTimeString()
    }
  }
  return 'No activity'
}

async function checkHealth() {
  try {
    apiStatus.value = { text: 'Checking...', class: 'status-checking' }
    const response = await fetch(`${apiEndpoint.value}/`)
    
    if (response.ok) {
      const data = await response.json()
      apiStatus.value = { text: 'Online', class: 'status-online' }
      connectionStatus.value = { text: 'Connected', class: 'status-online' }
      console.log('API Health:', data)
    } else {
      apiStatus.value = { text: 'Error', class: 'status-error' }
      connectionStatus.value = { text: 'Failed', class: 'status-error' }
    }
  } catch (error) {
    apiStatus.value = { text: 'Offline', class: 'status-offline' }
    connectionStatus.value = { text: 'Disconnected', class: 'status-offline' }
    console.error('Health check failed:', error)
  }
}

async function refreshProfile() {
  // Refresh user data if authenticated
  if (authStore.isAuthenticated && authStore.token) {
    try {
      // You can add an API call here to refresh user data
      await checkHealth()
      
      // Refresh conversation list if needed
      if (authStore.token) {
        try {
          const { conversationsApi } = await import('../services/api')
          const response = await conversationsApi.getConversations(authStore.token)
          conversations.value = response.conversations
        } catch (error) {
          console.error('Failed to fetch conversations:', error)
        }
      }
    } catch (error) {
      console.error('Profile refresh failed:', error)
    }
  }
}

function clearSession() {
  if (confirm('Are you sure you want to clear your session? This will log you out.')) {
    authStore.logout()
    sessionStore.resetSession()
    chatStore.clearMessages()
    window.location.href = '/login'
  }
}

onMounted(() => {
  checkHealth()
})
</script>

<style scoped>
.profile-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.profile-header {
  margin-bottom: 30px;
}

.profile-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.info-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-card h2 {
  font-size: 20px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.value {
  font-size: 16px;
  color: #111827;
  font-weight: 400;
}

.code-value {
  font-family: 'Courier New', monospace;
  background: #f3f4f6;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
}

.status-active {
  color: #10b981;
  font-weight: 600;
}

.status-inactive {
  color: #ef4444;
  font-weight: 600;
}

.scores-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.score-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dimension {
  min-width: 100px;
  font-weight: 500;
  color: #374151;
}

.score-bar {
  flex: 1;
  height: 20px;
  background: #f3f4f6;
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}

.score-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 10px;
  transition: width 0.3s ease;
}

.score-value {
  min-width: 50px;
  text-align: right;
  font-weight: 600;
  color: #1f2937;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-indicator {
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}

.status-online {
  background: #d1fae5;
  color: #065f46;
}

.status-offline {
  background: #fee2e2;
  color: #991b1b;
}

.status-error {
  background: #fef3c7;
  color: #92400e;
}

.status-checking {
  background: #e0e7ff;
  color: #3730a3;
}

.status-unknown {
  background: #f3f4f6;
  color: #6b7280;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover {
  background: #dc2626;
}

.debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.toggle-icon {
  font-size: 14px;
  color: #6b7280;
}

.debug-content {
  margin-top: 16px;
  background: #0b1020;
  color: #d1d5db;
  padding: 16px;
  border-radius: 8px;
  overflow: auto;
  font-size: 13px;
  font-family: 'Courier New', monospace;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style>