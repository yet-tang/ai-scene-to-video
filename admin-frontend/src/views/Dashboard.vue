<template>
  <div class="dashboard">
    <a-spin :spinning="loading">
      <a-row :gutter="16">
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="Total Projects"
              :value="stats.totalProjects"
              :value-style="{ color: '#1890ff' }"
            >
              <template #prefix><ProjectOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="Today Created"
              :value="stats.todayCreated"
              :value-style="{ color: '#52c41a' }"
            >
              <template #prefix><PlusCircleOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="Today Completed"
              :value="stats.todayCompleted"
              :value-style="{ color: '#52c41a' }"
            >
              <template #prefix><CheckCircleOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="Today Failed"
              :value="stats.todayFailed"
              :value-style="{ color: '#ff4d4f' }"
            >
              <template #prefix><CloseCircleOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="16" style="margin-top: 16px">
        <a-col :span="8">
          <a-card>
            <a-statistic
              title="Processing"
              :value="stats.processingCount"
              :value-style="{ color: '#faad14' }"
            >
              <template #prefix><SyncOutlined spin /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card>
            <a-statistic
              title="Healthy Models"
              :value="stats.healthyModelCount"
              :value-style="{ color: '#52c41a' }"
            >
              <template #prefix><ApiOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card>
            <a-statistic
              title="Unhealthy Models"
              :value="stats.unhealthyModelCount"
              :value-style="{ color: '#ff4d4f' }"
            >
              <template #prefix><WarningOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="16" style="margin-top: 24px">
        <a-col :span="24">
          <a-card title="Quick Actions">
            <a-space>
              <a-button type="primary" @click="$router.push({ name: 'ProjectList' })">
                <template #icon><ProjectOutlined /></template>
                View Projects
              </a-button>
              <a-button @click="$router.push({ name: 'ModelList' })">
                <template #icon><ApiOutlined /></template>
                Check Models
              </a-button>
              <a-button @click="$router.push({ name: 'SystemHealth' })">
                <template #icon><MonitorOutlined /></template>
                System Health
              </a-button>
            </a-space>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  ProjectOutlined,
  PlusCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ApiOutlined,
  WarningOutlined,
  MonitorOutlined,
} from '@ant-design/icons-vue'
import { getDashboardStats } from '@/api/projects'
import type { DashboardStats } from '@/types'

const loading = ref(false)
const stats = ref<DashboardStats>({
  totalProjects: 0,
  todayCreated: 0,
  todayCompleted: 0,
  todayFailed: 0,
  processingCount: 0,
  healthyModelCount: 0,
  unhealthyModelCount: 0,
})

async function fetchStats() {
  loading.value = true
  try {
    stats.value = await getDashboardStats()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}
</style>
