import { createRouter, createWebHistory } from "vue-router";
import Chat from "../views/Chat.vue";
import Data from "../views/Data.vue";
import Profile from "../views/Profile.vue";
import Assessment from "../views/Assessment.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/assessment" },
    { path: "/assessment", component: Assessment },
    { path: "/chat", component: Chat },
    { path: "/data", component: Data },
    { path: "/profile", component: Profile },
  ],
});

export default router;
