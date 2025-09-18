<template>
  <div class="profile-container">
    <!-- User Header -->
    <div class="profile-header">
      <div class="avatar-section">
        <div class="avatar">
          {{ getInitials() }}
        </div>
        <div class="user-details">
          <h1>{{ userProfile.displayName }}</h1>
          <p class="user-email">{{ userProfile.email }}</p>
          <span class="user-status" :class="authStore.isAuthenticated ? 'status-active' : 'status-inactive'">
            {{ authStore.isAuthenticated ? 'Active' : 'Inactive' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Basic Info Card -->
    <div class="info-card">
      <h2>Basic Information</h2>
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
      </div>
    </div>

    <!-- Actions -->
    <div class="actions">
      <button class="action-btn secondary" @click="updateProfile">
        Update Profile
      </button>
      <button class="action-btn secondary" @click="changePassword">
        Change Password
      </button>
      <button class="action-btn primary" @click="logout">
        Logout
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const chatStore = useChatStore()
const router = useRouter()

const userProfile = computed(() => ({
  displayName: authStore.displayName || 'User',
  email: authStore.userEmail || 'user@example.com',
  memberSince: 'March 2024'
}))

const activityStats = computed(() => ({
  assessmentsCompleted: 5,
  questionsAnswered: chatStore.messages?.length || 0
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

function updateProfile() {
  alert('Profile update functionality would be implemented here')
}

function changePassword() {
  alert('Password change functionality would be implemented here')
}

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.profile-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px;
  background: #f8fafc;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
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
  gap: 20px;
}

.avatar {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 22px;
  font-weight: 600;
}

.user-details h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
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
  font-size: 18px;
  color: #1f2937;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
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

.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.action-btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.primary {
  background: #ef4444;
  color: white;
}

.action-btn.primary:hover {
  background: #dc2626;
}

.action-btn.secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.action-btn.secondary:hover {
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

  .actions {
    flex-direction: column;
  }
}
</style>