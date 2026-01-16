<template>
  <div class="project-detail">
    <a-spin :spinning="loading">
      <div v-if="project" class="detail-content">
        <a-page-header
          :title="project.title || 'Untitled Project'"
          :sub-title="`ID: ${project.id}`"
          @back="$router.push({ name: 'ProjectList' })"
        >
          <template #extra>
            <a-tag :color="getStatusColor(project.status)" style="font-size: 14px; padding: 4px 12px">
              {{ project.status }}
            </a-tag>
          </template>
        </a-page-header>

        <a-divider />

        <!-- Processing Timeline -->
        <a-card title="Processing Timeline" style="margin-bottom: 24px">
          <a-steps :current="currentStep" :status="stepsStatus" size="small">
            <a-step
              v-for="node in project.timeline.nodes"
              :key="node.step"
              :title="node.step"
              :description="getStepDescription(node)"
            >
              <template #icon>
                <CheckCircleOutlined v-if="node.status === 'SUCCESS'" style="color: #52c41a" />
                <CloseCircleOutlined v-else-if="node.status === 'FAILED'" style="color: #ff4d4f" />
                <LoadingOutlined v-else-if="node.status === 'RUNNING'" />
                <ClockCircleOutlined v-else style="color: #d9d9d9" />
              </template>
            </a-step>
          </a-steps>
        </a-card>

        <!-- Basic Info -->
        <a-row :gutter="24">
          <a-col :span="12">
            <a-card title="Basic Information" style="margin-bottom: 24px">
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item label="User ID">{{ project.userId }}</a-descriptions-item>
                <a-descriptions-item label="Created At">{{ formatDate(project.createdAt) }}</a-descriptions-item>
                <a-descriptions-item label="Asset Count">{{ project.assets.length }}</a-descriptions-item>
                <a-descriptions-item label="Audio URL">
                  <a v-if="project.audioUrl" :href="project.audioUrl" target="_blank">View Audio</a>
                  <span v-else>-</span>
                </a-descriptions-item>
                <a-descriptions-item label="BGM URL">
                  <a v-if="project.bgmUrl" :href="project.bgmUrl" target="_blank">View BGM</a>
                  <span v-else>-</span>
                </a-descriptions-item>
                <a-descriptions-item label="Final Video">
                  <a v-if="project.finalVideoUrl" :href="project.finalVideoUrl" target="_blank">View Video</a>
                  <span v-else>-</span>
                </a-descriptions-item>
              </a-descriptions>
            </a-card>
          </a-col>

          <a-col :span="12">
            <a-card title="Error Information" style="margin-bottom: 24px" v-if="project.status === 'FAILED'">
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item label="Error Step">
                  <a-tag color="red">{{ project.errorStep }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="Error At">{{ formatDate(project.errorAt!) }}</a-descriptions-item>
                <a-descriptions-item label="Task ID">{{ project.errorTaskId || '-' }}</a-descriptions-item>
                <a-descriptions-item label="Request ID">{{ project.errorRequestId || '-' }}</a-descriptions-item>
              </a-descriptions>
              <div v-if="project.errorLog" style="margin-top: 16px">
                <strong>Error Log:</strong>
                <pre class="error-log">{{ project.errorLog }}</pre>
              </div>
            </a-card>
            <a-card v-else title="Status" style="margin-bottom: 24px">
              <a-result
                :status="project.status === 'COMPLETED' ? 'success' : 'info'"
                :title="project.status"
                :sub-title="getStatusDescription(project.status)"
              />
            </a-card>
          </a-col>
        </a-row>

        <!-- House Info -->
        <a-card v-if="project.houseInfo" title="House Information" style="margin-bottom: 24px">
          <pre class="json-viewer">{{ JSON.stringify(project.houseInfo, null, 2) }}</pre>
        </a-card>

        <!-- Script Content -->
        <a-card v-if="project.scriptContent" title="Script Content" style="margin-bottom: 24px">
          <pre class="json-viewer">{{ JSON.stringify(project.scriptContent, null, 2) }}</pre>
        </a-card>

        <!-- Assets -->
        <a-card title="Assets" style="margin-bottom: 24px">
          <a-table
            :columns="assetColumns"
            :data-source="project.assets"
            :pagination="false"
            row-key="id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'ossUrl'">
                <a :href="record.ossUrl" target="_blank">View</a>
              </template>
              <template v-if="column.key === 'duration'">
                {{ record.duration ? `${record.duration}s` : '-' }}
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons-vue'
import { getProjectDetail } from '@/api/projects'
import type { ProjectDetail, ProjectStatus, TimelineNode } from '@/types'

const props = defineProps<{
  id: string
}>()

const loading = ref(false)
const project = ref<ProjectDetail | null>(null)

const assetColumns = [
  { title: 'Sort', dataIndex: 'sortOrder', key: 'sortOrder', width: 60 },
  { title: 'Scene Label', dataIndex: 'sceneLabel', key: 'sceneLabel' },
  { title: 'Duration', dataIndex: 'duration', key: 'duration', width: 100 },
  { title: 'URL', dataIndex: 'ossUrl', key: 'ossUrl', width: 80 },
]

const currentStep = computed(() => {
  if (!project.value) return 0
  const nodes = project.value.timeline.nodes
  for (let i = nodes.length - 1; i >= 0; i--) {
    const node = nodes[i]
    if (node && (node.status === 'SUCCESS' || node.status === 'FAILED')) {
      return i
    }
    if (node?.status === 'RUNNING') {
      return i
    }
  }
  return 0
})

const stepsStatus = computed(() => {
  if (!project.value) return 'process'
  if (project.value.status === 'FAILED') return 'error'
  if (project.value.status === 'COMPLETED') return 'finish'
  return 'process'
})

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

function getStatusDescription(status: ProjectStatus): string {
  const descMap: Record<ProjectStatus, string> = {
    DRAFT: 'Project created, waiting for upload',
    UPLOADING: 'Uploading assets...',
    ANALYZING: 'Analyzing video content...',
    REVIEW: 'Ready for review',
    SCRIPT_GENERATING: 'Generating script...',
    SCRIPT_GENERATED: 'Script generated',
    AUDIO_GENERATING: 'Generating audio...',
    AUDIO_GENERATED: 'Audio generated',
    RENDERING: 'Rendering final video...',
    COMPLETED: 'Video rendering completed',
    FAILED: 'Processing failed',
  }
  return descMap[status] || status
}

function getStepDescription(node: TimelineNode): string {
  if (node.status === 'PENDING') return 'Waiting'
  if (node.status === 'RUNNING') return 'In progress...'
  if (node.status === 'SUCCESS' && node.duration) {
    return `Completed (${node.duration}ms)`
  }
  if (node.status === 'FAILED') {
    return node.errorMessage || 'Failed'
  }
  return ''
}

function formatDate(date: string): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

async function fetchProject() {
  loading.value = true
  try {
    project.value = await getProjectDetail(props.id)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchProject()
})
</script>

<style scoped>
.project-detail {
  width: 100%;
}

.detail-content {
  max-width: 1200px;
}

.error-log {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow: auto;
}

.json-viewer {
  background: #f5f5f5;
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow: auto;
}
</style>
