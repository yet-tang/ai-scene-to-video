import { createRouter, createWebHistory } from 'vue-router'
import CreateProject from '../views/CreateProject.vue'
import ReviewTimeline from '../views/ReviewTimeline.vue'
import VideoResult from '../views/VideoResult.vue'
import ProjectList from '../views/ProjectList.vue'
import ProjectDetail from '../views/ProjectDetail.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/projects'
    },
    {
      path: '/projects',
      name: 'ProjectList',
      component: ProjectList
    },
    {
      path: '/projects/:id',
      name: 'ProjectDetail',
      component: ProjectDetail
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
