<template>
  <div class="project-list-page">
    <van-nav-bar title="项目列表" fixed placeholder />

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <van-cell
          v-for="project in list"
          :key="project.id"
          is-link
          @click="goToDetail(project.id)"
        >
          <template #title>
            <div class="van-ellipsis font-bold">{{ project.title }}</div>
            <div class="text-xs text-gray-500">ID: {{ project.id }}</div>
            <div class="text-xs text-gray-500">{{ formatDate(project.createdAt) }}</div>
          </template>
          <template #value>
            <van-tag :type="getStatusType(project.status)">{{ project.status }}</van-tag>
          </template>
        </van-cell>
      </van-list>
    </van-pull-refresh>

    <!-- Floating Action Button to Create Project -->
    <div class="fab-container">
      <van-button icon="plus" type="primary" round shadow @click="goToCreate" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { projectApi } from '../api/project'
import { showToast } from 'vant'

interface ProjectListItem {
  id: string
  title: string
  status: string
  createdAt: string
}

const router = useRouter()
const list = ref<ProjectListItem[]>([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)
const pageSize = 10

const onLoad = async () => {
  if (refreshing.value) {
    list.value = []
    refreshing.value = false
  }

  try {
    const { data } = await projectApi.list({ page: page.value, size: pageSize })
    // Assuming backend returns { content: [], totalElements: number, last: boolean } or similar page structure
    // Adjust based on actual API response. 
    // If API returns list directly:
    const items = Array.isArray(data) ? data : (data.content || [])
    
    if (items.length < pageSize) {
      finished.value = true
    }

    list.value.push(...items)
    page.value++
  } catch (error) {
    console.error('Failed to load projects', error)
    showToast('加载失败')
    finished.value = true
  } finally {
    loading.value = false
  }
}

const onRefresh = () => {
  finished.value = false
  loading.value = true
  page.value = 1
  onLoad()
}

const goToDetail = (id: string) => {
  router.push(`/projects/${id}`)
}

const goToCreate = () => {
  router.push('/create')
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'FAILED':
    case 'RENDER_FAILED':
      return 'danger'
    case 'PROCESSING':
    case 'RENDERING':
      return 'primary'
    default:
      return 'default'
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}
</script>

<style scoped>
.project-list-page {
  background-color: #f7f8fa;
  min-height: 100vh;
  padding-bottom: 20px;
}

.fab-container {
  position: fixed;
  bottom: 30px;
  right: 20px;
  z-index: 99;
}

.fab-container .van-button {
  width: 50px;
  height: 50px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}
</style>
