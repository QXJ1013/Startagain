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
          <div class="value-container">
            <span v-if="!editingName" class="value">{{ userProfile.displayName }}</span>
            <input
              v-else
              v-model="editData.displayName"
              type="text"
              class="edit-input"
              @keyup.enter="saveProfile"
              @keyup.esc="cancelEdit"
              placeholder="Enter your name"
            />
            <button
              v-if="!editingName"
              @click="startEditName"
              class="edit-btn"
              title="Edit name"
            >
              ✏️
            </button>
            <div v-else class="edit-actions">
              <button @click="saveProfile" class="save-btn" title="Save">✓</button>
              <button @click="cancelEdit" class="cancel-btn" title="Cancel">✗</button>
            </div>
          </div>
        </div>
        <div class="info-item">
          <span class="label">Email:</span>
          <div class="value-container">
            <span v-if="!editingEmail" class="value">{{ userProfile.email }}</span>
            <input
              v-else
              v-model="editData.email"
              type="email"
              class="edit-input"
              @keyup.enter="saveProfile"
              @keyup.esc="cancelEdit"
              placeholder="Enter your email"
            />
            <button
              v-if="!editingEmail"
              @click="startEditEmail"
              class="edit-btn"
              title="Edit email"
            >
              ✏️
            </button>
            <div v-else class="edit-actions">
              <button @click="saveProfile" class="save-btn" title="Save">✓</button>
              <button @click="cancelEdit" class="cancel-btn" title="Cancel">✗</button>
            </div>
          </div>
        </div>
        <div class="info-item">
          <span class="label">Member Since:</span>
          <span class="value">{{ userProfile.memberSince }}</span>
        </div>
      </div>
    </div>

    <!-- Password Change Card -->
    <div class="info-card">
      <h2>Security</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">Password:</span>
          <div class="value-container">
            <span v-if="!editingPassword" class="value">••••••••</span>
            <div v-else class="password-change-form">
              <input
                v-model="passwordData.currentPassword"
                type="password"
                class="edit-input password-input"
                placeholder="Current password"
              />
              <input
                v-model="passwordData.newPassword"
                type="password"
                class="edit-input password-input"
                placeholder="New password"
              />
              <input
                v-model="passwordData.confirmPassword"
                type="password"
                class="edit-input password-input"
                placeholder="Confirm new password"
              />
            </div>
            <button
              v-if="!editingPassword"
              @click="startEditPassword"
              class="edit-btn"
              title="Change password"
            >
              ✏️
            </button>
            <div v-else class="edit-actions">
              <button @click="savePassword" class="save-btn" title="Save">✓</button>
              <button @click="cancelPasswordEdit" class="cancel-btn" title="Cancel">✗</button>
            </div>
          </div>
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
      <button class="action-btn primary" @click="logout">
        Logout
      </button>
    </div>

    <!-- Loading overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>Updating...</p>
    </div>

    <!-- Success/Error messages -->
    <div v-if="message" :class="['message', messageType]">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import { useRouter } from 'vue-router'
import { userApi } from '../services/api'

const authStore = useAuthStore()
const chatStore = useChatStore()
const router = useRouter()

// Reactive state
const loading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

// Edit states
const editingName = ref(false)
const editingEmail = ref(false)
const editingPassword = ref(false)

// Edit data
const editData = reactive({
  displayName: '',
  email: ''
})

// Password data
const passwordData = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

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

// Edit functions
function startEditName() {
  editData.displayName = userProfile.value.displayName
  editingName.value = true
}

function startEditEmail() {
  editData.email = userProfile.value.email
  editingEmail.value = true
}

function startEditPassword() {
  passwordData.currentPassword = ''
  passwordData.newPassword = ''
  passwordData.confirmPassword = ''
  editingPassword.value = true
}

function cancelEdit() {
  editingName.value = false
  editingEmail.value = false
}

function cancelPasswordEdit() {
  editingPassword.value = false
  passwordData.currentPassword = ''
  passwordData.newPassword = ''
  passwordData.confirmPassword = ''
}

async function saveProfile() {
  if (!authStore.token) {
    showMessage('Please login first', 'error')
    return
  }

  const updates: any = {}

  if (editingName.value && editData.displayName.trim() !== userProfile.value.displayName) {
    updates.display_name = editData.displayName.trim()
  }

  if (editingEmail.value && editData.email.trim() !== userProfile.value.email) {
    updates.email = editData.email.trim()
  }

  if (Object.keys(updates).length === 0) {
    showMessage('No changes to save', 'error')
    cancelEdit()
    return
  }

  try {
    loading.value = true
    const result = await userApi.updateProfile(authStore.token, updates)

    // Update auth store with new data
    if (updates.display_name) {
      authStore.user!.display_name = result.display_name
    }
    if (updates.email) {
      authStore.user!.email = result.email
    }

    showMessage('Profile updated successfully!', 'success')
    cancelEdit()
  } catch (error: any) {
    console.error('Profile update error:', error)
    showMessage(error.message || 'Failed to update profile', 'error')
  } finally {
    loading.value = false
  }
}

async function savePassword() {
  if (!authStore.token) {
    showMessage('Please login first', 'error')
    return
  }

  if (!passwordData.currentPassword || !passwordData.newPassword) {
    showMessage('Please fill in all password fields', 'error')
    return
  }

  if (passwordData.newPassword !== passwordData.confirmPassword) {
    showMessage('New passwords do not match', 'error')
    return
  }

  if (passwordData.newPassword.length < 8) {
    showMessage('New password must be at least 8 characters', 'error')
    return
  }

  try {
    loading.value = true
    await userApi.changePassword(authStore.token, passwordData.currentPassword, passwordData.newPassword)

    showMessage('Password changed successfully!', 'success')
    cancelPasswordEdit()
  } catch (error: any) {
    console.error('Password change error:', error)
    showMessage(error.message || 'Failed to change password', 'error')
  } finally {
    loading.value = false
  }
}

function showMessage(text: string, type: 'success' | 'error') {
  message.value = text
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 5000)
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
  position: relative;
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
  min-width: 120px;
}

.value-container {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: flex-end;
}

.value {
  color: #6b7280;
  text-align: right;
}

.edit-input {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
  min-width: 150px;
}

.edit-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.password-change-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 200px;
}

.password-input {
  min-width: 200px;
}

.edit-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.edit-btn:hover {
  background: #f3f4f6;
}

.edit-actions {
  display: flex;
  gap: 4px;
}

.save-btn, .cancel-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  transition: background-color 0.2s;
}

.save-btn {
  color: #059669;
}

.save-btn:hover {
  background: #d1fae5;
}

.cancel-btn {
  color: #dc2626;
}

.cancel-btn:hover {
  background: #fee2e2;
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

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.message {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: 500;
  z-index: 1001;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.message.success {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.message.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
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

  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .value-container {
    justify-content: flex-start;
    width: 100%;
  }

  .password-change-form,
  .password-input,
  .edit-input {
    min-width: 100%;
  }

  .actions {
    flex-direction: column;
  }
}
</style>