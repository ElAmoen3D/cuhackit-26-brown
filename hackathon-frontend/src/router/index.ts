import { createRouter, createWebHistory } from 'vue-router'
// Note: Adjust the path below if your Dashboard.vue is in a different folder
import Dashboard from '../components/Dashboard.vue'

const router = createRouter({
  // Just pass '/' directly instead of using import.meta
  history: createWebHistory('/'), 
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    }
  ]
})

export default router