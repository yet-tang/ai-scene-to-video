<template>
  <div class="model-list">
    <div class="toolbar">
      <a-button type="primary" @click="refreshAll" :loading="refreshing">
        <template #icon><ReloadOutlined /></template>
        Refresh All
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-row :gutter="16">
        <a-col :span="8" v-for="model in models" :key="model.id">
          <a-card class="model-card" :class="{ 'model-unhealthy': !isHealthy(model) }">
            <template #title>
              <div class="model-title">
                <span>{{ model.agentType }}</span>
                <a-tag :color="isHealthy(model) ? 'success' : 'error'">
                  {{ isHealthy(model) ? 'Healthy' : 'Unhealthy' }}
                </a-tag>
              </div>
            </template>
            <template #extra>
              <a-button
                type="link"
                size="small"
                :loading="testingIds.includes(model.id)"
                @click="testModel(model.id)"
                :disabled="!userStore.isAdmin"
              >
                Test
              </a-button>
            </template>

            <a-descriptions :column="1" size="small">
              <a-descriptions-item label="Provider">
                <a-tag>{{ model.provider }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Model">{{ model.modelName }}</a-descriptions-item>
              <a-descriptions-item label="API Key">
                <a-tag :color="model.apiKeyConfigured ? 'success' : 'error'">
                  {{ model.apiKeyConfigured ? 'Configured' : 'Missing' }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Last Test">
                {{ model.lastTestAt ? formatDate(model.lastTestAt) : 'Never' }}
              </a-descriptions-item>
              <a-descriptions-item label="Status">
                <a-tag v-if="model.lastTestStatus" :color="model.lastTestStatus === 'SUCCESS' ? 'success' : 'error'">
                  {{ model.lastTestStatus }}
                </a-tag>
                <span v-else>-</span>
              </a-descriptions-item>
              <a-descriptions-item label="Latency">
                {{ model.lastTestLatencyMs ? `${model.lastTestLatencyMs}ms` : '-' }}
              </a-descriptions-item>
            </a-descriptions>

            <div v-if="model.lastTestError" class="error-message">
              <WarningOutlined /> {{ model.lastTestError }}
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, WarningOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { getModels, testModel as testModelApi } from '@/api/models'
import { useUserStore } from '@/stores/user'
import type { ModelStatus } from '@/types'

const userStore = useUserStore()
const loading = ref(false)
const refreshing = ref(false)
const models = ref<ModelStatus[]>([])
const testingIds = ref<string[]>([])

function isHealthy(model: ModelStatus): boolean {
  return model.apiKeyConfigured && model.lastTestStatus === 'SUCCESS'
}

function formatDate(date: string): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

async function fetchModels() {
  loading.value = true
  try {
    models.value = await getModels()
  } finally {
    loading.value = false
  }
}

async function testModel(id: string) {
  testingIds.value.push(id)
  try {
    const result = await testModelApi(id)
    // Update model in list
    const index = models.value.findIndex((m) => m.id === id)
    if (index !== -1) {
      models.value[index] = result
    }
    if (result.lastTestStatus === 'SUCCESS') {
      message.success('Model test passed')
    } else {
      message.error(`Model test failed: ${result.lastTestError}`)
    }
  } catch {
    message.error('Failed to test model')
  } finally {
    testingIds.value = testingIds.value.filter((i) => i !== id)
  }
}

async function refreshAll() {
  refreshing.value = true
  try {
    // Test all models sequentially
    for (const model of models.value) {
      if (userStore.isAdmin) {
        await testModel(model.id)
      }
    }
    message.success('All models refreshed')
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  fetchModels()
})
</script>

<style scoped>
.model-list {
  width: 100%;
}

.toolbar {
  margin-bottom: 16px;
}

.model-card {
  margin-bottom: 16px;
}

.model-card.model-unhealthy {
  border-color: #ff4d4f;
}

.model-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-message {
  margin-top: 12px;
  padding: 8px;
  background: #fff2f0;
  border-radius: 4px;
  color: #ff4d4f;
  font-size: 12px;
}
</style>
