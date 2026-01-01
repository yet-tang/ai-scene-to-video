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

    <div class="empty-state" v-else>
      <van-empty description="视频生成失败或已过期" />
      <van-button round type="primary" @click="router.push('/create')">
        返回首页
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { showToast, showSuccessToast } from 'vant'

const router = useRouter()
const projectStore = useProjectStore()

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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}
</style>
