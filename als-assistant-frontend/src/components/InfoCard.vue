<template>
    <div class="card">
      <div class="title">{{title}}</div>
      <ul>
        <li v-for="(b,i) in bullets" :key="i">{{ b }}</li>
      </ul>
      <div class="meta">
        <a v-if="url" :href="url" target="_blank" rel="noopener">Source</a>
        <span v-if="source"> · {{ source }}</span>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  defineProps<{
    title: string;
    bullets: string[];
    url?: string;
    source?: string;
  }>();
  </script>
  
  <style scoped>
  .card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; background: #fff; }
  .title { font-weight: 600; margin-bottom: 8px; }
  ul { margin: 0; padding-left: 16px; }
  .meta { margin-top: 8px; font-size: 12px; color:#6b7280; }
  </style>
  