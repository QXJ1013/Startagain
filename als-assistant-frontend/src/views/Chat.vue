<template>
  <div class="chat">
    <!-- Conversation History Component -->
    <ConversationHistory />
    
    <!-- Header -->
    <div class="chat-header">
      <h1>💬 ALS Assistant Chat</h1>
      <div class="header-indicators">
        <div class="mode-indicator" v-if="isInDialogueMode">
          <span class="mode-badge dialogue">🗣️ Dialogue Mode (80%)</span>
        </div>
        <div class="mode-indicator" v-else>
          <span class="mode-badge question">📋 Assessment Mode</span>
        </div>
        <div class="stage-indicator" v-if="currentStage">
          <span class="stage-badge">{{ currentStage }}</span>
        </div>
      </div>
    </div>

    <!-- Messages Container -->
    <div class="messages-container" ref="messagesContainer">
      <div v-for="(message, index) in messages" :key="index" class="message" :class="message.type">
        
        <!-- User Message -->
        <div v-if="message.type === 'user'" class="user-message">
          <div class="message-content">{{ message.content }}</div>
          <div class="message-timestamp">{{ formatTimestamp(message.timestamp) }}</div>
        </div>

        <!-- Assistant Message -->
        <div v-else class="assistant-message">
          <!-- Info Cards (displayed first) -->
          <div v-if="message.infoCards" class="info-cards">
            <div v-for="(card, cardIndex) in message.infoCards" :key="cardIndex" class="info-card">
              <div class="card-title">{{ card.title }}</div>
              <div class="card-content">
                <div v-for="(bullet, bulletIndex) in card.bullets" :key="bulletIndex" class="card-bullet">
                  {{ bullet }}
                </div>
              </div>
              <div class="card-disclaimer">
                {{ card.disclaimer || "This advice is based on your responses and internal resources. It does not constitute a diagnosis." }}
              </div>
            </div>
          </div>
          
          <!-- Transition Message -->
          <div v-if="message.transition" class="transition-message">
            {{ message.transition }}
          </div>
          
          <!-- Dialogue or Question Content -->
          <div class="question-content" :class="{ 'dialogue-mode': message.isDialogue }">
            <div class="question-text" :class="{ 'dialogue-text': message.isDialogue }">{{ message.content }}</div>
            
            <!-- Button Options (hide in dialogue mode) -->
            <div v-if="!message.isDialogue && message.options && message.options.length" class="options-container">
              <div class="options-grid" :class="{ 'multi-select': message.multiSelect }">
                <button 
                  v-for="option in message.options"
                  :key="option.value"
                  class="option-btn"
                  :class="{ 
                    selected: isOptionSelected(option.value, message.multiSelect),
                    'multi-select': message.multiSelect 
                  }"
                  @click="selectOption(option, message.multiSelect)"
                >
                  <span v-if="message.multiSelect" class="checkbox">
                    {{ isOptionSelected(option.value, true) ? '☑️' : '☐' }}
                  </span>
                  {{ option.label }}
                </button>
              </div>
              
              <!-- Optional text input (always show in dialogue mode) -->
              <div v-if="message.allowTextInput || message.isDialogue" class="text-input-container">
                <div class="input-label">(Optional additional details)</div>
                <textarea 
                  v-model="supplementaryText" 
                  placeholder="Enter additional details..."
                  rows="2"
                  class="supplement-input"
                ></textarea>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="isLoading" class="loading-message">
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div class="loading-text">{{ loadingText }}</div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <!-- Always show text input for user to type -->
      <div class="text-input-section">
        <div class="input-container">
          <textarea 
            v-model="userInput"
            @keydown.enter.ctrl="sendMessage"
            @keydown.enter.shift="sendMessage"
            @keydown.esc="clearInput"
            placeholder="Describe your situation or enter your response... (Ctrl+Enter or Shift+Enter to send, Esc to clear)"
            rows="3"
            class="main-input"
            :disabled="isLoading"
            ref="mainInputRef"
          ></textarea>
          <button 
            @click="sendMessage" 
            :disabled="!userInput.trim() || isLoading"
            class="send-btn primary"
          >
            Send
          </button>
        </div>
      </div>

      <!-- Action buttons when options are selected -->
      <div v-if="hasCurrentQuestion && hasSelection" class="action-buttons">
        <button 
          @click="submitSelection"
          :disabled="!hasSelection || isLoading"
          class="submit-btn primary"
        >
          Submit selected options
        </button>
        
        <button 
          @click="clearSelection"
          class="clear-btn secondary"
        >
          Clear selection
        </button>
      </div>
    </div>

    <!-- Notification Display -->
    <div v-if="sessionStore.message" class="notification-container">
      <div class="notification-message">
        <span class="notification-icon">ℹ️</span>
        {{ sessionStore.message }}
      </div>
      <button @click="sessionStore.setMessage(null)" class="dismiss-notification">Close</button>
    </div>

    <!-- Error Display -->
    <div v-if="error" class="error-container" :class="`error-${errorType}`">
      <div class="error-message">
        <span class="error-icon">⚠️</span>
        <div class="error-content">
          <div class="error-text">{{ error }}</div>
          <div v-if="retryCount > 0" class="error-retry-info">
            Retry attempt {{ retryCount }}/{{ maxRetries }}
          </div>
        </div>
      </div>
      <div class="error-actions">
        <button v-if="errorType === 'connection' || errorType === 'server'" 
                @click="retryLastOperation" 
                class="retry-error"
                :disabled="retryCount >= maxRetries">
          Retry
        </button>
        <button @click="clearError" class="dismiss-error">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useSessionStore } from '../stores/session'
import { useChatStore } from '../stores/chat'
import { api, conversationsApi } from '../services/api'
import ConversationHistory from '../components/ConversationHistory.vue'
import { useAuthStore } from '../stores/auth'

// State
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const authStore = useAuthStore()
const userInput = ref('')
const supplementaryText = ref('')
const selectedOptions = ref<{value: string, label: string}[]>([])
const currentStage = ref('Processing diagnosis')
const isLoading = ref(false)
const error = ref<string | null>(null)
const messagesContainer = ref<HTMLElement>()
const hasInitialized = ref(false)
const isInDialogueMode = ref(false)
const mainInputRef = ref<HTMLTextAreaElement>()
const loadingText = ref('Analyzing your response...')
const autoFocusInput = ref(true)
const errorType = ref<'connection' | 'auth' | 'validation' | 'server' | 'unknown'>('unknown')
const retryCount = ref(0)
const maxRetries = 3
const lastFailedOperation = ref<(() => Promise<void>) | null>(null)

// Use messages from chat store and transform for display
const messages = computed(() => {
  return chatStore.messages.map(msg => ({
    ...msg,
    // Transform for backward compatibility with template
    type: msg.role,
    options: msg.metadata?.options || msg.options || [],
    multiSelect: msg.metadata?.multiSelect || msg.multiSelect || false,
    allowTextInput: msg.metadata?.allowTextInput || msg.allowTextInput || false,
    transition: msg.metadata?.transition || msg.transition || null,
    infoCards: msg.metadata?.infoCards || msg.infoCards || null,
    isDialogue: msg.metadata?.isDialogue || msg.isDialogue || false
  }))
})

// Computed
const hasCurrentQuestion = computed(() => {
  const lastMessage = messages.value[messages.value.length - 1]
  return lastMessage && lastMessage.role === 'assistant' && lastMessage.options && lastMessage.options.length > 0
})

const hasSelection = computed(() => {
  return selectedOptions.value.length > 0
})

// Methods
function clearInput() {
  userInput.value = ''
}

function focusInput() {
  if (mainInputRef.value) {
    mainInputRef.value.focus()
  }
}

function setLoadingText(text: string) {
  loadingText.value = text
}

function formatTimestamp(timestamp: string): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  // Less than 1 minute
  if (diff < 60000) {
    return 'Just now'
  }
  
  // Less than 1 hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes}m ago`
  }
  
  // Same day
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }
  
  // Different day
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function categorizeError(error: any): 'connection' | 'auth' | 'validation' | 'server' | 'unknown' {
  if (!error) return 'unknown'
  
  const message = error.message?.toLowerCase() || error.toString?.().toLowerCase() || ''
  
  if (message.includes('network') || message.includes('fetch') || message.includes('connection')) {
    return 'connection'
  }
  
  if (message.includes('unauthorized') || message.includes('authentication') || message.includes('token')) {
    return 'auth'
  }
  
  if (message.includes('validation') || message.includes('invalid') || message.includes('required')) {
    return 'validation'
  }
  
  if (message.includes('server') || message.includes('internal')) {
    return 'server'
  }
  
  return 'unknown'
}

function getErrorMessage(type: string): string {
  switch (type) {
    case 'connection':
      return 'Connection issue. Please check your internet connection and try again.'
    case 'auth':
      return 'Authentication failed. Please refresh the page and log in again.'
    case 'validation':
      return 'Invalid input. Please check your message and try again.'
    case 'server':
      return 'Server error. Please try again in a moment.'
    default:
      return 'An unexpected error occurred. Please try again.'
  }
}


function clearError() {
  error.value = null
  errorType.value = 'unknown'
  retryCount.value = 0
  lastFailedOperation.value = null
}

async function retryLastOperation() {
  if (lastFailedOperation.value && retryCount.value < maxRetries) {
    try {
      await lastFailedOperation.value()
      clearError()
    } catch (e: any) {
      errorType.value = categorizeError(e)
      error.value = getErrorMessage(errorType.value)
      retryCount.value++
      console.error('Retry failed:', e)
    }
  }
}

function isOptionSelected(value: string, multiSelect: boolean = false): boolean {
  if (multiSelect) {
    return selectedOptions.value.some(opt => opt.value === value)
  }
  return selectedOptions.value.length > 0 && selectedOptions.value[0].value === value
}

function selectOption(option: {value: string, label: string}, multiSelect: boolean = false) {
  if (multiSelect) {
    const index = selectedOptions.value.findIndex(opt => opt.value === option.value)
    if (index > -1) {
      selectedOptions.value.splice(index, 1)
    } else {
      selectedOptions.value.push(option)
    }
  } else {
    selectedOptions.value = [option]
  }
}

function clearSelection() {
  selectedOptions.value = []
  supplementaryText.value = ''
}

async function sendMessage() {
  if (!userInput.value.trim() || isLoading.value) return
  
  const messageText = userInput.value.trim()
  userInput.value = ''
  
  // Add user message
  chatStore.addMessage({
    id: Date.now(),
    role: 'user',
    content: messageText,
    type: 'text',
    timestamp: new Date().toISOString()
  })
  
  // Check if this is the first real user message in this conversation
  const userMessages = chatStore.messages.filter(m => m.role === 'user')
  if (userMessages.length === 1 && chatStore.conversationType === 'general_chat') {
    // This is the first user message, start conversation with routing
    await startConversationWithInput(messageText)
  } else {
    // Continue existing conversation
    await processUserInput(messageText)
  }
}

async function submitSelection() {
  if (!hasSelection.value || isLoading.value) return
  
  // Combine selected options with supplementary text - use labels for display, values for backend
  const selectedLabels = selectedOptions.value.map(opt => opt.label).join(', ')
  const selectedValues = selectedOptions.value.map(opt => opt.value).join(',')
  
  let displayText = selectedLabels
  let submitText = selectedValues  // Send values to backend for processing
  
  if (supplementaryText.value.trim()) {
    displayText += `\nAdditional details: ${supplementaryText.value.trim()}`
    submitText += `\nAdditional details: ${supplementaryText.value.trim()}`
  }
  
  // Add user message showing their selection with full labels
  chatStore.addMessage({
    id: Date.now(),
    role: 'user',
    content: displayText,
    type: 'text',
    timestamp: new Date().toISOString()
  })
  
  // Clear selections
  selectedOptions.value = []
  supplementaryText.value = ''
  
  // Send the actual values to backend for proper processing
  await processUserInput(submitText)
}

async function processUserInput(input: string) {
  isLoading.value = true
  error.value = ''
  setLoadingText('Analyzing your response...')
  
  try {
    // Save message to conversation if authenticated
    if (authStore.isAuthenticated && chatStore.currentConversationId) {
      await conversationsApi.addMessage(
        authStore.token!,
        chatStore.currentConversationId,
        'user',
        input,
        'text'
      )
    }
    
    setLoadingText('Getting AI response...')
    // Call the real backend API with auth token
    const response = await api.getNextQuestion(sessionStore.sessionId, input, undefined, authStore.token)
    
    if (response) {
      // Check if this is a dialogue response (Policy system active)
      const isDialogue = response.dialogue_mode === true || response.should_continue_dialogue === true
      isInDialogueMode.value = isDialogue  // Update mode indicator
      
      // Add assistant message with the backend response
      const assistantMessage = {
        id: Date.now(),
        role: 'assistant' as const,
        content: isDialogue && response.dialogue_content ? response.dialogue_content : response.question_text,
        type: 'response',
        timestamp: new Date().toISOString(),
        metadata: {
          options: isDialogue ? [] : (response.options || []),
          multiSelect: false,
          allowTextInput: isDialogue ? true : response.allow_text_input,
          transition: response.transition_message || null,
          infoCards: response.info_cards || null,
          isDialogue: isDialogue
        }
      }
      
      chatStore.addMessage(assistantMessage)
      
      // Update progress if assessment data provided
      if (response.current_pnm || response.current_term || response.fsm_state) {
        chatStore.updateProgress({
          current_pnm: response.current_pnm,
          current_term: response.current_term,
          fsm_state: response.fsm_state || 'ROUTE'
        })
      }
      
      await scrollToBottom()
    }
    
  } catch (e: any) {
    errorType.value = categorizeError(e)
    const errorMessage = getErrorMessage(errorType.value)
    error.value = errorMessage
    chatStore.setError(errorMessage)
    console.error('Processing error:', e)
  } finally {
    isLoading.value = false
    chatStore.setLoading(false)
    if (autoFocusInput.value) {
      setTimeout(focusInput, 100)
    }
  }
}

async function startConversationWithInput(userMessage: string) {
  isLoading.value = true
  error.value = ''
  
  // Only reset session for brand new conversations
  if (chatStore.conversationType === 'general_chat' && !sessionStore.currentPnm) {
    sessionStore.resetSession()
  }
  
  try {
    // Send the user's first message to backend which will route and return first question
    const response = await api.getNextQuestion(sessionStore.sessionId, userMessage, undefined, authStore.token)
    
    if (response) {
      const isDialogue = response.dialogue_mode === true || response.should_continue_dialogue === true
      
      const assistantMessage = {
        id: Date.now(),
        role: 'assistant' as const,
        content: isDialogue && response.dialogue_content ? response.dialogue_content : response.question_text,
        type: 'response',
        timestamp: new Date().toISOString(),
        metadata: {
          options: isDialogue ? [] : (response.options || []),
          multiSelect: false,
          allowTextInput: isDialogue ? true : response.allow_text_input,
          transition: response.transition_message || null,
          infoCards: response.info_cards || null,
          isDialogue: isDialogue
        }
      }
      
      chatStore.addMessage(assistantMessage)
      
      // Update progress if assessment data provided
      if (response.current_pnm || response.current_term || response.fsm_state) {
        chatStore.updateProgress({
          current_pnm: response.current_pnm,
          current_term: response.current_term,
          fsm_state: response.fsm_state || 'ROUTE'
        })
      }
      
      // Update session state if provided (legacy compatibility)
      if (response.current_pnm) {
        sessionStore.setState(response.current_pnm, response.current_term || null, response.fsm_state || 'ROUTE')
      }
      
      await scrollToBottom()
    }
  } catch (e: any) {
    error.value = e.message || 'Error processing message'
    chatStore.setError(e.message || 'Error processing message')
  } finally {
    isLoading.value = false
    chatStore.setLoading(false)
  }
}

// Removed unused function startConversation

// Skip current question - currently unused but may be needed for future functionality
// async function skipQuestion() {
//   if (isLoading.value) return
  
//   // Add user message indicating skip
//   chatStore.addMessage({
//     type: 'user',
//     content: 'Skip this question',
//     timestamp: new Date()
//   })
  
//   // Clear selections
//   selectedOptions.value = []
//   supplementaryText.value = ''
  
//   // Process skip as user response
//   await processUserInput('skip')
// }

// Function to continue from data page - currently unused
// function continueFromData() {
//   // This would be called from the data page
//   sessionStore.setError('This feature needs to be launched from the Data page')
// }

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Load existing conversation
async function loadExistingConversation(conversationId: string) {
  isLoading.value = true
  chatStore.setLoading(true)
  
  try {
    const detail = await conversationsApi.getConversationDetail(authStore.token!, conversationId)
    
    // Load conversation data into chat store
    chatStore.loadConversationData({
      conversation: {
        id: detail.id,
        title: detail.title,
        type: detail.type,
        dimension: detail.dimension,
        status: detail.status,
        created_at: detail.created_at,
        updated_at: detail.updated_at,
        current_pnm: detail.assessment_state?.current_pnm,
        current_term: detail.assessment_state?.current_term,
        fsm_state: detail.assessment_state?.fsm_state
      },
      messages: detail.messages || [],
      progress: detail.assessment_state
    })
    
    // Update current stage
    if (detail.dimension) {
      currentStage.value = `${detail.dimension} Assessment`
    } else if (detail.assessment_state?.current_pnm) {
      currentStage.value = detail.assessment_state.current_pnm
    }
    
    await scrollToBottom()
  } catch (e: any) {
    error.value = `Failed to load conversation: ${e.message}`
    chatStore.setError(e.message)
  } finally {
    isLoading.value = false
    chatStore.setLoading(false)
  }
}

// Watch for dimension focus from data page
watch(() => sessionStore.dimensionFocus, async (newDimension) => {
  if (newDimension && !hasInitialized.value) {
    // Clear messages when starting a dimension-specific conversation
    await startDimensionConversation(newDimension)
    sessionStore.setDimensionFocus(null) // Clear after handling
  }
}, { immediate: true })

// Start dimension-specific conversation
async function startDimensionConversation(dimension: string) {
  // Start a new dimension-specific conversation
  chatStore.startNewConversation('dimension', dimension)
  
  // Create a new session for this dimension
  sessionStore.resetSession()
  
  isLoading.value = true
  hasInitialized.value = true
  
  try {
    // Create new conversation for dimension
    if (authStore.isAuthenticated) {
      try {
        const newConv = await conversationsApi.createConversation(authStore.token!, 'dimension', dimension)
        chatStore.setCurrentConversation(newConv.id)
      } catch (e: any) {
        console.error('Failed to create dimension conversation:', e)
      }
    }
    
    // Get the first question for this dimension from the backend
    const conversationId = chatStore.currentConversationId || 'temp-' + Date.now().toString()
    const response = await api.getNextQuestion(conversationId, '', dimension, authStore.token)
    
    if (response) {
      const isDialogue = response.dialogue_mode === true || response.should_continue_dialogue === true
      
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant' as const,
        content: isDialogue && response.dialogue_content ? response.dialogue_content : response.question_text,
        type: 'response',
        timestamp: new Date().toISOString(),
        metadata: {
          options: isDialogue ? [] : (response.options || []),
          multiSelect: false,
          allowTextInput: isDialogue ? true : response.allow_text_input,
          transition: response.transition_message || null,
          infoCards: response.info_cards || null,
          isDialogue: isDialogue
        }
      }
      
      chatStore.addMessage(assistantMessage)
      currentStage.value = `${dimension} Assessment`
      
      // Update session state
      if (response.current_pnm) {
        sessionStore.setState(response.current_pnm, response.current_term || null, response.fsm_state || 'ROUTE')
      }
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to start dimension conversation'
    // Fallback message
    chatStore.addMessage({
      id: Date.now(),
      role: 'assistant' as const,
      content: `Starting ${dimension} assessment. Please describe any issues or concerns related to this dimension.`,
      type: 'response',
      timestamp: new Date().toISOString()
    })
    currentStage.value = `${dimension} Assessment`
  } finally {
    isLoading.value = false
  }
  
  await scrollToBottom()
}

onMounted(async () => {
  // Check authentication
  if (!authStore.isAuthenticated) {
    error.value = 'Please login to use the assistant'
    return
  }
  
  // Load active conversation if exists
  try {
    const activeConv = await conversationsApi.getActiveConversation(authStore.token!)
  
    // Check if there's a dimension focus on mount
    if (sessionStore.dimensionFocus && !hasInitialized.value) {
      // Dimension-specific conversation is already created in Data.vue
      startDimensionConversation(sessionStore.dimensionFocus)
      sessionStore.setDimensionFocus(null)
    } else if (activeConv) {
      // Load existing active conversation
      await loadExistingConversation(activeConv.id)
    } else if (chatStore.messages.length === 0) {
      // Create new general conversation
      try {
        const newConv = await conversationsApi.createConversation(authStore.token!, 'general_chat')
        chatStore.startNewConversation('general_chat')
        chatStore.setCurrentConversation(newConv.id)
        
        // Create fresh session for new conversation
        sessionStore.resetSession()
        
        // Show welcome message
        chatStore.addMessage({
          id: Date.now(),
          role: 'assistant',
          content: 'Welcome to ALS Assistant! Please describe your current issues or symptoms, or select a specific dimension from the "Results & Data" page to begin assessment.',
          type: 'response',
          timestamp: new Date().toISOString()
        })
      } catch (e: any) {
        error.value = `Failed to create conversation: ${e.message}`
        chatStore.setError(e.message)
      }
    }
  } catch (e: any) {
    error.value = `Failed to initialize conversation: ${e.message}`
    console.error('Conversation initialization error:', e)
  }
  
  hasInitialized.value = true
})

onUnmounted(() => {
  // Clear initialization flag when leaving
  hasInitialized.value = false
})
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}

/* Mobile-first responsive design */
@media (max-width: 768px) {
  .chat {
    height: 100dvh; /* Use dynamic viewport height on mobile */
  }
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 768px) {
  .chat-header {
    padding: 12px 16px;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .chat-header h1 {
    font-size: 18px;
  }
  
  .header-indicators {
    width: 100%;
    justify-content: space-between;
  }
}

.chat-header h1 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
}

.header-indicators {
  display: flex;
  gap: 12px;
  align-items: center;
}

.mode-indicator {
  display: flex;
  align-items: center;
}

.mode-badge {
  padding: 6px 12px;
  border-radius: 18px;
  font-size: 12px;
  font-weight: 600;
  color: white;
  animation: pulse 2s infinite;
}

.mode-badge.dialogue {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
}

.mode-badge.question {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.stage-indicator {
  display: flex;
  align-items: center;
}

.stage-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (max-width: 768px) {
  .messages-container {
    padding: 16px 12px;
    gap: 12px;
  }
}

.message {
  display: flex;
  flex-direction: column;
}

.user-message {
  align-self: flex-end;
  max-width: 70%;
}

@media (max-width: 768px) {
  .user-message {
    max-width: 85%;
  }
}

.user-message .message-content {
  background: #3b82f6;
  color: white;
  padding: 12px 16px;
  border-radius: 18px 18px 4px 18px;
  font-size: 14px;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .user-message .message-content {
    padding: 10px 14px;
    font-size: 13px;
    border-radius: 16px 16px 4px 16px;
  }
}

.message-timestamp {
  font-size: 11px;
  color: #6b7280;
  margin-top: 4px;
  text-align: right;
}

.assistant-message {
  align-self: flex-start;
  max-width: 85%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.transition-message {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-style: italic;
}

.question-content {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.question-text {
  font-size: 16px;
  color: #1f2937;
  margin-bottom: 16px;
  line-height: 1.5;
}

/* Dialogue mode styles */
.dialogue-mode {
  background: linear-gradient(to right, #f0f9ff, #eff6ff);
  border: 1px solid #93c5fd;
}

.dialogue-text {
  font-size: 15px;
  color: #1e40af;
  font-style: normal;
  margin-bottom: 8px;
}

.dialogue-mode .text-input-container {
  margin-top: 12px;
  border-top: 1px solid #dbeafe;
  padding-top: 12px;
}

.options-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.options-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: 1fr;
}

.options-grid.multi-select {
  gap: 6px;
}

.option-btn {
  padding: 10px 14px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #374151;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-btn:hover {
  border-color: #3b82f6;
  background: #f8fafc;
}

.option-btn.selected {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1e40af;
}

.option-btn.multi-select.selected {
  background: #ecfdf5;
  border-color: #10b981;
  color: #065f46;
}

.checkbox {
  font-size: 16px;
}

.text-input-container {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.input-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}

.supplement-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  resize: vertical;
  font-family: inherit;
}

.supplement-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.info-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-card {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 10px;
  padding: 16px;
}

.card-title {
  font-weight: 600;
  color: #0c4a6e;
  margin-bottom: 12px;
  font-size: 15px;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.card-bullet {
  color: #0f172a;
  font-size: 14px;
  line-height: 1.5;
  position: relative;
  padding-left: 16px;
}

.card-bullet::before {
  content: "•";
  color: #0284c7;
  position: absolute;
  left: 0;
}

.card-disclaimer {
  font-size: 11px;
  color: #6b7280;
  font-style: italic;
  border-top: 1px solid #e0f2fe;
  padding-top: 8px;
}

.loading-message {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #6b7280;
  font-size: 14px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s ease-in-out infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-10px); }
}

.input-area {
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  background: white;
}

@media (max-width: 768px) {
  .input-area {
    padding: 12px 16px;
  }
}

.text-input-section {
  display: flex;
  flex-direction: column;
}

.input-container {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

@media (max-width: 768px) {
  .input-container {
    gap: 8px;
  }
}

.main-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

.main-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.main-input:disabled {
  background: #f9fafb;
  color: #6b7280;
  cursor: not-allowed;
}

.main-input:disabled::placeholder {
  color: #9ca3af;
}

.action-buttons,
.start-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

@media (max-width: 768px) {
  .action-buttons,
  .start-buttons {
    flex-direction: column;
    gap: 8px;
  }
}

.send-btn,
.submit-btn,
.start-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}

.send-btn:hover:not(:disabled),
.submit-btn:hover:not(:disabled),
.start-btn:hover:not(:disabled) {
  background: #2563eb;
}

.skip-btn,
.continue-btn,
.clear-btn {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.skip-btn:hover:not(:disabled),
.continue-btn:hover:not(:disabled),
.clear-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-container {
  position: fixed;
  top: 80px;
  right: 24px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

@media (max-width: 768px) {
  .error-container {
    position: fixed;
    top: 60px;
    left: 16px;
    right: 16px;
    max-width: none;
    padding: 10px 12px;
  }
}

.error-connection {
  background: #fef7f0;
  border-color: #fed7aa;
}

.error-auth {
  background: #fdf2f8;
  border-color: #fbcfe8;
}

.error-server {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.error-message {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #991b1b;
  font-size: 14px;
}

.error-content {
  flex: 1;
}

.error-text {
  font-weight: 500;
  margin-bottom: 4px;
}

.error-retry-info {
  font-size: 12px;
  color: #6b7280;
  font-style: italic;
}

.error-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.retry-error {
  background: #f59e0b;
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-error:hover:not(:disabled) {
  background: #d97706;
}

.retry-error:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.error-icon {
  font-size: 16px;
}

.dismiss-error {
  background: none;
  border: none;
  color: #991b1b;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 8px;
}

.dismiss-error:hover {
  text-decoration: underline;
}

.notification-container {
  position: fixed;
  top: 80px;
  right: 24px;
  background: #f0f9ff;
  border: 1px solid #7dd3fc;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

@media (max-width: 768px) {
  .notification-container {
    top: 60px;
    left: 16px;
    right: 16px;
    max-width: none;
    padding: 10px 12px;
  }
}

.notification-message {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0c4a6e;
  font-size: 14px;
}

.notification-icon {
  font-size: 16px;
}

.dismiss-notification {
  background: none;
  border: none;
  color: #0c4a6e;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 8px;
}

.dismiss-notification:hover {
  text-decoration: underline;
}
</style>