<template>
  <div class="chat">
    <!-- Initial Menu View -->
    <div v-if="viewMode === 'menu'" class="chat-menu">
      <div class="menu-header">
        <h1>💬 ALS Assistant Chat</h1>
        <p>Choose how you'd like to start your conversation</p>
      </div>

      <div class="menu-options">
        <button @click="startNewChat" class="menu-option new-chat">
          <div class="option-icon">💬</div>
          <div class="option-content">
            <h3>New Chat</h3>
            <p>Start a new conversation with the ALS Assistant</p>
          </div>
        </button>

        <button @click="viewHistory" class="menu-option history">
          <div class="option-icon">📋</div>
          <div class="option-content">
            <h3>Chat History</h3>
            <p>View and continue previous conversations</p>
          </div>
        </button>
      </div>
    </div>

    <!-- History View -->
    <div v-else-if="viewMode === 'history'" class="history-view">
      <div class="history-header">
        <button @click="backToMenu" class="back-btn">← Back</button>
        <h2>Chat History</h2>
        <button @click="startNewChat" class="new-chat-btn">
          <span class="btn-icon">💬</span>
          New Chat
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="historyLoading" class="history-loading">
        <div class="spinner"></div>
        <p>Loading conversations...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="historyConversations.length === 0" class="history-empty">
        <div class="empty-icon">📚</div>
        <h3>No conversations yet</h3>
        <p>Start a new conversation to begin your ALS assessment journey</p>
        <button @click="startNewChat" class="start-chat-btn">
          <span class="btn-icon">💬</span>
          Start Your First Chat
        </button>
      </div>

      <!-- Conversation List -->
      <div v-else class="history-content">
        <div class="conversations-grid">
          <div
            v-for="conv in historyConversations"
            :key="conv.id"
            class="conversation-card"
            :class="{
              active: conv.status === 'active',
              completed: conv.status === 'completed'
            }"
            @click="openHistoryConversation(conv)"
          >
            <!-- Card Header -->
            <div class="card-header">
              <div class="status-dot" :class="conv.status"></div>
              <h3 class="card-title">{{ conv.title || getConversationTitle(conv) }}</h3>
              <div class="card-actions">
                <button
                  @click.stop="continueHistoryConversation(conv)"
                  class="continue-btn"
                  v-if="conv.status === 'active'"
                >
                  →
                </button>
              </div>
            </div>

            <!-- Card Content -->
            <div class="card-content">
              <div class="conv-type-badge" :class="conv.type">
                {{ getConversationType(conv) }}
              </div>
              <div class="conv-date">{{ formatHistoryDate(conv.updated_at || conv.created_at) }}</div>
            </div>

            <!-- Stats Footer -->
            <div class="card-footer">
              <span class="stat">💬 {{ conv.message_count || 0 }}</span>
              <span class="stat" v-if="conv.info_card_count">📋 {{ conv.info_card_count }}</span>
              <span class="status-badge" :class="conv.status">{{ conv.status }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Chat View -->
    <div v-else-if="viewMode === 'chat'" class="chat-view">
      <!-- Header -->
      <div class="chat-header">
        <button @click="backToMenu" class="back-btn">← Menu</button>
        <div class="header-content">
          <h1>💬 ALS Assistant Chat</h1>
          <div class="header-indicators">
            <div class="mode-indicator" v-if="isInDialogueMode">
              <span class="mode-badge dialogue">🗣️ Dialogue Mode</span>
            </div>
            <div class="mode-indicator" v-else>
              <span class="mode-badge question">📋 Assessment Mode</span>
            </div>
            <div class="stage-indicator" v-if="currentStage">
              <span class="stage-badge">{{ currentStage }}</span>
            </div>
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
        <!-- Show completion notice for completed conversations -->
        <div v-if="isConversationCompleted" class="completion-notice">
          <div class="completion-message">
            <span class="completion-icon">✅</span>
            <span>This conversation has been completed. You can view the history but cannot add new messages.</span>
          </div>
        </div>

        <!-- Always show text input for user to type (unless completed) -->
        <div v-else class="text-input-section">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { useChatStore } from '../stores/chat'
import { api, conversationsApi } from '../services/api'
import { useAuthStore } from '../stores/auth'

// State
const router = useRouter()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const authStore = useAuthStore()
const viewMode = ref<'menu' | 'history' | 'chat'>('menu')
const userInput = ref('')
const supplementaryText = ref('')
const selectedOptions = ref<{value: string, label: string}[]>([])
const currentStage = ref('Processing diagnosis')
const isLoading = ref(false)
const error = ref<string | null>(null)
const messagesContainer = ref<HTMLElement>()
const hasInitialized = ref(false)
const isInDialogueMode = ref(false)
const isConversationCompleted = ref(false) // Track if current conversation is completed
const mainInputRef = ref<HTMLTextAreaElement>()
const loadingText = ref('Analyzing your response...')
const autoFocusInput = ref(true)
const errorType = ref<'connection' | 'auth' | 'validation' | 'server' | 'unknown'>('unknown')
const retryCount = ref(0)
const maxRetries = 3
const lastFailedOperation = ref<(() => Promise<void>) | null>(null)

// History-related state
const historyLoading = ref(false)
const historyConversations = ref<any[]>([])

// Use messages from chat store and transform for display
const messages = computed(() => {
  const transformedMessages = chatStore.messages.map(msg => ({
    ...msg,
    // Keep original type, add role-based type for CSS classes
    type: msg.role, // This is used for CSS classes in template
    options: msg.metadata?.options || msg.options || [],
    multiSelect: msg.metadata?.multiSelect || msg.multiSelect || false,
    allowTextInput: msg.metadata?.allowTextInput || msg.allowTextInput || false,
    transition: msg.metadata?.transition || msg.transition || null,
    infoCards: msg.metadata?.infoCards || msg.infoCards || null,
    isDialogue: msg.metadata?.isDialogue || msg.isDialogue || false
  }))


  return transformedMessages
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
function startNewChat() {
  viewMode.value = 'chat'
  // Clear any existing conversation
  chatStore.startNewConversation('general_chat')
  // Reset completion status for new chat
  isConversationCompleted.value = false
  // Initialize the chat
  initializeNewChat()
}

function viewHistory() {
  viewMode.value = 'history'
  loadConversationHistory()
}

function backToMenu() {
  viewMode.value = 'menu'
}

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
  // Use conversationId presence as the primary indicator, not message count
  console.log(`[SEND MESSAGE DEBUG] currentConversationId: ${chatStore.currentConversationId}, conversationType: ${chatStore.conversationType}`)

  if (!chatStore.currentConversationId && chatStore.conversationType === 'general_chat') {
    // No conversation ID yet, this is truly the first message - create new conversation
    console.log('[SEND MESSAGE] Creating new conversation...')
    await startConversationWithInput(messageText)
  } else {
    // We have a conversation ID, continue existing conversation
    console.log('[SEND MESSAGE] Continuing existing conversation...')
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
    // Ensure we have a valid conversation ID
    let conversationId = chatStore.currentConversationId

    // If no conversation ID, create a new general chat conversation
    if (!conversationId) {
      setLoadingText('Creating conversation...')
      try {
        const newConv = await conversationsApi.createConversation(
          authStore.token!,
          'general_chat',
          undefined,
          'General Chat'
        )
        conversationId = newConv.id
        console.log(`[START CONV] Setting conversation ID: ${conversationId}`)
        chatStore.setCurrentConversation(conversationId)
        console.log(`[START CONV] Store conversation ID after setting: ${chatStore.currentConversationId}`)
      } catch (e: any) {
        error.value = `Failed to create conversation: ${e.message}`
        isLoading.value = false
        return
      }
    }

    setLoadingText('Getting AI response...')
    // Call the real backend API with auth token and proper conversation ID
    const response = await api.getNextQuestion(conversationId, input, undefined, authStore.token)

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
    // Ensure we have a valid conversation ID
    let conversationId = chatStore.currentConversationId

    // If no conversation ID, create a new general chat conversation
    if (!conversationId) {
      setLoadingText('Creating conversation...')
      try {
        const newConv = await conversationsApi.createConversation(
          authStore.token!,
          'general_chat',
          undefined,
          'General Chat'
        )
        conversationId = newConv.id
        console.log(`[START CONV] Setting conversation ID: ${conversationId}`)
        chatStore.setCurrentConversation(conversationId)
        console.log(`[START CONV] Store conversation ID after setting: ${chatStore.currentConversationId}`)
      } catch (e: any) {
        error.value = `Failed to create conversation: ${e.message}`
        isLoading.value = false
        return
      }
    }

    // Send the user's first message to backend which will route and return first question
    const response = await api.getNextQuestion(conversationId, userMessage, undefined, authStore.token)

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

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
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
  console.log(`[CHAT.VUE] Starting dimension conversation for ${dimension}`)

  viewMode.value = 'chat'

  // Check if conversation is already created (from Data.vue)
  const conversationExists = !!chatStore.currentConversationId
  console.log(`[CHAT.VUE] Conversation exists: ${conversationExists}, ID: ${chatStore.currentConversationId}`)

  if (!conversationExists) {
    // Only create new conversation if one doesn't exist
    chatStore.startNewConversation('dimension', dimension)
  } else {
    // Use existing conversation, just set the type and dimension
    chatStore.conversationType = 'dimension'
    chatStore.dimensionName = dimension
  }

  // Always reset session for fresh dimension assessment
  sessionStore.resetSession()

  // Clear any existing messages to ensure fresh start
  chatStore.clearMessages()

  // Force clear any cached state that might interfere
  isInDialogueMode.value = false
  error.value = null

  console.log(`[CHAT.VUE] State cleared for ${dimension} - messages: ${chatStore.messages.length}`)

  isLoading.value = true
  hasInitialized.value = true

  try {
    let conversationId = chatStore.currentConversationId

    // Create new conversation only if one doesn't exist
    if (authStore.isAuthenticated && !conversationId) {
      try {
        const newConv = await conversationsApi.createConversation(authStore.token!, 'dimension', dimension, `${dimension} Assessment`)
        conversationId = newConv.id
        chatStore.setCurrentConversation(conversationId)
      } catch (e: any) {
        console.error('Failed to create dimension conversation:', e)
        error.value = 'Failed to create conversation'
        return
      }
    }

    // Add a small delay to ensure backend state is properly set
    await new Promise(resolve => setTimeout(resolve, 50));

    // Get the first question for this dimension from the backend
    if (conversationId) {
      console.log(`[CHAT.VUE] Requesting first question for ${dimension} conversation ${conversationId}`)
      const response = await api.getNextQuestion(conversationId, '', dimension, authStore.token)

      if (response) {
        console.log(`[CHAT.VUE] Got response for ${dimension}:`, {
          dialogue_mode: response.dialogue_mode,
          question_type: response.question_type,
          options_count: response.options?.length || 0,
          content_length: response.question_text?.length || 0,
          current_pnm: response.current_pnm,
          current_term: response.current_term
        })

        const isDialogue = response.dialogue_mode === true || response.should_continue_dialogue === true

        // Log potential issue indicators
        if (isDialogue && response.options && response.options.length === 0) {
          console.warn(`[CHAT.VUE] ⚠️ POTENTIAL ISSUE: ${dimension} is in dialogue mode with no options - this might be the analysis mode bypass bug`)
        }

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
    }
  } catch (e: any) {
    console.error('Failed to start dimension conversation:', e)
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

async function initializeNewChat() {
  // Check authentication
  if (!authStore.isAuthenticated) {
    error.value = 'Please login to use the assistant'
    return
  }

  try {
    // Generate a simple conversation ID for the session
    const simpleConversationId = `conv_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`
    chatStore.setCurrentConversation(simpleConversationId)

    // Create fresh session for new conversation
    sessionStore.resetSession()

    // Show welcome message
    chatStore.addMessage({
      id: Date.now(),
      role: 'assistant',
      content: 'Welcome to ALS Assistant! Please describe your current issues or symptoms.',
      type: 'response',
      timestamp: new Date().toISOString()
    })

    hasInitialized.value = true
  } catch (e: any) {
    error.value = `Failed to initialize conversation: ${e.message}`
    console.error('Conversation initialization error:', e)
  }
}

onMounted(async () => {
  // Check authentication
  if (!authStore.isAuthenticated) {
    error.value = 'Please login to use the assistant'
    return
  }

  try {
    // Check if there's a dimension focus on mount (from Data page navigation)
    if (sessionStore.dimensionFocus && !hasInitialized.value) {
      viewMode.value = 'chat'
      // Dimension-specific conversation is already created in Data.vue
      startDimensionConversation(sessionStore.dimensionFocus)
      sessionStore.setDimensionFocus(null)
    }
    // Otherwise, stay in menu mode and let user choose
  } catch (e: any) {
    error.value = `Failed to initialize: ${e.message}`
    console.error('Initialization error:', e)
  }
})

// History-related methods
async function loadConversationHistory() {
  historyLoading.value = true
  try {
    if (!authStore.token) {
      authStore.logout();
      sessionStore.setMessage('Please login to view history');
      router.push('/login');
      return;
    }

    const response = await conversationsApi.getConversations(authStore.token!)
    historyConversations.value = response.conversations || []
  } catch (e: any) {
    console.error('Failed to load conversation history:', e)

    // Check if it's an authentication error
    if (e.message && e.message.includes('401')) {
      authStore.logout();
      sessionStore.setMessage('Session expired. Please login again.');
      router.push('/login');
    } else {
      error.value = 'Failed to load conversation history'
    }
  } finally {
    historyLoading.value = false
  }
}

function getConversationTitle(conversation: any): string {
  return conversation.title || `Chat ${conversation.id.slice(0, 8)}`
}

function formatHistoryDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  // Less than 24 hours
  if (diff < 86400000) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  // Less than 7 days
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}d ago`
  }

  // Older
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

async function openHistoryConversation(conversation: any) {
  try {
    // Load this conversation into the chat view
    chatStore.setCurrentConversation(conversation.id)
    chatStore.clearMessages()

    // Fetch full conversation details with messages from backend
    historyLoading.value = true
    const conversationDetail = await conversationsApi.getConversationDetail(authStore.token!, conversation.id)

    // Load messages into the store - show original conversation history as-is
    if (conversationDetail.messages && conversationDetail.messages.length > 0) {
      conversationDetail.messages.forEach((msg: any) => {
        chatStore.addMessage({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          type: msg.role, // Use role for display type (user/assistant)
          timestamp: msg.timestamp,
          metadata: msg.metadata || {}
        })
      })
    }

    // Set conversation type and dimension if available
    if (conversationDetail.type) {
      chatStore.conversationType = conversationDetail.type as 'general_chat' | 'dimension' | 'assessment'
    }
    if (conversationDetail.dimension) {
      chatStore.dimensionName = conversationDetail.dimension
    }

    // Switch to chat view and update state properly for continuation
    viewMode.value = 'chat'
    hasInitialized.value = true

    // Update dialogue mode and completion status based on conversation status
    isConversationCompleted.value = conversationDetail.status === 'completed'

    if (conversationDetail.status === 'active') {
      // For active conversations, check if last message was from user (waiting for AI response)
      const lastMessage = conversationDetail.messages[conversationDetail.messages.length - 1]
      isInDialogueMode.value = lastMessage?.role === 'assistant' // If last was assistant, we're in dialogue mode
    } else {
      // Completed conversations are not in dialogue mode
      isInDialogueMode.value = false
    }


    // Scroll to bottom after a brief delay to ensure messages are rendered
    setTimeout(() => {
      scrollToBottom()
    }, 100)

  } catch (e: any) {
    console.error('Failed to load conversation:', e)
    error.value = `Failed to load conversation: ${e.message}`
  } finally {
    historyLoading.value = false
  }
}

function getConversationType(conversation?: any) {
  if (!conversation) return 'General Chat'
  if (conversation.type === 'dimension') return `${conversation.dimension} Assessment`
  if (conversation.type === 'assessment') return 'Assessment'
  return 'General Chat'
}

function continueHistoryConversation(conversation: any) {
  openHistoryConversation(conversation)
}

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

/* Chat Menu Styles */
.chat-menu {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  padding: 40px 24px;
}

.menu-header {
  text-align: center;
  margin-bottom: 48px;
}

.menu-header h1 {
  font-size: 28px;
  color: #1f2937;
  margin: 0 0 12px 0;
}

.menu-header p {
  color: #6b7280;
  font-size: 16px;
  margin: 0;
}

.menu-options {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  max-width: 400px;
}

.menu-option {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  width: 100%;
}

.menu-option:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.15);
}

.option-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.option-content {
  flex: 1;
}

.option-content h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  color: #1f2937;
}

.option-content p {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
  line-height: 1.4;
}

/* History View Styles */
.history-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.history-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: white;
}

.history-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
  flex: 1;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.new-chat-btn:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.btn-icon {
  font-size: 16px;
}

.history-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.conversations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.conversation-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.conversation-card:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.conversation-card.active {
  border-color: #10b981;
  background: #f0fdf4;
}

.conversation-card.completed {
  border-color: #8b5cf6;
  background: #faf5ff;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
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

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  flex: 1;
  line-height: 1.3;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.continue-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: #3b82f6;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.2s ease;
}

.continue-btn:hover {
  background: #2563eb;
  transform: scale(1.1);
}

.card-content {
  margin-bottom: 12px;
}

.conv-type-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 8px;
}

.conv-type-badge.dimension {
  background: #eff6ff;
  color: #1d4ed8;
}

.conv-type-badge.assessment {
  background: #f0f9ff;
  color: #0369a1;
}

.conv-type-badge.general_chat {
  background: #f9fafb;
  color: #374151;
}

.conv-date {
  font-size: 13px;
  color: #6b7280;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.stat {
  font-size: 12px;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-badge {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  text-transform: capitalize;
}

.status-badge.active {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.completed {
  background: #ede9fe;
  color: #5b21b6;
}

.status-badge.paused {
  background: #fef3c7;
  color: #92400e;
}

/* Chat View Styles */
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
}

.back-btn {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  color: #374151;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: #e5e7eb;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
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

.message {
  display: flex;
  flex-direction: column;
}

.user-message {
  align-self: flex-end;
  max-width: 70%;
}

.user-message .message-content {
  background: #3b82f6;
  color: white;
  padding: 12px 16px;
  border-radius: 18px 18px 4px 18px;
  font-size: 14px;
  line-height: 1.5;
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

.completion-notice {
  display: flex;
  justify-content: center;
  padding: 12px 0;
}

.completion-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  color: #0c4a6e;
  font-size: 14px;
  font-weight: 500;
}

.completion-icon {
  font-size: 16px;
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

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 12px;
}

.send-btn,
.submit-btn,
.clear-btn {
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}

.send-btn,
.submit-btn {
  background: #3b82f6;
  color: white;
}

.send-btn:hover:not(:disabled),
.submit-btn:hover:not(:disabled) {
  background: #2563eb;
}

.clear-btn {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.clear-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-container {
  position: fixed;
  bottom: 24px;
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

@media (max-width: 768px) {
  .menu-options {
    max-width: 100%;
  }

  .menu-option {
    padding: 16px;
  }

  .option-content h3 {
    font-size: 16px;
  }

  .option-content p {
    font-size: 13px;
  }

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

  .messages-container {
    padding: 16px 12px;
    gap: 12px;
  }

  .user-message {
    max-width: 85%;
  }

  .user-message .message-content {
    padding: 10px 14px;
    font-size: 13px;
    border-radius: 16px 16px 4px 16px;
  }

  .input-area {
    padding: 12px 16px;
  }

  .input-container {
    gap: 8px;
  }

  .action-buttons {
    flex-direction: column;
    gap: 8px;
  }

  .error-container {
    bottom: 16px;
    left: 16px;
    right: 16px;
    max-width: none;
    padding: 10px 12px;
  }
}
</style>