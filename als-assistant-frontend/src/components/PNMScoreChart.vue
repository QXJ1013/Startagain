<template>
  <div class="pnm-score-chart">
    <div class="chart-header">
      <h3>{{ title }}</h3>
      <div class="overall-score">
        <span class="score-value">{{ overallScore }}%</span>
        <span class="score-level">{{ overallLevel }}</span>
      </div>
    </div>

    <!-- PNM Level Breakdown -->
    <div class="pnm-levels">
      <template v-for="(level, levelKey) in pnmData" :key="levelKey">
        <div 
          v-if="levelKey !== 'overall'"
          class="pnm-level"
        >
        <div class="level-header">
          <div class="level-name">{{ levelKey }}</div>
          <div class="level-score">{{ level.percentage.toFixed(1) }}%</div>
        </div>
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ 
              width: `${level.percentage}%`,
              backgroundColor: getColorForScore(level.percentage)
            }"
          ></div>
        </div>
        <div class="level-description">{{ level.level }}</div>
      </div>
      </template>
    </div>

    <!-- Detailed Scores -->
    <div class="detailed-scores" v-if="showDetails">
      <h4>Detailed Assessment Scores</h4>
      <div class="score-grid">
        <div 
          v-for="score in scores" 
          :key="`${score.pnm_level}-${score.domain}`"
          class="score-item"
        >
          <div class="score-domain">
            <div class="domain-name">{{ score.domain }}</div>
            <div class="domain-pnm">{{ score.pnm_level }}</div>
          </div>
          <div class="score-breakdown">
            <div class="dimension">
              <span class="dim-label">Awareness:</span>
              <span class="dim-score">{{ score.awareness_score }}/4</span>
            </div>
            <div class="dimension">
              <span class="dim-label">Understanding:</span>
              <span class="dim-score">{{ score.understanding_score }}/4</span>
            </div>
            <div class="dimension">
              <span class="dim-label">Coping:</span>
              <span class="dim-score">{{ score.coping_score }}/4</span>
            </div>
            <div class="dimension">
              <span class="dim-label">Action:</span>
              <span class="dim-score">{{ score.action_score }}/4</span>
            </div>
          </div>
          <div class="total-score">
            <span class="total-value">{{ score.total_score }}/16</span>
            <span class="total-percent">({{ score.percentage.toFixed(1) }}%)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Toggle Details -->
    <button class="toggle-details" @click="showDetails = !showDetails">
      {{ showDetails ? 'Hide Details' : 'Show Details' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface PNMScore {
  pnm_level: string;
  domain: string;
  awareness_score: number;
  understanding_score: number;
  coping_score: number;
  action_score: number;
  total_score: number;
  percentage: number;
}

interface PNMData {
  overall: {
    score: number;
    possible: number;
    percentage: number;
    level: string;
    domains_assessed: number;
  };
  [key: string]: any;
}

interface Props {
  title?: string;
  pnmData: PNMData;
  scores: PNMScore[];
}

const props = withDefaults(defineProps<Props>(), {
  title: 'PNM Awareness Assessment'
});

const showDetails = ref(false);

const overallScore = computed(() => {
  return props.pnmData.overall?.percentage?.toFixed(1) || '0.0';
});

const overallLevel = computed(() => {
  return props.pnmData.overall?.level || 'Not Assessed';
});

function getColorForScore(percentage: number): string {
  if (percentage >= 80) return '#10b981'; // Green
  if (percentage >= 60) return '#3b82f6'; // Blue  
  if (percentage >= 40) return '#f59e0b'; // Yellow
  if (percentage >= 20) return '#ef4444'; // Red
  return '#9ca3af'; // Gray
}
</script>

<style scoped>
.pnm-score-chart {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.chart-header h3 {
  margin: 0;
  color: #1f2937;
}

.overall-score {
  text-align: right;
}

.score-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #3b82f6;
}

.score-level {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

/* PNM Levels */
.pnm-levels {
  display: grid;
  gap: 16px;
  margin-bottom: 24px;
}

.pnm-level {
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #f3f4f6;
}

.level-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.level-name {
  font-weight: 600;
  color: #374151;
}

.level-score {
  font-weight: 600;
  color: #1f2937;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.level-description {
  font-size: 12px;
  color: #6b7280;
}

/* Detailed Scores */
.detailed-scores {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #f3f4f6;
}

.detailed-scores h4 {
  margin: 0 0 16px 0;
  color: #1f2937;
}

.score-grid {
  display: grid;
  gap: 16px;
}

.score-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 16px;
  align-items: center;
}

.score-domain {
  text-align: left;
}

.domain-name {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.domain-pnm {
  font-size: 12px;
  color: #6b7280;
}

.score-breakdown {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.dimension {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.dim-label {
  color: #6b7280;
}

.dim-score {
  color: #374151;
  font-weight: 500;
}

.total-score {
  text-align: right;
}

.total-value {
  display: block;
  font-size: 16px;
  font-weight: bold;
  color: #1f2937;
}

.total-percent {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

/* Toggle Button */
.toggle-details {
  width: 100%;
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  cursor: pointer;
  font-size: 14px;
  margin-top: 16px;
  transition: all 0.2s ease;
}

.toggle-details:hover {
  background: #f9fafb;
}

/* Responsive */
@media (max-width: 768px) {
  .score-item {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .score-breakdown {
    grid-template-columns: 1fr;
  }
  
  .total-score {
    text-align: left;
  }
}
</style>