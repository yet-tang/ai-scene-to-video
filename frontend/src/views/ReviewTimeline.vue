<template>
  <div class="review-timeline">
    <van-nav-bar
      title="智能分段确认"
      left-text="返回"
      left-arrow
      @click-left="router.back()"
    />

    <!-- 头部信息 -->
    <div class="header-info">
      <div class="info-item">
        <span class="label">总时长:</span>
        <span class="value">{{ totalDuration }}</span>
      </div>
      <div class="info-item">
        <span class="label">风格:</span>
        <span class="value">标准·专业顾问</span>
      </div>
    </div>

    <!-- 拖拽列表 -->
    <div class="timeline-list">
      <div class="list-title">请确认 AI 识别的顺序与内容:</div>
      
      <draggable 
        v-model="assets" 
        item-key="id"
        handle=".drag-handle"
        @end="onDragEnd"
      >
        <template #item="{ element, index }">
          <div class="timeline-item">
            <div class="item-header">
              <span class="index">{{ index + 1 }}</span>
              <span class="time-range">{{ formatTimeRange(index) }}</span>
              <van-icon name="cross" class="delete-btn" @click="removeAsset(index)" />
            </div>
            
            <div class="item-content">
              <!-- 视频预览 (使用 video 标签展示第一帧，或者只是个图标) -->
              <div class="thumbnail">
                <video :src="element.url" muted preload="metadata" class="video-preview"></video>
                <div class="play-icon"><van-icon name="play-circle-o" /></div>
              </div>
              
              <div class="details">
                <div class="scene-row" @click="openScenePicker(index)">
                  <span class="label">识别场景:</span>
                  <span class="scene-tag">{{ element.userLabel }} <van-icon name="edit" /></span>
                </div>
                <div class="desc-row">
                  <span class="label">时长:</span>
                  <span>{{ Math.round(element.duration) }}s</span>
                </div>
              </div>

              <div class="drag-handle">
                <van-icon name="wap-nav" size="20" />
              </div>
            </div>
          </div>
        </template>
      </draggable>

      <div class="add-btn" @click="showToast('添加功能开发中')">
        <van-icon name="plus" /> 添加遗漏片段
      </div>
    </div>

    <!-- 脚本预览 -->
    <div class="script-preview">
      <div class="section-title-row">
        <div class="section-title">预览解说词全文:</div>
        <van-button size="small" type="primary" plain @click="onGenerateScript" :loading="isScriptGenerating">
          生成 AI 解说词
        </van-button>
      </div>
      <van-field
        v-model="scriptContent"
        type="textarea"
        rows="6"
        autosize
        border
        class="script-input"
        placeholder="点击上方按钮生成，或直接输入..."
      />
    </div>

    <!-- 底部按钮 -->
    <div class="bottom-action">
      <van-button round block type="primary" @click="onGenerateVideo" :loading="isRendering">
        生成最终视频
      </van-button>
    </div>

    <!-- 场景修改弹窗 -->
    <van-popup v-model:show="showPicker" position="bottom" round>
      <van-picker
        :columns="sceneOptions"
        @confirm="onSceneConfirm"
        @cancel="showPicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, type Asset } from '../stores/project'
import { projectApi } from '../api/project'
import draggable from 'vuedraggable'
import { showToast } from 'vant'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const projectId = route.params.id as string

const assets = ref<Asset[]>([])
const scriptContent = ref('')
const isScriptGenerating = ref(false)
const isRendering = ref(false)
let pollTimer: any = null

// 场景选择
const showPicker = ref(false)
const editingIndex = ref(-1)
const sceneOptions = [
  { text: '小区大门', value: '小区大门' },
  { text: '小区环境', value: '小区环境' },
  { text: '客厅', value: '客厅' },
  { text: '餐厅', value: '餐厅' },
  { text: '主卧', value: '主卧' },
  { text: '次卧', value: '次卧' },
  { text: '厨房', value: '厨房' },
  { text: '卫生间', value: '卫生间' },
  { text: '阳台', value: '阳台' },
  { text: '书房', value: '书房' },
]

onMounted(async () => {
  if (!projectId) {
    showToast('参数错误')
    router.replace('/create')
    return
  }

  await loadData()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

const loadData = async () => {
  try {
    await projectStore.fetchProject(projectId)
    await projectStore.fetchTimeline(projectId)
    
    assets.value = [...projectStore.currentProject.assets]
    if (projectStore.currentProject.script) {
        scriptContent.value = projectStore.currentProject.script
    }
  } catch (e) {
    showToast('加载失败')
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    // Poll until all assets have scene labels (analysis done)
    await projectStore.fetchTimeline(projectId)
    const newAssets = projectStore.currentProject.assets
    
    // Only update if we are not dragging? 
    // Updating list while dragging causes issues.
    // For MVP, we simply update if length changed or status changed.
    // Better: only update missing labels.
    let hasUpdate = false
    newAssets.forEach((newAsset, idx) => {
        const current = assets.value.find(a => a.id === newAsset.id)
        if (current) {
            if (!current.sceneLabel && newAsset.sceneLabel) {
                current.sceneLabel = newAsset.sceneLabel
                current.userLabel = newAsset.userLabel
                current.sceneScore = newAsset.sceneScore
                hasUpdate = true
            }
        }
    })
    
    if (hasUpdate) {
        showToast('AI 分析已更新')
    }
    
    // Also check script status if we are waiting for it
    if (isScriptGenerating.value) {
        await projectStore.fetchProject(projectId)
        if (projectStore.currentProject.status === 'SCRIPT_GENERATED') {
            scriptContent.value = projectStore.currentProject.script
            isScriptGenerating.value = false
            showToast('脚本生成完成')
        }
    }

  }, 3000)
}

const stopPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
}

const totalDuration = computed(() => {
  const totalSeconds = assets.value.reduce((sum, item) => sum + item.duration, 0)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.floor(totalSeconds % 60)
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
})

const formatTimeRange = (index: number) => {
  if (!assets.value[index]) return '00:00 - 00:00'
  let startTime = 0
  for (let i = 0; i < index; i++) {
    const item = assets.value[i]
    if (item) startTime += item.duration
  }
  const endTime = startTime + assets.value[index].duration
  
  const format = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
  }
  
  return `${format(startTime)} - ${format(endTime)}`
}

const onDragEnd = async () => {
  // Update Sort Order
  // We need to update ALL assets sort order in backend?
  // Or just the moved one?
  // Backend relies on sort_order. We should update all to be safe (0, 1, 2...)
  const updates = assets.value.map((asset, index) => {
    return projectApi.updateAsset(projectId, asset.id, { sortOrder: index })
  })
  
  try {
    await Promise.all(updates)
    // Sync store
    projectStore.currentProject.assets = assets.value
  } catch (e) {
    showToast('排序保存失败')
  }
}

const removeAsset = (index: number) => {
  // Backend doesn't support delete asset yet?
  // We can just hide it locally or add delete API.
  // For MVP, just remove from local list (won't be included in script if we regenerate?)
  // Actually generateScript reads from DB. So we MUST delete from DB or mark ignored.
  // Missing backend API for delete.
  showToast('暂不支持删除片段')
}

const openScenePicker = (index: number) => {
  editingIndex.value = index
  showPicker.value = true
}

const onSceneConfirm = async ({ selectedOptions }: any) => {
  const asset = assets.value[editingIndex.value]
  if (editingIndex.value > -1 && selectedOptions[0] && asset) {
    const newVal = selectedOptions[0].text
    asset.userLabel = newVal
    
    try {
        await projectApi.updateAsset(projectId, asset.id, { userLabel: newVal })
    } catch (e) {
        showToast('修改失败')
    }
  }
  showPicker.value = false
}

const onGenerateScript = async () => {
    isScriptGenerating.value = true
    try {
        await projectApi.generateScript(projectId)
        showToast('正在生成解说词...')
    } catch (e) {
        isScriptGenerating.value = false
        showToast('请求失败')
    }
}

const onGenerateVideo = async () => {
  if (!scriptContent.value) {
    showToast('请先生成或填写解说词')
    return
  }
  
  isRendering.value = true
  try {
      // 1. Generate Audio
      await projectApi.generateAudio(projectId, scriptContent.value)
      // 2. Render Video
      await projectApi.renderVideo(projectId)
      
      router.push(`/result/${projectId}`)
  } catch (e) {
      showToast('提交任务失败')
      isRendering.value = false
  }
}
</script>

<style scoped>
.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.review-timeline {
  padding-bottom: 80px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.header-info {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  margin-bottom: 12px;
  font-size: 14px;
}

.header-info .label {
  color: #646566;
  margin-right: 4px;
}

.header-info .value {
  font-weight: bold;
  color: #323233;
}

.timeline-list {
  padding: 0 16px;
}

.list-title {
  font-size: 14px;
  color: #969799;
  margin-bottom: 8px;
}

.timeline-item {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: #969799;
}

.item-header .index {
  background: #ebedf0;
  padding: 2px 6px;
  border-radius: 4px;
  color: #323233;
  margin-right: 8px;
}

.item-content {
  display: flex;
  align-items: center;
}

.thumbnail {
  width: 80px;
  height: 80px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  background: #000;
  margin-right: 12px;
}

.video-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.play-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: rgba(255,255,255,0.8);
  font-size: 24px;
}

.details {
  flex: 1;
}

.scene-row {
  margin-bottom: 4px;
  display: flex;
  align-items: center;
}

.scene-tag {
  color: #1989fa;
  font-weight: 500;
  margin-left: 4px;
  display: flex;
  align-items: center;
}

.desc-row {
  font-size: 12px;
  color: #646566;
}

.drag-handle {
  padding: 8px;
  color: #c8c9cc;
  cursor: grab;
}

.add-btn {
  text-align: center;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
  border: 1px dashed #dcdee0;
  color: #1989fa;
  font-size: 14px;
  margin-top: 12px;
}

.script-preview {
  margin-top: 24px;
  padding: 0 16px;
}

.section-title {
  font-size: 14px;
  color: #323233;
  margin-bottom: 8px;
  font-weight: 500;
}

.script-input {
  border-radius: 8px;
  background: #fff;
}

.bottom-action {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: #fff;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
  z-index: 100;
}
</style>
