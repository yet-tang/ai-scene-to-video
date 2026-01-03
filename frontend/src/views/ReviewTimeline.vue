<template>
  <div class="review-timeline">
    <van-nav-bar
      title="智能分段确认"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <!-- 概览信息 -->
    <div class="overview-card">
      <div class="stat-item">
        <div class="value">{{ assets.length }}</div>
        <div class="label">片段数</div>
      </div>
      <div class="stat-item">
        <div class="value">{{ totalDuration }}</div>
        <div class="label">总时长</div>
      </div>
      <div class="stat-item">
        <div class="value">专业顾问</div>
        <div class="label">解说风格</div>
      </div>
    </div>

    <!-- 拖拽列表 -->
    <div class="timeline-list">
      <div class="section-header">
        <span class="title">视频片段排序</span>
        <span class="sub">长按拖拽调整顺序</span>
      </div>
      
      <draggable 
        v-model="assets" 
        item-key="id"
        handle=".drag-handle"
        @end="onDragEnd"
        animation="200"
        ghost-class="ghost-item"
      >
        <template #item="{ element, index }">
          <div class="timeline-item">
            <div class="thumbnail-wrapper">
              <div class="index-badge">{{ index + 1 }}</div>
              <video :src="element.url" muted class="video-preview"></video>
              <div class="duration-badge">{{ Math.round(element.duration) }}s</div>
            </div>
            
            <div class="item-content">
              <div class="content-top">
                <div class="scene-info" @click="openScenePicker(index)">
                  <span class="scene-label">{{ element.userLabel || '未知场景' }}</span>
                  <van-icon name="edit" class="edit-icon" />
                </div>
                <div class="delete-btn" @click.stop="removeAsset(index)">
                  <van-icon name="delete-o" size="18" color="#c8c9cc" />
                </div>
              </div>
              
              <div class="content-bottom">
                <div class="ai-tag" v-if="element.sceneLabel">
                  AI: {{ element.sceneLabel }}
                </div>
                <div class="time-range">
                  {{ formatTimeRange(index) }}
                </div>
              </div>
            </div>

            <div class="drag-handle">
              <van-icon name="bars" size="20" color="#c8c9cc" />
            </div>
          </div>
        </template>
      </draggable>

      <div class="add-clip-btn" @click="showToast('添加功能开发中')">
        <van-icon name="plus" /> 添加遗漏片段
      </div>
    </div>

    <!-- 脚本预览 -->
    <div class="script-section">
      <div class="section-header">
        <span class="title">AI 解说文案</span>
        <van-button 
          size="mini" 
          type="primary" 
          plain 
          hairline
          @click="onGenerateScript" 
          :loading="isScriptGenerating"
        >
          重新生成
        </van-button>
      </div>
      
      <div class="script-card">
        <van-field
          v-model="scriptContent"
          type="textarea"
          rows="6"
          autosize
          :placeholder="isScriptGenerating ? '正在思考文案...' : '点击上方按钮生成，或直接输入...'"
          class="script-input"
        />
      </div>
    </div>

    <!-- 底部按钮 -->
    <div class="bottom-action-bar">
      <div class="action-summary">
        预计生成时长: {{ Math.ceil(assets.reduce((s, i) => s + i.duration, 0) / 60 * 2) }} 分钟
      </div>
      <van-button 
        round 
        block 
        type="primary" 
        @click="onGenerateVideo" 
        :loading="isRendering"
        color="linear-gradient(to right, #1989fa, #39b9f5)"
        loading-text="正在合成..."
      >
        生成最终视频
      </van-button>
    </div>

    <!-- 场景修改弹窗 -->
    <van-popup v-model:show="showPicker" position="bottom" round>
      <van-picker
        title="修正场景标签"
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
const analysisDone = ref(false)

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
  { text: '走廊', value: '走廊' },
  { text: '其他', value: '其他' },
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
    if (newAssets.length !== assets.value.length) {
      assets.value = [...newAssets]
    }
    
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

    if (!analysisDone.value) {
      const done = assets.value.length > 0 && assets.value.every(a => !!a.sceneLabel)
      if (done) {
        analysisDone.value = true
        stopPolling()
        showToast('AI 分析完成')
      }
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
.review-timeline {
  padding-bottom: 120px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.overview-card {
  margin: 12px 16px;
  background: #fff;
  border-radius: 8px;
  padding: 16px 8px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-item .value {
  font-size: 18px;
  font-weight: 600;
  color: #323233;
}

.stat-item .label {
  font-size: 12px;
  color: #969799;
  margin-top: 4px;
}

.timeline-list {
  padding: 0 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header .title {
  font-size: 15px;
  font-weight: 600;
  color: #323233;
}

.section-header .sub {
  font-size: 12px;
  color: #969799;
}

.timeline-item {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  display: flex;
  align-items: stretch;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  position: relative;
  transition: all 0.2s;
}

.ghost-item {
  opacity: 0.5;
  background: #e8f3ff;
}

.index-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 18px;
  height: 18px;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(2px);
  color: #fff;
  border-radius: 4px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.thumbnail-wrapper {
  width: 72px;
  height: 96px; /* 3:4 */
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  background: #000;
  margin-right: 12px;
  flex-shrink: 0;
}

.video-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.duration-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 10px;
  padding: 2px 4px;
  border-top-left-radius: 4px;
}

.item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 4px 0;
}

.content-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.content-bottom {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.scene-info {
  display: flex;
  align-items: center;
}

.scene-label {
  font-size: 15px;
  font-weight: 600;
  color: #323233;
}

.edit-icon {
  font-size: 14px;
  color: #969799;
  margin-left: 4px;
  opacity: 0.5;
}

.ai-tag {
  font-size: 10px;
  color: #1989fa;
  background: #e8f3ff;
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
}

.time-range {
  font-size: 12px;
  color: #969799;
  font-family: monospace;
}

.drag-handle {
  display: flex;
  align-items: center;
  padding: 0 4px 0 12px;
  cursor: grab;
}

.delete-btn {
  padding: 4px;
  margin-top: -4px;
  margin-right: -4px;
}

.add-clip-btn {
  text-align: center;
  padding: 14px;
  background: #fff;
  border-radius: 8px;
  border: 1px dashed #dcdee0;
  color: #1989fa;
  font-size: 14px;
  margin-top: 8px;
  font-weight: 500;
}

.script-section {
  margin-top: 24px;
  padding: 0 16px;
}

.script-card {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

.script-input :deep(.van-field__control) {
  font-size: 14px;
  line-height: 1.6;
  color: #323233;
}

.bottom-action-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
  background: #fff;
  box-shadow: 0 -4px 12px rgba(0,0,0,0.05);
  z-index: 100;
}

.action-summary {
  text-align: center;
  font-size: 12px;
  color: #969799;
  margin-bottom: 8px;
}
</style>
