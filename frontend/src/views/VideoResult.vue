<template>
  <div class="container">
    <div class="video-result">
      <van-nav-bar
        title="制作完成"
        left-arrow
        @click-left="router.push('/create')"
        :border="false"
        class="transparent-nav"
      />

      <div class="result-container" v-if="projectStore.currentProject.finalVideoUrl">
        <!-- 视频播放区域 -->
        <div class="video-wrapper app-card">
          <video 
            :src="projectStore.currentProject.finalVideoUrl" 
            controls 
            autoplay
            playsinline
            class="result-video"
          ></video>
        </div>

        <div class="audio-wrapper" v-if="projectStore.currentProject.audioUrl">
          <audio :src="projectStore.currentProject.audioUrl" controls preload="metadata" class="result-audio"></audio>
        </div>

        <!-- 成功信息 -->
        <div class="success-card app-card">
          <div class="success-icon-wrapper">
            <van-icon name="success" color="#fff" size="24" />
          </div>
          <div class="title">视频制作成功</div>
          <div class="desc">
            AI 已为您完成剪辑、配音与字幕<br>
            <span class="highlight">专业房产解说风格</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <van-button 
            round 
            block 
            type="primary" 
            class="mb-16 main-btn"
            color="linear-gradient(to right, #1989fa, #39b9f5)"
            @click="downloadVideo"
          >
            <van-icon name="down" class="btn-icon" /> 保存到相册
          </van-button>
          
          <van-button 
            round 
            block 
            plain 
            type="primary" 
            class="mb-16"
            @click="shareVideo"
          >
            <van-icon name="share" class="btn-icon" /> 复制链接分享
          </van-button>

          <div class="secondary-actions">
            <span @click="router.push('/create')">再做一个</span>
          </div>
        </div>
      </div>

      <div class="loading-state" v-else-if="isInProgress">
        <div class="loading-content app-card">
          <div class="loading-header">
            <div class="loading-title">
              <van-loading size="16" type="spinner" color="#1989fa" />
              <span>正在合成视频</span>
            </div>
            <div class="loading-meta">{{ loadingPercent }}%</div>
          </div>

          <van-progress :percentage="loadingPercent" stroke-width="8" />

          <div class="loading-steps">
            <div class="step" :class="{ active: stepIndex >= 1 }">1. 生成语音</div>
            <div class="step" :class="{ active: stepIndex >= 2 }">2. 智能剪辑</div>
            <div class="step" :class="{ active: stepIndex >= 3 }">3. 合成字幕</div>
          </div>

          <div class="loading-audio" v-if="projectStore.currentProject.audioUrl">
            <div class="loading-audio-title">语音已生成</div>
            <audio :src="projectStore.currentProject.audioUrl" controls preload="metadata" class="result-audio"></audio>
          </div>
        </div>
      </div>

      <div class="empty-state" v-else>
        <van-empty image="error" description="视频生成遇到问题" />
        <div class="error-text" v-if="projectStore.currentProject.status === 'FAILED'">请检查网络或稍后重试</div>
        <div class="error-text" v-else>任务仍在处理中，请稍后返回查看</div>
        <van-button round type="primary" class="retry-btn" @click="router.push('/create')">
          返回首页
        </van-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { showToast, showSuccessToast } from 'vant'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const projectId = route.params.id as string

const isMock = computed(() => {
  const v = route.query.mock
  return v === '1' || v === 'true'
})

const mockStatus = computed(() => (route.query.mockStatus as string) || 'completed')

const isLoading = ref(true)
let pollTimer: any = null

const isInProgress = computed(() => {
  if (projectStore.currentProject.finalVideoUrl) return false
  if (isLoading.value) return true
  return projectStore.currentProject.status !== 'FAILED'
})

const stepIndex = computed(() => {
  const status = projectStore.currentProject.status
  if (status === 'AUDIO_GENERATING') return 1
  if (status === 'AUDIO_GENERATED') return 2
  if (status === 'RENDERING') return 3
  return 1
})

const loadingPercent = computed(() => {
  if (isLoading.value) return 10
  const status = projectStore.currentProject.status
  if (status === 'AUDIO_GENERATING') return 25
  if (status === 'AUDIO_GENERATED') return 45
  if (status === 'RENDERING') return 75
  if (status === 'COMPLETED') return 100
  return 10
})

onMounted(async () => {
  if (!projectId) {
    router.replace('/create')
    return
  }

  if (isMock.value) {
    const status = mockStatus.value
    if (status === 'failed') {
      projectStore.applyMockProject(projectId, 'FAILED')
    } else if (status === 'audio') {
      projectStore.applyMockProject(projectId, 'AUDIO_GENERATED')
    } else if (status === 'loading') {
      projectStore.applyMockProject(projectId, 'RENDERING')
    } else {
      projectStore.applyMockProject(projectId, 'COMPLETED')
    }
    isLoading.value = false
    return
  }
  
  await checkStatus()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

const checkStatus = async () => {
  if (isMock.value) return
  try {
    await projectStore.fetchProject(projectId)
    isLoading.value = false
    
    const status = projectStore.currentProject.status
    if (status === 'COMPLETED' || status === 'FAILED') {
      stopPolling()
    }
  } catch (e) {
    showToast('获取状态失败')
    stopPolling()
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(checkStatus, 3000)
}

const stopPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
}

const downloadVideo = () => {
  // 实际场景如果是 H5，可能需要引导用户长按保存或调用原生桥接
  // 这里模拟下载
  const a = document.createElement('a')
  a.href = projectStore.currentProject.finalVideoUrl
  a.download = `房产视频_${projectStore.currentProject.info.communityName}.mp4`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  showSuccessToast('已开始下载')
}

const shareVideo = () => {
  // 模拟复制链接
  const url = window.location.href
  navigator.clipboard.writeText(url).then(() => {
    showToast('链接已复制，快去分享吧')
  }).catch(() => {
    showToast('复制失败，请手动复制')
  })
}
</script>

<style scoped>
.video-result {
  min-height: 100vh;
  background-color: #f7f8fa;
  display: flex;
  flex-direction: column;
}


.result-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.video-wrapper {
  width: calc(100% - 32px);
  margin: 12px 16px 0;
  /* aspect-ratio: 9/16; removed to let video decide height but max-height constrained */
  max-height: 60vh;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-video {
  width: 100%;
  height: 100%;
  max-height: 60vh;
  object-fit: contain;
}

.audio-wrapper {
  padding: 12px 0 0;
  margin: 0 16px;
}

.result-audio {
  width: 100%;
}

.loading-audio {
  margin-top: 18px;
  width: 100%;
  max-width: 100%;
}

.loading-audio-title {
  font-size: 13px;
  color: #323233;
  font-weight: 600;
  margin-bottom: 10px;
}

.success-card {
  padding: 24px 16px;
  text-align: center;
  margin: 12px 16px 0;
  position: relative;
  z-index: 10;
}

.success-icon-wrapper {
  width: 48px;
  height: 48px;
  background: #07c160;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 4px 12px rgba(7, 193, 96, 0.3);
}

.success-card .title {
  font-size: 20px;
  font-weight: 700;
  color: #323233;
  margin-bottom: 8px;
}

.success-card .desc {
  font-size: 14px;
  color: #969799;
  line-height: 1.6;
}

.success-card .highlight {
  color: #1989fa;
  font-weight: 500;
}

.action-buttons {
  padding: 0 32px calc(48px + env(safe-area-inset-bottom));
  margin-top: auto;
}

.mb-16 {
  margin-bottom: 16px;
}

.main-btn {
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(25, 137, 250, 0.3);
}

.btn-icon {
  margin-right: 4px;
  font-size: 18px;
}

.secondary-actions {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #969799;
}

.secondary-actions span {
  cursor: pointer;
  padding: 8px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  flex: 1;
  padding: 12px 0;
  background: #f7f8fa;
}

.loading-content {
  margin: 12px 16px;
  padding: 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.loading-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.loading-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #323233;
}

.loading-meta {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.loading-steps {
  margin-top: 2px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step {
  font-size: 13px;
  color: #94a3b8;
}

.step.active {
  color: #1989fa;
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 24px 16px;
  background: #f7f8fa;
}

.retry-btn {
  width: 120px;
  margin-top: 24px;
}
</style>
