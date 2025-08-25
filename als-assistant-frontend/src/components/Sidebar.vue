<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="logo">🧠 ALS Assistant</h1>
      <p class="subtitle">Self-Awareness Assessment</p>
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
      <div class="version">v2.0 - PNM Focus</div>
    </div>
  </aside>
</template>

<script setup lang="ts"></script>

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

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
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
