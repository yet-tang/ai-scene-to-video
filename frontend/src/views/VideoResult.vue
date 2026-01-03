<template>
  <div class="video-result">
    <van-nav-bar
      title="制作完成"
      left-arrow
      @click-left="router.push('/create')"
    />

    <div class="result-container" v-if="projectStore.currentProject.finalVideoUrl">
      <div class="video-wrapper">
        <video 
          :src="projectStore.currentProject.finalVideoUrl" 
          controls 
          autoplay
          playsinline
          class="result-video"
        ></video>
      </div>

      <div class="success-tips">
        <van-icon name="checked" color="#07c160" size="48" />
        <div class="title">视频生成成功!</div>
        <div class="desc">已自动合成解说词与字幕</div>
      </div>

      <div class="action-buttons">
        <van-button 
          round 
          block 
          type="primary" 
          class="mb-16"
          @click="downloadVideo"
        >
          保存到相册
        </van-button>
        
        <van-button 
          round 
          block 
          plain 
          type="primary" 
          class="mb-16"
          @click="shareVideo"
        >
          复制链接分享
        </van-button>

        <van-button 
          round 
          block 
          plain 
          @click="router.push('/create')"
        >
          再做一个
        </van-button>
      </div>
    </div>

    <div class="loading-state" v-else-if="isLoading || projectStore.currentProject.status === 'RENDERING' || projectStore.currentProject.status === 'AUDIO_GENERATED'">
      <van-loading size="48px" vertical>视频合成中...</van-loading>
      <div class="loading-desc">预计耗时 1-2 分钟，请稍候</div>
    </div>

    <div class="empty-state" v-else>
      <van-empty description="视频生成失败或已过期" />
      <div class="error-text" v-if="projectStore.currentProject.status === 'FAILED'">处理失败，请重试</div>
      <van-button round type="primary" @click="router.push('/create')">
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

.result-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.video-wrapper {
  width: 100%;
  aspect-ratio: 9/16;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.success-tips {
  padding: 32px 16px;
  text-align: center;
}

.success-tips .title {
  font-size: 20px;
  font-weight: bold;
  margin-top: 16px;
  color: #323233;
}

.success-tips .desc {
  font-size: 14px;
  color: #969799;
  margin-top: 8px;
}

.action-buttons {
  padding: 16px 32px;
  margin-top: auto;
  padding-bottom: 48px;
}

.mb-16 {
  margin-bottom: 16px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}

.loading-desc {
  margin-top: 16px;
  color: #969799;
  font-size: 14px;
}

.error-text {
  color: #ee0a24;
  margin: 10px 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}
</style>
