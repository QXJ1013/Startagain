<template>
  <div class="chat">
    <!-- Header -->
    <div class="chat-header">
      <h1>💬 ALS Assistant Chat</h1>
      <div class="stage-indicator" v-if="currentStage">
        <span class="stage-badge">{{ currentStage }}</span>
      </div>
    </div>

    <!-- Messages Container -->
    <div class="messages-container" ref="messagesContainer">
      <div v-for="(message, index) in messages" :key="index" class="message" :class="message.type">
        
        <!-- User Message -->
        <div v-if="message.type === 'user'" class="user-message">
          <div class="message-content">{{ message.content }}</div>
        </div>

        <!-- Assistant Message -->
        <div v-else class="assistant-message">
          <!-- Transition Message -->
          <div v-if="message.transition" class="transition-message">
            {{ message.transition }}
          </div>
          
          <!-- Question Content -->
          <div class="question-content">
            <div class="question-text">{{ message.content }}</div>
            
            <!-- Button Options -->
            <div v-if="message.options && message.options.length" class="options-container">
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
              
              <!-- Optional text input -->
              <div v-if="message.allowTextInput" class="text-input-container">
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

          <!-- Info Cards -->
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
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="isLoading" class="loading-message">
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div class="loading-text">Analyzing your response...</div>
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
            placeholder="Describe your situation or enter your response..."
            rows="3"
            class="main-input"
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
    <div v-if="error" class="error-container">
      <div class="error-message">
        <span class="error-icon">⚠️</span>
        {{ error }}
      </div>
      <button @click="error = null" class="dismiss-error">Close</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useSessionStore } from '../stores/session'
import { useChatStore } from '../stores/chat'
import { api } from '../services/api'

// State
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const userInput = ref('')
const supplementaryText = ref('')
const selectedOptions = ref<{value: string, label: string}[]>([])
const currentStage = ref('Processing diagnosis')
const isLoading = ref(false)
const error = ref('')
const messagesContainer = ref<HTMLElement>()
const hasInitialized = ref(false)

// Use messages from chat store
const messages = computed(() => chatStore.messages)

// Computed
const hasCurrentQuestion = computed(() => {
  const lastMessage = messages.value[messages.value.length - 1]
  return lastMessage && lastMessage.type === 'assistant' && lastMessage.options && lastMessage.options.length > 0
})

const hasSelection = computed(() => {
  return selectedOptions.value.length > 0
})

// Methods
function isOptionSelected(value: string, multiSelect: boolean): boolean {
  if (multiSelect) {
    return selectedOptions.value.some(opt => opt.value === value)
  }
  return selectedOptions.value.length > 0 && selectedOptions.value[0].value === value
}

function selectOption(option: {value: string, label: string}, multiSelect: boolean) {
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
    type: 'user',
    content: messageText,
    timestamp: new Date()
  })
  
  // Check if this is the first real user message in this conversation
  const userMessages = chatStore.messages.filter(m => m.type === 'user')
  if (userMessages.length === 1 && chatStore.conversationType === 'general') {
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
    type: 'user',
    content: displayText,
    timestamp: new Date()
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
  
  try {
    // Call the real backend API
    const response = await api.getNextQuestion(sessionStore.sessionId, input)
    
    if (response) {
      // Add assistant message with the backend response
      const assistantMessage = {
        type: 'assistant',
        content: response.question_text,
        options: response.options || [],
        multiSelect: false, // Can be enhanced to support multi-select from backend
        allowTextInput: response.allow_text_input,
        transition: response.transition_message || null,
        infoCards: response.info_cards || null,
        timestamp: new Date()
      }
      
      chatStore.addMessage(assistantMessage)
      chatStore.incrementQuestionCount()
      await scrollToBottom()
    }
    
  } catch (e: any) {
    error.value = e.message || 'Error processing message'
  } finally {
    isLoading.value = false
  }
}

async function startConversationWithInput(userMessage: string) {
  isLoading.value = true
  error.value = ''
  
  // Only reset session for brand new conversations
  if (chatStore.conversationType === 'general' && !sessionStore.currentPnm) {
    sessionStore.resetSession()
  }
  
  try {
    // Send the user's first message to backend which will route and return first question
    const response = await api.getNextQuestion(sessionStore.sessionId, userMessage)
    
    if (response) {
      const assistantMessage = {
        type: 'assistant',
        content: response.question_text,
        options: response.options || [],
        multiSelect: false,
        allowTextInput: response.allow_text_input,
        transition: response.transition_message || null,
        infoCards: response.info_cards || null,
        timestamp: new Date()
      }
      
      chatStore.addMessage(assistantMessage)
      chatStore.incrementQuestionCount()
      
      // Update session state if provided
      if (response.current_pnm) {
        sessionStore.setState(response.current_pnm, response.current_term, response.fsm_state || 'ROUTE')
      }
      
      await scrollToBottom()
    }
  } catch (e: any) {
    error.value = e.message || 'Error processing message'
  } finally {
    isLoading.value = false
  }
}

async function startConversation() {
  // This is now only called when starting from Data page with dimension focus
  messages.value = []
  isLoading.value = true
  
  try {
    const response = await api.getNextQuestion(sessionStore.sessionId)
    
    if (response) {
      const assistantMessage = {
        type: 'assistant',
        content: response.question_text,
        options: response.options || [],
        multiSelect: false,
        allowTextInput: response.allow_text_input,
        transition: response.transition_message || null,
        infoCards: response.info_cards || null,
        timestamp: new Date()
      }
      
      chatStore.addMessage(assistantMessage)
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to start conversation'
  } finally {
    isLoading.value = false
  }
  
  await scrollToBottom()
}

async function skipQuestion() {
  if (isLoading.value) return
  
  // Add user message indicating skip
  chatStore.addMessage({
    type: 'user',
    content: 'Skip this question',
    timestamp: new Date()
  })
  
  // Clear selections
  selectedOptions.value = []
  supplementaryText.value = ''
  
  // Process skip as user response
  await processUserInput('skip')
}

function continueFromData() {
  // This would be called from the data page
  sessionStore.setError('This feature needs to be launched from the Data page')
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
  // Start a new dimension-specific conversation
  chatStore.startNewConversation('dimension', dimension)
  
  // Create a new session for this dimension
  sessionStore.resetSession()
  
  isLoading.value = true
  hasInitialized.value = true
  
  try {
    // Get the first question for this dimension from the backend
    // Pass the dimension focus to backend
    const response = await api.getNextQuestion(sessionStore.sessionId, undefined, dimension)
    
    if (response) {
      const assistantMessage = {
        type: 'assistant',
        content: response.question_text,
        options: response.options || [],
        multiSelect: false,
        allowTextInput: response.allow_text_input,
        transition: response.transition_message || null,
        infoCards: response.info_cards || null,
        timestamp: new Date()
      }
      
      chatStore.addMessage(assistantMessage)
      chatStore.incrementQuestionCount()
      currentStage.value = `${dimension} Assessment`
      
      // Update session state
      if (response.current_pnm) {
        sessionStore.setState(response.current_pnm, response.current_term, response.fsm_state || 'ROUTE')
      }
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to start dimension conversation'
    // Fallback message
    chatStore.addMessage({
      type: 'assistant',
      content: `Starting ${dimension} assessment. Please describe any issues or concerns related to this dimension.`,
      timestamp: new Date()
    })
    currentStage.value = `${dimension} Assessment`
  } finally {
    isLoading.value = false
  }
  
  await scrollToBottom()
}

onMounted(() => {
  // Check if there's a dimension focus on mount
  if (sessionStore.dimensionFocus && !hasInitialized.value) {
    startDimensionConversation(sessionStore.dimensionFocus)
    sessionStore.setDimensionFocus(null)
  } else if (chatStore.messages.length === 0) {
    // Start a new general conversation
    chatStore.startNewConversation('general')
    
    // Create fresh session for new conversation
    sessionStore.resetSession()
    
    // Show welcome message
    chatStore.addMessage({
      type: 'assistant',
      content: 'Welcome to ALS Assistant! Please describe your current issues or symptoms, or select a specific dimension from the "Results & Data" page to begin assessment.',
      options: [],
      timestamp: new Date()
    })
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
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h1 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
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

.action-buttons,
.start-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
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
  align-items: center;
  gap: 12px;
  max-width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #991b1b;
  font-size: 14px;
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