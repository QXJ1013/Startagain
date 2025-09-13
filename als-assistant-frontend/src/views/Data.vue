<template>
  <div class="data-page">
    <!-- Overall Stage Badge -->
    <div class="stage-header">
      <div class="stage-badge">Researching solutions</div>
      <p class="stage-subtitle">Current Progress Stage</p>
    </div>

    <div class="main-content">
      <!-- Left: 8-Dimension Bar Chart -->
      <div class="dimensions-section">
        <h2>Eight Dimension Scores</h2>
        <div class="dimensions-chart">
          <div 
            v-for="dim in eightDimensions" 
            :key="dim.name"
            class="dimension-bar"
            @mouseenter="showDimensionHover(dim.name)"
            @mouseleave="hideDimensionHover"
          >
            <div class="dimension-label">{{ dim.name }}</div>
            <div class="bar-container">
              <div class="bar-background">
                <div 
                  class="bar-fill" 
                  :class="{ 'bar-zero': dim.score === 0 }"
                  :style="{ width: dim.score === 0 ? '3%' : `${(dim.score / 7) * 100}%` }"
                ></div>
              </div>
              <span class="score-value" :class="{ 'score-zero': dim.score === 0 }">
                {{ dim.score.toFixed(1) }}
              </span>
            </div>
            <!-- Hover button - simplified to single assessment -->
            <div v-if="hoveredDimension === dim.name" class="dimension-hover-btn">
              <button @click="startDimensionChat(dim.name)" class="start-chat-btn">
                📋 Start Assessment
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Recent Completed Terms -->
      <div class="recent-terms-section">
        <h3>Recently Completed Terms</h3>
        <div class="terms-table" v-if="recentTerms.length > 0">
          <div v-for="term in recentTerms" :key="term.name" class="term-row">
            <span class="term-name">{{ term.name }}</span>
            <span class="term-score">{{ term.score }}/7</span>
            <span class="term-date">(Last: {{ term.lastDate }})</span>
          </div>
        </div>
        <div v-else class="empty-terms">
          <p>No assessments completed yet.</p>
          <p class="hint">Click on a dimension bar to start your first assessment.</p>
        </div>
      </div>
    </div>

    <!-- Next Steps Suggestions -->
    <div class="next-steps-section">
      <h3>Suggested Next Steps</h3>
      <div class="suggestions">
        <div class="suggestion">Continue with Physiological - Mobility or Sleep</div>
        <div class="suggestion">If experiencing frequent choking, consider discussing thickened liquids and swallowing exercises with your team</div>
      </div>
    </div>

    <!-- Loading -->
    <div class="loading" v-if="isLoading">
      <div class="spinner"></div>
      <p>Loading data...</p>
    </div>

    <!-- Interrupt Warning Dialog -->
    <div v-if="showInterruptWarning" class="interrupt-dialog-overlay">
      <div class="interrupt-dialog">
        <h3>Active Conversation Warning</h3>
        <p>You have an active conversation in progress. Starting a new assessment will interrupt it.</p>
        <p class="conversation-title">Current: {{ activeConversation?.title || 'Untitled Conversation' }}</p>
        <div class="dialog-actions">
          <button @click="cancelInterrupt()" class="btn-cancel">
            Continue Current
          </button>
          <button @click="confirmInterrupt()" class="btn-confirm">
            Start New Assessment
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useSessionStore } from "../stores/session";
import { useRouter } from "vue-router";
import { useAuthStore } from '../stores/auth';
import { useChatStore } from '../stores/chat';
import { conversationsApi } from '../services/api';

const sessionStore = useSessionStore();
const router = useRouter();
const authStore = useAuthStore();
const chatStore = useChatStore();
const showInterruptWarning = ref(false);
const activeConversation = ref<any>(null);
const pendingDimension = ref<string | null>(null);
const isLoading = ref(false);
const hoveredDimension = ref<string | null>(null);

// 8 dimensions data with realistic scores
const eightDimensions = ref([
  { name: "Physiological", score: 4.2 },
  { name: "Safety", score: 3.8 },
  { name: "Love & Belonging", score: 3.5 },
  { name: "Esteem", score: 2.9 },
  { name: "Self-Actualisation", score: 2.1 },
  { name: "Cognitive", score: 4.5 },
  { name: "Aesthetic", score: 3.2 },
  { name: "Transcendence", score: 1.8 }
]);

// Define type for recent term data
interface RecentTerm {
  name: string;
  score: number;  // Changed from string to number
  lastDate: string;
}

// Recent completed terms with sample data
const recentTerms = ref<RecentTerm[]>([
  { name: "Walking and mobility", score: 4.2, lastDate: "Today" },
  { name: "Muscle strength", score: 3.8, lastDate: "Yesterday" },
  { name: "Speech clarity", score: 5.1, lastDate: "2 days ago" },
  { name: "Swallowing ability", score: 4.7, lastDate: "3 days ago" },
  { name: "Breathing comfort", score: 3.5, lastDate: "1 week ago" }
]);

function showDimensionHover(dimensionName: string) {
  hoveredDimension.value = dimensionName;
}

function hideDimensionHover() {
  hoveredDimension.value = null;
}

async function startDimensionChat(dimensionName: string) {
  try {
    if (!authStore.isAuthenticated) {
      sessionStore.setMessage('Please login to start assessment');
      router.push('/login');
      return;
    }

    // Check for active conversation
    try {
      const activeConv = await conversationsApi.getActiveConversation(authStore.token!);
      if (activeConv) {
        // Show interrupt warning
        activeConversation.value = activeConv;
        showInterruptWarning.value = true;
        // Store the dimension to start after interruption
        pendingDimension.value = dimensionName;
        return;
      }
    } catch (error) {
      console.log('No active conversation found, proceeding with new one');
    }

    // Create new dimension-specific conversation
    await startNewDimensionConversation(dimensionName);
    
    // If there's an active conversation, the warning will be shown
    // The action will be executed if user confirms
  } catch (error) {
    console.error('Error starting dimension chat:', error);
    sessionStore.setMessage(`Error starting ${dimensionName} assessment`);
  }
}

async function startNewDimensionConversation(dimensionName: string) {
  try {
    // Create new dimension conversation
    await conversationsApi.createConversation(
      authStore.token!,
      'dimension',
      dimensionName,
      `${dimensionName} Assessment`
    );
    
    // Set dimension focus in session store
    sessionStore.setDimensionFocus(dimensionName);
    
    // Navigate to Chat page
    router.push('/chat');
    
    // Show notification
    sessionStore.setMessage(`Starting ${dimensionName} assessment`);
  } catch (error: any) {
    console.error('Failed to create dimension conversation:', error);
    sessionStore.setMessage(`Failed to start ${dimensionName} assessment: ${error.message}`);
  }
}

function cancelInterrupt() {
  showInterruptWarning.value = false;
  activeConversation.value = null;
  pendingDimension.value = null;
}

async function confirmInterrupt() {
  try {
    if (activeConversation.value && authStore.token) {
      // Interrupt the current conversation
      await conversationsApi.interruptConversation(authStore.token, activeConversation.value.id);
    }
    
    // Close the warning dialog
    showInterruptWarning.value = false;
    
    // Start the pending dimension if exists
    if (pendingDimension.value) {
      await startNewDimensionConversation(pendingDimension.value);
    }
    
    // Clear state
    activeConversation.value = null;
    pendingDimension.value = null;
  } catch (error: any) {
    console.error('Failed to interrupt conversation:', error);
    sessionStore.setMessage(`Failed to interrupt conversation: ${error.message}`);
  }
}

async function loadData() {
  try {
    isLoading.value = true;
    
    // Load scores data from the backend - simplified approach
    const conversationId = chatStore.currentConversationId;
    if (conversationId) {
      // Note: scores endpoint removed in backend simplification
      // Using mock data for display - replace with conversation state later
      const scoresResponse = { dimension_scores: [], term_scores: [] };
      
      // Update dimensions with real scores
      if (scoresResponse.dimension_scores && scoresResponse.dimension_scores.length > 0) {
      // Map backend PNM names to our 8 dimensions display
      const pnmMapping: Record<string, string> = {
        'Physiological': 'Physiological',
        'physiological': 'Physiological',
        'Safety': 'Safety',
        'safety': 'Safety', 
        'Love & Belonging': 'Love & Belonging',
        'love': 'Love & Belonging',
        'Love_Belonging': 'Love & Belonging',
        'Esteem': 'Esteem',
        'esteem': 'Esteem',
        'Self-Actualisation': 'Self-Actualisation',
        'self_actualisation': 'Self-Actualisation',
        'Self_Actualisation': 'Self-Actualisation',
        'Cognitive': 'Cognitive',
        'cognitive': 'Cognitive',
        'Aesthetic': 'Aesthetic',
        'aesthetic': 'Aesthetic',
        'Transcendence': 'Transcendence',
        'transcendence': 'Transcendence'
      };
      
      // Update scores based on dimension scores
      scoresResponse.dimension_scores.forEach((dimScore: any) => {
        const dimensionName = pnmMapping[dimScore.pnm] || pnmMapping[dimScore.pnm.toLowerCase()];
        if (dimensionName) {
          const dim = eightDimensions.value.find(d => d.name === dimensionName);
          if (dim) {
            // Use the score directly (already in 0-7 scale)
            dim.score = dimScore.score_0_7 || 0;
          }
        }
      });
      }
      
      // Update recent terms from term scores
      if (scoresResponse.term_scores && scoresResponse.term_scores.length > 0) {
      // Sort by updated_at and get most recent terms
      const sortedTerms = [...scoresResponse.term_scores]
        .sort((a: any, b: any) => {
          const dateA = new Date(a.updated_at || 0).getTime();
          const dateB = new Date(b.updated_at || 0).getTime();
          return dateB - dateA; // Most recent first
        })
        .slice(0, 5); // Get last 5 completed terms
      
      recentTerms.value = sortedTerms.map((termScore: any) => {
        // Format the date
        const date = termScore.updated_at ? new Date(termScore.updated_at) : new Date();
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        let dateStr = 'Recent';
        if (date.toDateString() === today.toDateString()) {
          dateStr = 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
          dateStr = 'Yesterday';
        } else if (date > new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)) {
          dateStr = 'This week';
        }
        
        return {
          name: termScore.term,
          score: termScore.score_0_7 || 0,  // Keep as number
          lastDate: dateStr
        };
      }) as RecentTerm[];
      }
    }
    
  } catch (error: any) {
    console.error('Error loading data:', error);
    console.log('Conversation ID:', chatStore.currentConversationId);
    
    // Show empty state for new sessions or when no data exists
    // Keep dimensions at 0 for new sessions
    eightDimensions.value.forEach(dim => dim.score = 0);
    recentTerms.value = [];
    
    // Only show error message for actual errors (not empty data)
    if (error.message && !error.message.includes('404')) {
      console.error('Failed to load scores:', error.message);
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.data-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  color: #1f2937;
  background: #f8fafc;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}

/* Stage Header */
.stage-header {
  text-align: center;
  margin-bottom: 32px;
}

.stage-badge {
  display: inline-block;
  background: linear-gradient(135deg, #10b981 0%, #065f46 100%);
  color: white;
  padding: 8px 20px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.stage-subtitle {
  color: #6b7280;
  font-size: 14px;
  margin: 8px 0 0 0;
}

/* Main Content Layout */
.main-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 32px;
  margin-bottom: 32px;
}

/* Dimensions Section */
.dimensions-section h2 {
  color: #1f2937;
  margin-bottom: 24px;
  font-size: 20px;
  font-weight: 600;
}

.dimensions-chart {
  display: grid;
  gap: 12px;
}

.dimension-bar {
  position: relative;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.2s ease;
  cursor: pointer;
}

.dimension-bar:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.dimension-label {
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
  font-size: 15px;
}

.bar-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bar-background {
  flex: 1;
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
  min-width: 3%;
}

.bar-fill.bar-zero {
  background: linear-gradient(90deg, #9ca3af 0%, #6b7280 100%);
  opacity: 0.6;
}

.score-value {
  font-weight: 600;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
  min-width: 32px;
  text-align: right;
}

.score-value.score-zero {
  color: #9ca3af;
  font-style: italic;
}

/* Dimension Hover Button */
.dimension-hover-btn {
  position: absolute;
  top: 50%;
  right: 16px;
  transform: translateY(-50%);
  z-index: 10;
}

.start-chat-btn {
  padding: 6px 12px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.start-chat-btn:hover {
  background: #2563eb;
  transform: scale(1.05);
}

/* Recent Terms Section */
.recent-terms-section h3 {
  color: #1f2937;
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
}

.terms-table {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}

.term-row {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e5e7eb;
  gap: 12px;
}

.term-row:last-child {
  border-bottom: none;
}

.term-name {
  font-weight: 600;
  color: #374151;
  flex: 1;
}

.term-score {
  font-weight: 600;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
}

.term-date {
  font-size: 12px;
  color: #6b7280;
}

/* Empty Terms State */
.empty-terms {
  text-align: center;
  padding: 24px;
  color: #6b7280;
}

.empty-terms p {
  margin: 8px 0;
}

.empty-terms .hint {
  font-size: 14px;
  color: #9ca3af;
  font-style: italic;
}

/* Next Steps Section */
.next-steps-section {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 32px;
}

.next-steps-section h3 {
  color: #1e40af;
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
}

.suggestions {
  display: grid;
  gap: 12px;
}

.suggestion {
  background: white;
  border: 1px solid #e0e7ff;
  border-radius: 8px;
  padding: 12px 16px;
  color: #1e40af;
  position: relative;
  padding-left: 32px;
}

.suggestion::before {
  content: "•";
  color: #3b82f6;
  position: absolute;
  left: 16px;
  font-weight: bold;
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

/* Interrupt Dialog */
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
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.interrupt-dialog h3 {
  color: #ef4444;
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
}

.interrupt-dialog p {
  color: #4b5563;
  margin-bottom: 12px;
  line-height: 1.5;
}

.interrupt-dialog .conversation-title {
  font-weight: 600;
  color: #1f2937;
  background: #f3f4f6;
  padding: 8px 12px;
  border-radius: 6px;
  margin: 16px 0;
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.dialog-actions button {
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-cancel {
  background: #e5e7eb;
  color: #4b5563;
}

.btn-cancel:hover {
  background: #d1d5db;
}

.btn-confirm {
  background: #3b82f6;
  color: white;
}

.btn-confirm:hover {
  background: #2563eb;
}

/* Responsive Design */
@media (max-width: 768px) {
  .main-content {
    grid-template-columns: 1fr;
    gap: 24px;
  }
  
  .data-page {
    padding: 16px;
  }
}
</style>
  