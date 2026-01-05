<template>
  <div class="project-detail-page">
    <van-nav-bar
      title="项目详情"
      left-text="返回"
      left-arrow
      fixed
      placeholder
      @click-left="onClickLeft"
    />

    <div v-if="loading" class="loading-container">
      <van-loading type="spinner" />
    </div>

    <div v-else-if="project" class="content">
      <!-- Status Banner -->
      <div class="status-banner" :class="statusClass">
        <h3>{{ project.status }}</h3>
        <p>项目ID: {{ project.id }}</p>
      </div>

      <!-- Basic Info -->
      <van-cell-group title="基本信息" inset>
        <van-cell title="标题" :value="project.title" />
        <van-cell title="小区" :value="project.info.communityName" />
        <van-cell title="户型" :value="`${project.info.layout.room}室${project.info.layout.hall}厅`" />
        <van-cell title="面积" :value="project.info.area ? `${project.info.area}㎡` : '-'" />
        <van-cell title="价格" :value="project.info.price ? `${project.info.price}万` : '-'" />
      </van-cell-group>

      <!-- Script Section -->
      <van-cell-group title="脚本内容" inset v-if="project.script">
        <div class="script-content">
          {{ project.script }}
        </div>
      </van-cell-group>

      <!-- Actions -->
      <div class="action-buttons">
        <van-button 
          v-if="canEditScript" 
          block 
          type="primary" 
          plain 
          @click="showEditScriptDialog"
          class="mb-2"
        >
          编辑脚本
        </van-button>

        <van-button 
          v-if="canRetry" 
          block 
          type="danger" 
          @click="handleRetry"
        >
          重试渲染
        </van-button>
        
         <van-button 
          v-if="isCompleted" 
          block 
          type="success" 
          @click="goToResult"
        >
          查看视频
        </van-button>
      </div>
    </div>

    <!-- Edit Script Dialog -->
    <van-dialog
      v-model:show="showScriptDialog"
      title="编辑脚本"
      show-cancel-button
      @confirm="confirmEditScript"
    >
      <van-field
        v-model="editingScript"
        rows="5"
        autosize
        type="textarea"
        placeholder="请输入脚本内容"
      />
    </van-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { projectApi } from '../api/project'
import { showToast, showDialog } from 'vant'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()

const loading = ref(true)
const showScriptDialog = ref(false)
const editingScript = ref('')

const projectId = route.params.id as string
const project = computed(() => store.currentProject)

const statusClass = computed(() => {
  const status = project.value.status
  if (status === 'COMPLETED') return 'bg-success'
  if (['FAILED'].includes(status)) return 'bg-danger'
  return 'bg-primary'
})

const canEditScript = computed(() => {
  return ['SCRIPT_GENERATED', 'FAILED'].includes(project.value.status)
})

const canRetry = computed(() => {
  return ['FAILED'].includes(project.value.status)
})

const isCompleted = computed(() => {
    return project.value.status === 'COMPLETED'
})

onMounted(async () => {
  if (!projectId) {
    showToast('无效的项目ID')
    return
  }
  await loadData()
})

const loadData = async () => {
  loading.value = true
  try {
    await store.fetchProject(projectId)
  } catch (error) {
    showToast('加载项目详情失败')
  } finally {
    loading.value = false
  }
}

const onClickLeft = () => {
  router.push('/projects')
}

const showEditScriptDialog = () => {
  editingScript.value = project.value.script
  showScriptDialog.value = true
}

const confirmEditScript = async () => {
  try {
    await projectApi.updateScript(projectId, editingScript.value)
    showToast('脚本已更新')
    // Refresh data
    await loadData()
  } catch (error) {
    console.error(error)
    showToast('更新脚本失败')
  }
}

const handleRetry = () => {
  showDialog({
    title: '确认重试',
    message: '确定要重新开始渲染视频吗？',
    showCancelButton: true,
  }).then(async (action) => {
    if (action === 'confirm') {
      try {
        await projectApi.renderVideo(projectId)
        showToast('已提交渲染任务')
        await loadData()
      } catch (error) {
        showToast('提交失败')
      }
    }
  })
}

const goToResult = () => {
    router.push({ name: 'result', params: { id: projectId } })
}
</script>

<style scoped>
.project-detail-page {
  background-color: #f7f8fa;
  min-height: 100vh;
  padding-bottom: 20px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}

.status-banner {
  padding: 20px;
  color: white;
  text-align: center;
  margin-bottom: 16px;
}

.bg-success {
  background-color: #07c160;
}

.bg-danger {
  background-color: #ee0a24;
}

.bg-primary {
  background-color: #1989fa;
}

.script-content {
  padding: 16px;
  font-size: 14px;
  line-height: 1.5;
  color: #323233;
  white-space: pre-wrap;
}

.action-buttons {
  padding: 16px;
  margin-top: 20px;
}

.mb-2 {
  margin-bottom: 12px;
}
</style>
