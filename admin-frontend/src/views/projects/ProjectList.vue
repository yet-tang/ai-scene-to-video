<template>
  <div class="project-list">
    <div class="filter-bar">
      <a-space>
        <a-select
          v-model:value="filters.status"
          placeholder="Filter by status"
          style="width: 180px"
          allowClear
          @change="handleFilterChange"
        >
          <a-select-option v-for="status in statusOptions" :key="status" :value="status">
            {{ status }}
          </a-select-option>
        </a-select>
        <a-input-number
          v-model:value="filters.userId"
          placeholder="User ID"
          style="width: 120px"
          @change="handleFilterChange"
        />
        <a-button @click="handleReset">Reset</a-button>
      </a-space>
    </div>

    <a-table
      :columns="columns"
      :data-source="projects"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">
            {{ record.status }}
          </a-tag>
        </template>
        <template v-if="column.key === 'errorStep'">
          <a-tag v-if="record.errorStep" color="red">
            {{ record.errorStep }}
          </a-tag>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'createdAt'">
          {{ formatDate(record.createdAt) }}
        </template>
        <template v-if="column.key === 'action'">
          <a-button type="link" @click="viewDetail(record.id)">
            View Detail
          </a-button>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { getProjects } from '@/api/projects'
import type { ProjectListItem, ProjectStatus, PageResponse } from '@/types'
import type { TablePaginationConfig } from 'ant-design-vue'

const router = useRouter()
const loading = ref(false)
const projects = ref<ProjectListItem[]>([])

const filters = reactive({
  status: null as ProjectStatus | null,
  userId: null as number | null,
})

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `Total ${total} items`,
})

const statusOptions: ProjectStatus[] = [
  'DRAFT',
  'UPLOADING',
  'ANALYZING',
  'REVIEW',
  'SCRIPT_GENERATING',
  'SCRIPT_GENERATED',
  'AUDIO_GENERATING',
  'AUDIO_GENERATED',
  'RENDERING',
  'COMPLETED',
  'FAILED',
]

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 280, ellipsis: true },
  { title: 'Title', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: 'User ID', dataIndex: 'userId', key: 'userId', width: 100 },
  { title: 'Status', dataIndex: 'status', key: 'status', width: 150 },
  { title: 'Error Step', dataIndex: 'errorStep', key: 'errorStep', width: 150 },
  { title: 'Assets', dataIndex: 'assetCount', key: 'assetCount', width: 80 },
  { title: 'Created At', dataIndex: 'createdAt', key: 'createdAt', width: 180 },
  { title: 'Action', key: 'action', width: 120 },
]

function getStatusColor(status: ProjectStatus): string {
  const colorMap: Record<ProjectStatus, string> = {
    DRAFT: 'default',
    UPLOADING: 'processing',
    ANALYZING: 'processing',
    REVIEW: 'warning',
    SCRIPT_GENERATING: 'processing',
    SCRIPT_GENERATED: 'cyan',
    AUDIO_GENERATING: 'processing',
    AUDIO_GENERATED: 'cyan',
    RENDERING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
  }
  return colorMap[status] || 'default'
}

function formatDate(date: string): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

async function fetchProjects() {
  loading.value = true
  try {
    const response: PageResponse<ProjectListItem> = await getProjects({
      page: pagination.current - 1,
      size: pagination.pageSize,
      status: filters.status,
      userId: filters.userId,
    })
    projects.value = response.content
    pagination.total = response.totalElements
  } finally {
    loading.value = false
  }
}

function handleTableChange(pag: TablePaginationConfig) {
  pagination.current = pag.current || 1
  pagination.pageSize = pag.pageSize || 10
  fetchProjects()
}

function handleFilterChange() {
  pagination.current = 1
  fetchProjects()
}

function handleReset() {
  filters.status = null
  filters.userId = null
  pagination.current = 1
  fetchProjects()
}

function viewDetail(id: string) {
  router.push({ name: 'ProjectDetail', params: { id } })
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.project-list {
  width: 100%;
}

.filter-bar {
  margin-bottom: 16px;
}
</style>
