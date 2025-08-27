<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2>{{ isLogin ? 'Login' : 'Register' }}</h2>
      
      <form @submit.prevent="handleSubmit">
        <!-- Email Input -->
        <div class="form-group">
          <label for="email">Email</label>
          <input 
            id="email"
            v-model="email"
            type="email"
            placeholder="your@email.com"
            required
            autocomplete="email"
          />
        </div>
        
        <!-- Password Input -->
        <div class="form-group">
          <label for="password">Password</label>
          <input 
            id="password"
            v-model="password"
            type="password"
            placeholder="••••••••"
            required
            :autocomplete="isLogin ? 'current-password' : 'new-password'"
          />
        </div>
        
        <!-- Display Name (Register only) -->
        <div v-if="!isLogin" class="form-group">
          <label for="displayName">Display Name (Optional)</label>
          <input 
            id="displayName"
            v-model="displayName"
            type="text"
            placeholder="Your name"
            autocomplete="name"
          />
        </div>
        
        <!-- Error Message -->
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <!-- Submit Button -->
        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? 'Processing...' : (isLogin ? 'Login' : 'Register') }}
        </button>
      </form>
      
      <!-- Toggle Login/Register -->
      <div class="auth-toggle">
        <span v-if="isLogin">
          Don't have an account? 
          <a @click="toggleMode" class="toggle-link">Register</a>
        </span>
        <span v-else>
          Already have an account? 
          <a @click="toggleMode" class="toggle-link">Login</a>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useSessionStore } from '../stores/session'
import { debugAuth } from '../utils/debug'

// Run debug on mount
debugAuth()

const router = useRouter()
const authStore = useAuthStore()
const sessionStore = useSessionStore()

// Form state
const isLogin = ref(true)
const email = ref('')
const password = ref('')
const displayName = ref('')
const loading = ref(false)
const error = ref('')

function toggleMode() {
  isLogin.value = !isLogin.value
  error.value = ''
}

async function handleSubmit() {
  error.value = ''
  loading.value = true
  
  try {
    if (isLogin.value) {
      await authStore.login(email.value, password.value)
      sessionStore.setMessage('Login successful!')
    } else {
      await authStore.register(
        email.value, 
        password.value, 
        displayName.value || undefined
      )
      sessionStore.setMessage('Registration successful!')
    }
    
    // Navigate to chat after successful auth
    router.push('/chat')
  } catch (err: any) {
    error.value = err.message || 'Authentication failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.auth-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

h2 {
  color: #1f2937;
  margin-bottom: 32px;
  text-align: center;
  font-size: 28px;
  font-weight: 700;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  color: #4b5563;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
}

input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
  transition: all 0.2s;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.error-message {
  background: #fee2e2;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  border: 1px solid #fecaca;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-toggle {
  text-align: center;
  margin-top: 24px;
  color: #6b7280;
  font-size: 14px;
}

.toggle-link {
  color: #6366f1;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}

.toggle-link:hover {
  color: #4f46e5;
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 480px) {
  .auth-card {
    padding: 24px;
  }
  
  h2 {
    font-size: 24px;
  }
}
</style>