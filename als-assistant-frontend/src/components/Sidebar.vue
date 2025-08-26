<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="logo">🧠 ALS Assistant</h1>
      <p class="subtitle">Self-Awareness Assessment</p>
      <div v-if="authStore.user" class="user-info">
        <span class="user-name">{{ authStore.user.display_name || authStore.user.email }}</span>
      </div>
    </div>
    <nav>
      <RouterLink to="/chat" class="nav-link primary">
        <span class="nav-icon">💬</span>
        <span>Chat</span>
      </RouterLink>
      <RouterLink to="/data" class="nav-link">
        <span class="nav-icon">📊</span>
        <span>Results & Data</span>
      </RouterLink>
      <RouterLink to="/profile" class="nav-link">
        <span class="nav-icon">👤</span>
        <span>Profile</span>
      </RouterLink>
    </nav>
    
    <div class="sidebar-footer">
      <button v-if="authStore.isAuthenticated" @click="handleLogout" class="logout-btn">
        <span class="nav-icon">🚪</span>
        <span>Logout</span>
      </button>
      <div class="version">v2.0 - PNM Focus</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/session'

const authStore = useAuthStore()
const router = useRouter()
const sessionStore = useSessionStore()

function handleLogout() {
  authStore.logout()
  sessionStore.resetSession()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
  color: white;
}

.subtitle {
  font-size: 12px;
  opacity: 0.8;
  margin: 0;
}

nav {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  transition: all 0.2s ease;
  font-size: 14px;
  font-weight: 500;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-link.router-link-active {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nav-link.primary.router-link-active {
  background: rgba(255, 255, 255, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.user-info {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
}

.user-name {
  font-size: 12px;
  opacity: 0.9;
  display: block;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.logout-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 16px;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border-color: rgba(255, 255, 255, 0.3);
}

.version {
  font-size: 11px;
  opacity: 0.6;
  text-align: center;
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    width: 220px;
  }
  
  .sidebar-header {
    padding: 16px;
  }
  
  .logo {
    font-size: 18px;
  }
  
  nav {
    padding: 16px;
  }
  
  .nav-link {
    padding: 10px 12px;
    font-size: 13px;
  }
}
</style>
