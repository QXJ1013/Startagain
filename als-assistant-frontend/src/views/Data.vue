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
            @click="startDimensionChat(dim.name)"
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
            <!-- Hover button -->
            <div v-if="hoveredDimension === dim.name" class="dimension-hover-btn">
              <button @click="startDimensionChat(dim.name)" class="start-chat-btn">
                📋 Start Assessment
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: All Term Scores -->
      <div class="terms-scores-section">
        <div class="terms-header">
          <h3>All Term Scores</h3>
          <button v-if="allTerms.length > 5" @click="showAllTermsModal = true" class="view-all-btn">
            View All ({{ allTerms.length }})
          </button>
        </div>
        <div class="terms-table" v-if="allTerms.length > 0">
          <div v-for="term in displayedTerms" :key="term.name" class="term-row">
            <span class="term-name" :title="term.name">{{ term.name }}</span>
            <span class="term-score">{{ term.score.toFixed(1) }}/7</span>
            <span class="term-date">{{ term.lastDate }}</span>
          </div>
          <div v-if="allTerms.length > 5" class="more-terms-indicator">
            +{{ allTerms.length - 5 }} more terms
          </div>
        </div>
        <div v-else class="no-terms">
          No completed assessments yet
        </div>
      </div>
    </div>

    <!-- Scoring Standards Explanation -->
    <div class="scoring-standards-section">
      <h3>Assessment Scoring Standards</h3>
      <div class="scoring-explanations">
        <div class="scoring-explanation">
          <strong>Score Scale:</strong> All assessments use a 0-7 point scale where 0 represents optimal functioning and 7 indicates significant challenges requiring immediate attention.
        </div>
        <div class="scoring-explanation">
          <strong>Evaluation Method:</strong> Scores are determined through either structured multiple-choice responses or AI-powered analysis of your detailed answers, ensuring comprehensive and personalized assessment.
        </div>
        <div class="scoring-explanation">
          <strong>Progress Tracking:</strong> Your scores help identify areas of strength and concern across eight key life dimensions, enabling targeted support and care planning.
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div class="loading" v-if="isLoading">
      <div class="spinner"></div>
      <p>Loading data...</p>
    </div>

    <!-- All Terms Modal -->
    <div v-if="showAllTermsModal" class="modal-overlay" @click="showAllTermsModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>All Term Scores ({{ allTerms.length }})</h3>
          <button @click="showAllTermsModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="all-terms-grid">
            <div v-for="term in allTerms" :key="term.name" class="modal-term-row">
              <div class="modal-term-info">
                <span class="modal-term-name">{{ term.name }}</span>
                <span class="modal-term-dimension">{{ term.dimension }}</span>
              </div>
              <div class="modal-term-score">
                <span class="score-value">{{ term.score.toFixed(1) }}/7</span>
                <span class="score-date">{{ term.lastDate }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useSessionStore } from "../stores/session";
import { useRouter } from "vue-router";
import { useAuthStore } from '../stores/auth';
import { useChatStore } from '../stores/chat';
import { conversationsApi } from '../services/api';

const sessionStore = useSessionStore();
const router = useRouter();
const authStore = useAuthStore();
const chatStore = useChatStore();
const isLoading = ref(false);
const hoveredDimension = ref<string | null>(null);
const showAllTermsModal = ref(false);

function showDimensionHover(dimensionName: string) {
  hoveredDimension.value = dimensionName;
}

function hideDimensionHover() {
  hoveredDimension.value = null;
}

// 8 dimensions data - loaded from backend
const eightDimensions = ref([
  { name: "Physiological", score: 0.0, assessments_count: 0 },
  { name: "Safety", score: 0.0, assessments_count: 0 },
  { name: "Love & Belonging", score: 0.0, assessments_count: 0 },
  { name: "Esteem", score: 0.0, assessments_count: 0 },
  { name: "Self-Actualisation", score: 0.0, assessments_count: 0 },
  { name: "Cognitive", score: 0.0, assessments_count: 0 },
  { name: "Aesthetic", score: 0.0, assessments_count: 0 },
  { name: "Transcendence", score: 0.0, assessments_count: 0 }
]);

const userStats = ref({
  total_conversations: 0,
  completed_assessments: 0
});

// Define type for term data
interface TermData {
  name: string;
  score: number;
  lastDate: string;
  dimension?: string;
}

// All terms data - loaded from backend
const allTerms = ref<TermData[]>([]);

// Computed property for displayed terms (first 5)
const displayedTerms = computed(() => allTerms.value.slice(0, 5));


async function startDimensionChat(dimensionName: string) {
  try {
    if (!authStore.isAuthenticated || !authStore.token) {
      sessionStore.setMessage('Please login to start assessment');
      router.push('/login');
      return;
    }

    console.log(`[DATA.VUE] Starting fresh ${dimensionName} assessment`);

    // STEP 1: Complete reset of all frontend state
    chatStore.reset(); // This clears all messages and conversation state
    sessionStore.resetSession(); // This clears session state

    // STEP 2: Clear localStorage keys that might interfere
    const sessionKeys = Object.keys(localStorage).filter(k => k.startsWith('als_session'));
    sessionKeys.forEach(k => {
      if (k !== 'als_session_id') { // Keep session ID but clear others
        localStorage.removeItem(k);
      }
    });

    // STEP 3: Defensive delay to ensure frontend state clears
    await new Promise(resolve => setTimeout(resolve, 100));

    console.log(`[DATA.VUE] Creating new conversation for ${dimensionName}`);

    // STEP 4: Create fresh conversation using conversations API
    const newConv = await conversationsApi.createConversation(
      authStore.token,
      'dimension',
      dimensionName,
      `${dimensionName} Assessment - ${new Date().toLocaleTimeString()}`
    );

    console.log(`[DATA.VUE] Created conversation ${newConv.id} for ${dimensionName}`);

    // STEP 5: Set fresh conversation state in chat store
    chatStore.setCurrentConversation(newConv.id);
    chatStore.conversationType = 'dimension';
    chatStore.dimensionName = dimensionName;

    // STEP 6: Set dimension focus for Chat.vue to pick up
    sessionStore.setDimensionFocus(dimensionName);

    // STEP 7: Navigate to chat page - it will handle the initial question
    router.push('/chat');

    // STEP 8: Show notification with timestamp to confirm fresh start
    sessionStore.setMessage(`Starting ${dimensionName} assessment (${new Date().toLocaleTimeString()})`);

  } catch (error: any) {
    console.error('Error starting dimension chat:', error);
    if (error.message && error.message.includes('401')) {
      authStore.logout();
      sessionStore.setMessage('Session expired. Please login again.');
      router.push('/login');
    } else {
      sessionStore.setMessage(`Error starting ${dimensionName} assessment`);
    }
  }
}


// Load real user data from backend
async function loadUserData() {
  if (!authStore.token) return;

  try {
    isLoading.value = true;
    const scoresData = await conversationsApi.getUserScoresSummary(authStore.token);

    // Update dimensions with real data
    eightDimensions.value = scoresData.dimensions;

    // Update user stats
    userStats.value = {
      total_conversations: scoresData.total_conversations,
      completed_assessments: scoresData.completed_assessments
    };

    // Load all terms from conversations
    await loadAllTerms();

  } catch (error: any) {
    console.error('Failed to load user data:', error);
    sessionStore.setMessage(`Failed to load data: ${error.message}`);
  } finally {
    isLoading.value = false;
  }
}

// Load all completed terms from database
async function loadAllTerms() {
  try {
    if (!authStore.token) return;

    // Get scores summary data which now includes term_scores
    const scoresData = await conversationsApi.getUserScoresSummary(authStore.token);

    // Extract all term scores from API response
    const termScores: TermData[] = [];

    if (scoresData.term_scores) {
      for (const termScore of scoresData.term_scores) { // Remove slice to get all terms
        // Parse date
        let dateStr = 'Recent';
        try {
          const date = new Date(termScore.updated_at);
          const now = new Date();
          const daysAgo = Math.floor((now.getTime() - date.getTime()) / (24 * 60 * 60 * 1000));

          if (daysAgo === 0) {
            dateStr = 'Today';
          } else if (daysAgo === 1) {
            dateStr = 'Yesterday';
          } else if (daysAgo < 7) {
            dateStr = `${daysAgo} day${daysAgo > 1 ? 's' : ''} ago`;
          } else {
            dateStr = 'Last week';
          }
        } catch (error) {
          dateStr = 'Recent';
        }

        termScores.push({
          name: termScore.term, // Show actual term name, not PNM dimension
          score: termScore.score,
          lastDate: dateStr,
          dimension: termScore.pnm // Add dimension info for modal
        });
      }
    }

    allTerms.value = termScores;

  } catch (error: any) {
    console.error('Failed to load all terms:', error);
    allTerms.value = [];
  }
}

async function loadData() {
  // Use the new loadUserData function instead
  await loadUserData();
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
  cursor: pointer;
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
  right: 50px;
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
  pointer-events: auto;
  z-index: 20;
  position: relative;
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

/* No Terms State */
.no-terms {
  text-align: center;
  padding: 20px;
  color: #6b7280;
  font-style: italic;
}

/* Scoring Standards Section */
.scoring-standards-section {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 32px;
}

.scoring-standards-section h3 {
  color: #1e40af;
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
}

.scoring-explanations {
  display: grid;
  gap: 12px;
}

.scoring-explanation {
  background: white;
  border: 1px solid #e0e7ff;
  border-radius: 8px;
  padding: 16px;
  color: #1e40af;
  line-height: 1.5;
}

.scoring-explanation strong {
  color: #1d4ed8;
  font-weight: 600;
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

/* Terms Header */
.terms-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.view-all-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.view-all-btn:hover {
  background: #2563eb;
}

.more-terms-indicator {
  text-align: center;
  padding: 8px;
  color: #6b7280;
  font-size: 12px;
  border-top: 1px solid #e5e7eb;
  margin-top: 4px;
}

/* Modal Styles */
.modal-overlay {
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

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #1f2937;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
}

.modal-body {
  padding: 20px 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.all-terms-grid {
  display: grid;
  gap: 12px;
}

.modal-term-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.modal-term-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.modal-term-name {
  font-weight: 500;
  color: #1f2937;
  font-size: 14px;
}

.modal-term-dimension {
  font-size: 12px;
  color: #6b7280;
  background: #e5e7eb;
  padding: 2px 6px;
  border-radius: 4px;
  width: fit-content;
}

.modal-term-score {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.score-value {
  font-weight: 600;
  color: #059669;
  font-size: 14px;
}

.score-date {
  font-size: 11px;
  color: #9ca3af;
}

/* Terms name with tooltip */
.term-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
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
  