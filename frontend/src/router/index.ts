import { createRouter, createWebHistory } from 'vue-router'
import CreateProject from '../views/CreateProject.vue'
import ReviewTimeline from '../views/ReviewTimeline.vue'
import VideoResult from '../views/VideoResult.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/create'
    },
    {
      path: '/create',
      name: 'create',
      component: CreateProject
    },
    {
      path: '/review/:id',
      name: 'review',
      component: ReviewTimeline
    },
    {
      path: '/result/:id',
      name: 'result',
      component: VideoResult
    }
  ]
})

export default router
