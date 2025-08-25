<template>
  <div class="layout">
    <Sidebar />
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import Sidebar from "./components/Sidebar.vue";
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
