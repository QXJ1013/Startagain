<template>
  <div class="profile-container">
    <div class="profile-header">
      <div class="avatar-section">
        <div class="avatar">
          {{ getInitials() }}
        </div>
        <div class="user-details">
          <h1>{{ userProfile.displayName }}</h1>
          <p class="user-email">{{ userProfile.email }}</p>
          <span class="user-status" :class="authStore.isAuthenticated ? 'status-active' : 'status-inactive'">
            {{ authStore.isAuthenticated ? 'Active Account' : 'Account Inactive' }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Personal Information Card -->
    <div class="info-card">
      <h2>Personal Information</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">Name:</span>
          <span class="value">{{ userProfile.displayName }}</span>
        </div>
        <div class="info-item">
          <span class="label">Email:</span>
          <span class="value">{{ userProfile.email }}</span>
        </div>
        <div class="info-item">
          <span class="label">Member Since:</span>
          <span class="value">{{ userProfile.memberSince }}</span>
        </div>
        <div class="info-item">
          <span class="label">Last Login:</span>
          <span class="value">{{ userProfile.lastLogin }}</span>
        </div>
      </div>
    </div>

    <!-- Activity Summary -->
    <div class="info-card">
      <h2>Activity Summary</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">Assessments Completed:</span>
          <span class="value">{{ activityStats.assessmentsCompleted }}</span>
        </div>
        <div class="info-item">
          <span class="label">Questions Answered:</span>
          <span class="value">{{ activityStats.questionsAnswered }}</span>
        </div>
        <div class="info-item">
          <span class="label">Current Session:</span>
          <span class="value">{{ activityStats.currentSession }}</span>
        </div>
        <div class="info-item">
          <span class="label">Last Activity:</span>
          <span class="value">{{ activityStats.lastActivity }}</span>
        </div>
      </div>
    </div>

    <!-- Account Settings -->
    <div class="info-card">
      <h2>Account Settings</h2>
      <div class="settings-actions">
        <button class="settings-btn secondary" @click="changePassword">
          Change Password
        </button>
        <button class="settings-btn secondary" @click="updateProfile">
          Update Profile
        </button>
        <button class="settings-btn primary" @click="exportData">
          Export My Data
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'

// Store references
const authStore = useAuthStore()
const chatStore = useChatStore()

// User profile data
const userProfile = computed(() => ({
  displayName: authStore.displayName || 'ALS Patient User',
  email: authStore.userEmail || 'user@example.com',
  memberSince: 'March 2024',
  lastLogin: 'Today'
}))

// Activity statistics
const activityStats = computed(() => ({
  assessmentsCompleted: 5,
  questionsAnswered: chatStore.messages?.length || 0,
  currentSession: 'In Progress',
  lastActivity: formatLastActivity()
}))

function getInitials(): string {
  const name = userProfile.value.displayName
  return name
    .split(' ')
    .map(word => word.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function formatLastActivity(): string {
  if (chatStore.messages && chatStore.messages.length > 0) {
    const lastMessage = chatStore.messages[chatStore.messages.length - 1]
    if (lastMessage.timestamp) {
      const date = new Date(lastMessage.timestamp)
      return date.toLocaleTimeString()
    }
  }
  return 'No recent activity'
}

function changePassword() {
  alert('Password change functionality would be implemented here')
}

function updateProfile() {
  alert('Profile update functionality would be implemented here')
}

function exportData() {
  alert('Data export functionality would be implemented here')
}

onMounted(() => {
  // Load user profile data if needed
})
</script>

<style scoped>
.profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  background: #f8fafc;
  min-height: 100vh;
}

.profile-header {
  background: white;
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 24px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  font-weight: 600;
}

.user-details h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: #1f2937;
}

.user-email {
  margin: 0 0 12px 0;
  color: #6b7280;
  font-size: 16px;
}

.user-status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-inactive {
  background: #fee2e2;
  color: #991b1b;
}

.info-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-card h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: #1f2937;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}

.info-item:last-child {
  border-bottom: none;
}

.label {
  font-weight: 500;
  color: #374151;
}

.value {
  color: #6b7280;
  text-align: right;
}

.settings-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.settings-btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.settings-btn.primary {
  background: #3b82f6;
  color: white;
}

.settings-btn.primary:hover {
  background: #2563eb;
}

.settings-btn.secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.settings-btn.secondary:hover {
  background: #e5e7eb;
}

@media (max-width: 768px) {
  .profile-container {
    padding: 16px;
  }
  
  .profile-header {
    padding: 24px 16px;
  }
  
  .avatar-section {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }
  
  .info-card {
    padding: 16px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .value {
    text-align: left;
  }
  
  .settings-actions {
    flex-direction: column;
  }
}
</style>