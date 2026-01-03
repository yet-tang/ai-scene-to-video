<template>
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
      <div class="video-wrapper">
        <video 
          :src="projectStore.currentProject.finalVideoUrl" 
          controls 
          autoplay
          playsinline
          class="result-video"
        ></video>
      </div>

      <!-- 成功信息 -->
      <div class="success-card">
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

    <div class="loading-state" v-else-if="isLoading || projectStore.currentProject.status === 'RENDERING' || projectStore.currentProject.status === 'AUDIO_GENERATED'">
      <div class="loading-content">
        <van-loading size="48px" type="spinner" color="#1989fa" vertical>
          <div class="loading-text">正在合成视频...</div>
        </van-loading>
        <div class="loading-steps">
          <div class="step active">1. 生成语音</div>
          <div class="step active">2. 智能剪辑</div>
          <div class="step">3. 合成字幕</div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <van-empty image="error" description="视频生成遇到问题" />
      <div class="error-text" v-if="projectStore.currentProject.status === 'FAILED'">请检查网络或稍后重试</div>
      <van-button round type="primary" class="retry-btn" @click="router.push('/create')">
        返回首页
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { showToast, showSuccessToast } from 'vant'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const projectId = route.params.id as string

const isLoading = ref(true)
let pollTimer: any = null

onMounted(async () => {
  if (!projectId) {
    router.replace('/create')
    return
  }
  
  await checkStatus()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

const checkStatus = async () => {
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
  background-color: #fff;
  display: flex;
  flex-direction: column;
}

.transparent-nav {
  background: transparent;
}

.result-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.video-wrapper {
  width: 100%;
  /* aspect-ratio: 9/16; removed to let video decide height but max-height constrained */
  max-height: 60vh;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.result-video {
  width: 100%;
  height: 100%;
  max-height: 60vh;
  object-fit: contain;
}

.success-card {
  padding: 24px 16px;
  text-align: center;
  background: #fff;
  border-top-left-radius: 20px;
  border-top-right-radius: 20px;
  margin-top: -20px;
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
  padding: 0 32px 48px;
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
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f7f8fa;
}

.loading-content {
  background: #fff;
  padding: 40px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  width: 80%;
}

.loading-text {
  margin-top: 16px;
  font-size: 16px;
  color: #323233;
  font-weight: 500;
}

.loading-steps {
  margin-top: 24px;
  text-align: left;
  padding-left: 20px;
}

.step {
  font-size: 13px;
  color: #c8c9cc;
  margin-bottom: 8px;
  transition: all 0.3s;
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
  height: 100vh;
  background: #fff;
}

.retry-btn {
  width: 120px;
  margin-top: 24px;
}
</style>
