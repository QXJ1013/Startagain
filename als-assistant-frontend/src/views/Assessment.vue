<template>
  <div class="assessment">
    <div class="header">
      <h1>ALS Self-Awareness Assessment</h1>
      <p class="subtitle">
        Understanding your knowledge about ALS and how it affects different aspects of your life
      </p>
    </div>

    <!-- Progress Indicator -->
    <div class="progress-bar" v-if="profile">
      <div class="progress-fill" :style="{ width: `${profile.overall.percentage}%` }"></div>
      <span class="progress-text">
        {{ profile.overall.percentage.toFixed(1) }}% - {{ profile.overall.level }}
      </span>
    </div>

    <!-- Current Question -->
    <div class="question-card" v-if="currentQuestion">
      <div class="question-type">{{ currentQuestion.question_type.toUpperCase() }}</div>
      
      <!-- Transition Message -->
      <div class="transition-message" v-if="currentQuestion.transition_message">
        <div class="transition-icon">→</div>
        <div>{{ currentQuestion.transition_message }}</div>
      </div>

      <div class="question-text">{{ currentQuestion.question_text }}</div>
      
      <!-- Response Options -->
      <div class="response-options" v-if="currentQuestion.options.length > 0">
        <button 
          v-for="option in currentQuestion.options"
          :key="option.value"
          class="option-btn"
          :class="{ selected: selectedOption === option.value }"
          @click="selectOption(option.value)"
        >
          {{ option.label }}
        </button>
      </div>

      <!-- Text Input -->
      <div class="text-input" v-if="currentQuestion.allow_text_input">
        <textarea 
          v-model="userResponse" 
          placeholder="Share your thoughts and experiences..."
          rows="4"
        ></textarea>
      </div>

      <div class="question-actions">
        <button 
          class="btn primary" 
          @click="submitResponse"
          :disabled="!hasResponse"
        >
          Submit Response
        </button>
      </div>
    </div>

    <!-- Start Assessment -->
    <div class="start-card" v-else-if="!isLoading">
      <h2>Ready to Begin?</h2>
      <p>
        This assessment will help us understand your current awareness and knowledge 
        about how ALS affects different aspects of your life.
      </p>
      <button class="btn primary large" @click="startAssessment">
        Start Assessment
      </button>
    </div>

    <!-- Info Cards -->
    <div class="info-cards" v-if="infoCards && infoCards.length > 0">
      <h3>📚 Personalized Information</h3>
      <div class="cards-grid">
        <InfoCard 
          v-for="(card, index) in infoCards"
          :key="index"
          :title="card.title"
          :bullets="card.bullets"
          :url="card.url"
          :source="card.source"
        />
      </div>
    </div>

    <!-- Loading -->
    <div class="loading" v-if="isLoading">
      <div class="spinner"></div>
      <p>Loading next question...</p>
    </div>

    <!-- Error -->
    <div class="error" v-if="error">
      <div class="error-icon">⚠️</div>
      <div class="error-message">{{ error }}</div>
      <button class="btn" @click="error = null">Dismiss</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useSessionStore } from '../stores/session';
import { api } from '../services/api';
import InfoCard from '../components/InfoCard.vue';

const sessionStore = useSessionStore();

// Reactive data
const currentQuestion = ref<any>(null);
const userResponse = ref('');
const selectedOption = ref('');
const infoCards = ref<any[]>([]);
const profile = ref<any>(null);
const isLoading = ref(false);
const error = ref('');

// Computed
const hasResponse = computed(() => {
  return userResponse.value.trim() || selectedOption.value;
});

// Methods
async function startAssessment() {
  try {
    isLoading.value = true;
    const response = await api.getNextQuestion(sessionStore.sessionId);
    currentQuestion.value = response;
    await loadProfile();
  } catch (e: any) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
}

function selectOption(value: string) {
  selectedOption.value = value;
  userResponse.value = value; // Use option value as response
}

async function submitResponse() {
  if (!hasResponse.value) return;
  
  try {
    isLoading.value = true;
    
    const response = await api.getNextQuestion(
      sessionStore.sessionId, 
      userResponse.value || selectedOption.value
    );
    
    // Update UI
    currentQuestion.value = response;
    infoCards.value = response.info_cards || [];
    
    // Clear inputs
    userResponse.value = '';
    selectedOption.value = '';
    
    // Update profile
    await loadProfile();
    
  } catch (e: any) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
}

async function loadProfile() {
  try {
    const profileData = await api.getPNMProfile(sessionStore.sessionId);
    profile.value = profileData.profile;
  } catch (e: any) {
    console.warn('Could not load PNM profile:', e.message);
  }
}

onMounted(() => {
  loadProfile();
});
</script>

<style scoped>
.assessment {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  color: #1f2937;
  margin-bottom: 8px;
}

.subtitle {
  color: #6b7280;
  font-size: 16px;
  line-height: 1.5;
}

/* Progress Bar */
.progress-bar {
  position: relative;
  background: #f3f4f6;
  border-radius: 8px;
  height: 12px;
  margin-bottom: 24px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #059669);
  border-radius: 8px;
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  top: 16px;
  right: 0;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

/* Question Card */
.question-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.question-type {
  display: inline-block;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 12px;
}

.transition-message {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  color: #0c4a6e;
}

.transition-icon {
  font-size: 18px;
  color: #0284c7;
}

.question-text {
  font-size: 18px;
  line-height: 1.6;
  color: #1f2937;
  margin-bottom: 20px;
}

/* Response Options */
.response-options {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.option-btn {
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
}

.option-btn:hover {
  border-color: #3b82f6;
  background: #f8fafc;
}

.option-btn.selected {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
}

/* Text Input */
.text-input {
  margin-bottom: 16px;
}

.text-input textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  resize: vertical;
  min-height: 100px;
}

.text-input textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Start Card */
.start-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.start-card h2 {
  color: #1f2937;
  margin-bottom: 16px;
}

.start-card p {
  color: #6b7280;
  line-height: 1.6;
  margin-bottom: 24px;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:hover {
  background: #f9fafb;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.btn.primary:hover {
  background: #2563eb;
}

.btn.large {
  padding: 12px 24px;
  font-size: 16px;
}

.question-actions {
  display: flex;
  justify-content: flex-end;
}

/* Info Cards */
.info-cards {
  margin-top: 24px;
}

.info-cards h3 {
  color: #1f2937;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

/* Loading */
.loading {
  text-align: center;
  padding: 40px;
  color: #6b7280;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Error */
.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.error-icon {
  font-size: 20px;
  color: #dc2626;
}

.error-message {
  flex: 1;
  color: #991b1b;
}
</style>