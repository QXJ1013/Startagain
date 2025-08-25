<template>
    <div>
      <div class="title">Profile</div>
      <p>Session ID: <code>{{ s.sessionId }}</code></p>
      <button class="btn" @click="health">Health Check</button>
      <pre class="pre" v-if="status">{{ status }}</pre>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref } from "vue";
  import { useSessionStore } from "../stores/session";
  import { api } from "../services/api";
  const s = useSessionStore();
  const status = ref("");
  
  async function health() {
    const res = await api.health();
    status.value = JSON.stringify(res, null, 2);
  }
  </script>
  
  <style scoped>
  .title { font-size:20px; font-weight:700; margin-bottom:8px; }
  .btn { padding:8px 12px; border:1px solid #e5e7eb; border-radius:8px; background:#fff; cursor:pointer; }
  .pre { background:#0b1020; color:#d1d5db; padding:12px; border-radius:8px; margin-top:12px; overflow:auto; }
  </style>
  