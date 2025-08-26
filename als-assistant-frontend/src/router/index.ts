import { createRouter, createWebHistory } from "vue-router";
import Chat from "../views/Chat.vue";
import Data from "../views/Data.vue";
import Profile from "../views/Profile.vue";
import Login from "../views/Login.vue";
import { useAuthStore } from "../stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/chat" },
    { path: "/login", component: Login, meta: { requiresAuth: false } },
    { path: "/chat", component: Chat, meta: { requiresAuth: true } },
    { path: "/data", component: Data, meta: { requiresAuth: true } },
    { path: "/profile", component: Profile, meta: { requiresAuth: true } },
  ],
});

// Authentication guard
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();
  
  // Check if user is authenticated from localStorage token
  if (!authStore.isAuthenticated) {
    await authStore.checkAuth();
  }
  
  // Check if route requires authentication
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if not authenticated
    next('/login');
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    // Redirect to chat if already authenticated
    next('/chat');
  } else {
    next();
  }
});

export default router;
