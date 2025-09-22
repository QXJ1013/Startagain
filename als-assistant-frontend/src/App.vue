<template>
  <div class="layout" v-if="!isLoginPage">
    <Sidebar />
    <main class="content">
      <router-view />
    </main>
  </div>
  <router-view v-else />
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import Sidebar from "./components/Sidebar.vue";

const route = useRoute()
const authStore = useAuthStore()
const isLoginPage = computed(() => route.path === '/login')

// Check authentication status on app startup
onMounted(async () => {
  try {
    await authStore.checkAuth()
  } catch (error) {
    console.error('Auth check failed on startup:', error)
    // Continue loading the app even if auth check fails
  }
})
</script>

<style scoped>
.layout { 
  display: grid; 
  grid-template-columns: 280px 1fr; 
  min-height: 100vh;
  background: #f8fafc;
}
.content { 
  padding: 0;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .layout {
    grid-template-columns: 220px 1fr;
  }
}
</style>
