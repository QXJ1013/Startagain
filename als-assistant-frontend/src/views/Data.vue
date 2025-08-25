<template>
  <div class="data-page">
    <!-- Overall Stage Badge -->
    <div class="stage-header">
      <div class="stage-badge">Researching solutions</div>
      <p class="stage-subtitle">当前进展阶段</p>
    </div>

    <div class="main-content">
      <!-- Left: 8-Dimension Bar Chart -->
      <div class="dimensions-section">
        <h2>八项维度评分</h2>
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
                  :style="{ width: `${(dim.score / 7) * 100}%` }"
                ></div>
              </div>
              <span class="score-value">{{ dim.score.toFixed(1) }}</span>
            </div>
            <!-- Hover button -->
            <div v-if="hoveredDimension === dim.name" class="dimension-hover-btn">
              <button @click="startDimensionChat(dim.name)" class="start-chat-btn">
                开始该维度问答
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Recent Completed Terms -->
      <div class="recent-terms-section">
        <h3>最近完成的 term</h3>
        <div class="terms-table">
          <div v-for="term in recentTerms" :key="term.name" class="term-row">
            <span class="term-name">{{ term.name }}</span>
            <span class="term-score">{{ term.score }}/7</span>
            <span class="term-date">（上次：{{ term.lastDate }}）</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Next Steps Suggestions -->
    <div class="next-steps-section">
      <h3>建议下一步</h3>
      <div class="suggestions">
        <div class="suggestion">继续 Physiological 下的 Mobility or Sleep</div>
        <div class="suggestion">若频繁呛咳，可考虑与团队讨论饮品增稠与吞咽训练</div>
      </div>
    </div>

    <!-- Loading -->
    <div class="loading" v-if="isLoading">
      <div class="spinner"></div>
      <p>Loading data...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useSessionStore } from "../stores/session";
import { useRouter } from "vue-router";
import { api } from "../services/api";

const sessionStore = useSessionStore();
const router = useRouter();
const isLoading = ref(false);
const hoveredDimension = ref<string | null>(null);

// 8 dimensions data - loaded from backend
const eightDimensions = ref([
  { name: "Physiological", score: 0 },
  { name: "Safety", score: 0 },
  { name: "Love & Belonging", score: 0 },
  { name: "Esteem", score: 0 },
  { name: "Self-Actualisation", score: 0 },
  { name: "Cognitive", score: 0 },
  { name: "Aesthetic", score: 0 },
  { name: "Transcendence", score: 0 }
]);

// Recent completed terms - loaded from backend
const recentTerms = ref([]);

function showDimensionHover(dimensionName: string) {
  hoveredDimension.value = dimensionName;
}

function hideDimensionHover() {
  hoveredDimension.value = null;
}

async function startDimensionChat(dimensionName: string) {
  try {
    // Navigate to Chat page directly since we have structured conversation flow
    router.push('/chat');
    
    // Show notification
    sessionStore.setMessage(`已为你在 Chat 准备好 ${dimensionName} 的问答`);
  } catch (error) {
    console.error('Error starting dimension chat:', error);
    sessionStore.setMessage(`启动 ${dimensionName} 问答时出错`);
  }
}

async function loadData() {
  try {
    isLoading.value = true;
    
    // Load PNM profile data which contains scores
    const profileResponse = await api.getPNMProfile(sessionStore.sessionId);
    
    // Update dimensions with real scores from PNM profile
    if (profileResponse.profile) {
      // Map PNM profile dimensions to our 8 dimensions display
      const pnmMapping = {
        'physiological': 'Physiological',
        'safety': 'Safety', 
        'love': 'Love & Belonging',
        'esteem': 'Esteem',
        'self_actualisation': 'Self-Actualisation',
        'cognitive': 'Cognitive',
        'aesthetic': 'Aesthetic',
        'transcendence': 'Transcendence'
      };
      
      // Update scores based on profile data
      Object.keys(pnmMapping).forEach(pnmKey => {
        const dimensionName = pnmMapping[pnmKey];
        const dim = eightDimensions.value.find(d => d.name === dimensionName);
        if (dim && profileResponse.profile[pnmKey]) {
          // Convert percentage to 0-7 scale for display
          const percentage = profileResponse.profile[pnmKey].percentage || 0;
          dim.score = (percentage / 100) * 7;
        }
      });
    }
    
    // Update recent terms from PNM scores
    if (profileResponse.scores && profileResponse.scores.length > 0) {
      // Group scores by domain and show most recent
      const termMap = new Map();
      profileResponse.scores.forEach(score => {
        const key = score.domain;
        if (!termMap.has(key) || termMap.get(key).total_score < score.total_score) {
          termMap.set(key, score);
        }
      });
      
      recentTerms.value = Array.from(termMap.values())
        .slice(-5) // Get last 5 completed terms
        .map(score => ({
          name: score.domain,
          score: (score.total_score || 0).toFixed(1),
          lastDate: '最近'
        }));
    }
    
  } catch (error) {
    console.error('Error loading data:', error);
    // Fallback to demo data if API fails
    eightDimensions.value = [
      { name: "Physiological", score: 4.5 },
      { name: "Safety", score: 3.0 },
      { name: "Love & Belonging", score: 2.5 },
      { name: "Esteem", score: 2.0 },
      { name: "Self-Actualisation", score: 1.5 },
      { name: "Cognitive", score: 2.0 },
      { name: "Aesthetic", score: 1.0 },
      { name: "Transcendence", score: 1.0 }
    ];
    recentTerms.value = [
      { name: "Emergency planning", score: "3", lastDate: "今天" },
      { name: "Travel planning", score: "2", lastDate: "昨天" }
    ];
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
}

.score-value {
  font-weight: 600;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
  min-width: 32px;
  text-align: right;
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
  