<template>
  <div class="system-health">
    <div class="toolbar">
      <a-button type="primary" @click="fetchHealth" :loading="loading">
        <template #icon><ReloadOutlined /></template>
        Refresh
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-row :gutter="16" v-if="health">
        <!-- Backend Service -->
        <a-col :span="6">
          <a-card class="service-card">
            <template #title>
              <CloudServerOutlined /> Backend
            </template>
            <div class="service-status">
              <a-badge :status="getStatusBadge(health.backend.status)" :text="health.backend.status" />
            </div>
            <div class="service-metric">
              Response Time: {{ health.backend.responseTimeMs }}ms
            </div>
            <div v-if="health.backend.message" class="service-message">
              {{ health.backend.message }}
            </div>
          </a-card>
        </a-col>

        <!-- Database -->
        <a-col :span="6">
          <a-card class="service-card">
            <template #title>
              <DatabaseOutlined /> Database
            </template>
            <div class="service-status">
              <a-badge :status="getStatusBadge(health.database.status)" :text="health.database.status" />
            </div>
            <div class="service-metric">
              Response Time: {{ health.database.responseTimeMs }}ms
            </div>
            <div v-if="health.database.message" class="service-message">
              {{ health.database.message }}
            </div>
          </a-card>
        </a-col>

        <!-- Redis -->
        <a-col :span="6">
          <a-card class="service-card">
            <template #title>
              <ThunderboltOutlined /> Redis
            </template>
            <div class="service-status">
              <a-badge :status="getStatusBadge(health.redis.status)" :text="health.redis.status" />
            </div>
            <div class="service-metric">
              Response Time: {{ health.redis.responseTimeMs }}ms
            </div>
            <div v-if="health.redis.message" class="service-message">
              {{ health.redis.message }}
            </div>
          </a-card>
        </a-col>

        <!-- Celery -->
        <a-col :span="6">
          <a-card class="service-card">
            <template #title>
              <ClusterOutlined /> Celery
            </template>
            <div class="service-status">
              <a-badge
                :status="health.celery.workers.length > 0 ? 'success' : 'error'"
                :text="health.celery.workers.length > 0 ? 'HEALTHY' : 'DOWN'"
              />
            </div>
            <div class="service-metric">
              Queue: {{ health.celery.queueName }}
            </div>
            <div class="service-metric">
              Pending: {{ health.celery.pendingTasks }} | Active: {{ health.celery.activeTasks }}
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- Celery Workers Detail -->
      <a-card v-if="health && health.celery.workers.length > 0" title="Celery Workers" style="margin-top: 16px">
        <a-table
          :columns="workerColumns"
          :data-source="health.celery.workers"
          :pagination="false"
          row-key="name"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-badge :status="record.status === 'active' ? 'success' : 'warning'" :text="record.status" />
            </template>
          </template>
        </a-table>
      </a-card>

      <a-empty v-if="!health && !loading" description="Failed to load system health" />
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  ReloadOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  ClusterOutlined,
} from '@ant-design/icons-vue'
import { getSystemHealth } from '@/api/system'
import type { SystemHealth } from '@/types'

const loading = ref(false)
const health = ref<SystemHealth | null>(null)

const workerColumns = [
  { title: 'Worker Name', dataIndex: 'name', key: 'name' },
  { title: 'Status', dataIndex: 'status', key: 'status', width: 120 },
  { title: 'Active Tasks', dataIndex: 'activeTasks', key: 'activeTasks', width: 120 },
  { title: 'Processed', dataIndex: 'processed', key: 'processed', width: 120 },
]

function getStatusBadge(status: string): 'success' | 'warning' | 'error' {
  switch (status) {
    case 'HEALTHY':
      return 'success'
    case 'DEGRADED':
      return 'warning'
    case 'DOWN':
      return 'error'
    default:
      return 'warning'
  }
}

async function fetchHealth() {
  loading.value = true
  try {
    health.value = await getSystemHealth()
  } catch {
    health.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchHealth()
})
</script>

<style scoped>
.system-health {
  width: 100%;
}

.toolbar {
  margin-bottom: 16px;
}

.service-card {
  height: 100%;
}

.service-status {
  font-size: 16px;
  margin-bottom: 12px;
}

.service-metric {
  color: #666;
  font-size: 13px;
  margin-bottom: 4px;
}

.service-message {
  margin-top: 8px;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}
</style>
