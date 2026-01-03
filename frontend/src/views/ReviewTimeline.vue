<template>
  <div class="review-timeline">
    <van-nav-bar
      title="智能分段确认"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

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
            <div class="thumbnail-wrapper" :class="{ portrait: isPortrait(element) }">
              <div class="index-badge">{{ index + 1 }}</div>
              <video 
                :src="element.url" 
                controls 
                class="video-preview"
                preload="metadata"
                playsinline
                @loadedmetadata="onVideoLoaded($event, element)"
              ></video>
              <div class="duration-badge">{{ Math.round(element.duration) }}s</div>
            </div>
            
            <div class="item-content">
              <div class="content-top">
                <div class="scene-info" @click="openScenePicker(index)">
                  <span class="scene-label">{{ element.userLabel || '未知场景' }}</span>
                  <van-icon name="edit" class="edit-icon" />
                </div>
                
                <div class="actions">
                    <div class="delete-btn" @click.stop="removeAsset(index)">
                        <van-icon name="delete-o" size="18" color="#c8c9cc" />
                    </div>
                    <div class="drag-handle">
                        <van-icon name="bars" size="20" color="#c8c9cc" />
                    </div>
                </div>
              </div>
              
              <div class="content-middle">
                <div class="ai-tag" v-if="element.sceneLabel">
                  AI: {{ element.sceneLabel }}
                </div>
                <div class="time-range">
                  {{ formatTimeRange(index) }}
                </div>
              </div>

              <div class="script-box">
                <van-field
                    v-model="element.script"
                    rows="2"
                    autosize
                    type="textarea"
                    placeholder="输入该片段的解说词..."
                    class="clip-script-input"
                />
              </div>
            </div>
          </div>
        </template>
      </draggable>

      <div class="add-clip-btn" @click="showToast('添加功能开发中')">
        <van-icon name="plus" /> 添加遗漏片段
      </div>
    </div>

    <div class="bottom-action-bar">
      <div class="action-summary">
        预计生成时长: {{ Math.ceil(assets.reduce((s, i) => s + i.duration, 0) / 60 * 2) }} 分钟
      </div>
      
      <div class="button-group">
          <van-button 
            plain
            type="primary" 
            @click="onGenerateScript" 
            :loading="isScriptGenerating"
            class="action-btn"
          >
            AI 生成解说
          </van-button>
          
          <van-button 
            type="primary" 
            @click="onGenerateVideo" 
            :loading="isRendering"
            color="linear-gradient(to right, #1989fa, #39b9f5)"
            loading-text="正在合成..."
            class="action-btn main-btn"
          >
            生成最终视频
          </van-button>
      </div>
    </div>

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

interface UIAsset extends Asset {
    script: string
    previewAspect?: number
}

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const projectId = route.params.id as string

const assets = ref<UIAsset[]>([])
const isScriptGenerating = ref(false)
const isRendering = ref(false)
let timelinePollTimer: any = null
let scriptPollTimer: any = null
const analysisDone = ref(false)

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
  startTimelinePolling()
})

onUnmounted(() => {
  stopTimelinePolling()
  stopScriptPolling()
})

const loadData = async () => {
  try {
    await projectStore.fetchProject(projectId)
    await projectStore.fetchTimeline(projectId)
    
    const storeAssets = projectStore.currentProject.assets
    const globalScript = projectStore.currentProject.script || ''
    
    const distributedScripts = distributeScript(globalScript, storeAssets.length)
    
    assets.value = storeAssets.map((a, i) => ({
        ...a,
        script: distributedScripts[i] || ''
    }))

  } catch (e) {
    showToast('加载失败')
  }
}

const distributeScript = (text: string, count: number): string[] => {
    if (count <= 0) return []
    if (!text) return new Array(count).fill('')
    
    const sentences = text.match(/[^。！？.!?]+[。！？.!?]+/g) || [text]
    
    if (sentences.length <= count) {
        const res = new Array(count).fill('')
        sentences.forEach((s, i) => res[i] = s)
        return res
    } else {
        const res = new Array(count).fill('')
        const perClip = Math.ceil(sentences.length / count)
        for (let i = 0; i < count; i++) {
            res[i] = sentences.slice(i * perClip, (i + 1) * perClip).join('')
        }
        return res
    }
}

const onVideoLoaded = (evt: Event, asset: UIAsset) => {
    const el = evt.target as HTMLVideoElement | null
    if (!el || !el.videoWidth || !el.videoHeight) return
    asset.previewAspect = el.videoWidth / el.videoHeight
}

const isPortrait = (asset: UIAsset) => {
    if (asset.previewAspect == null) return false
    return asset.previewAspect < 1
}

const startTimelinePolling = () => {
  stopTimelinePolling()
  timelinePollTimer = setInterval(async () => {
    await projectStore.fetchTimeline(projectId)
    const newAssets = projectStore.currentProject.assets
    
    let hasUpdate = false
    const mergedAssets: UIAsset[] = []
    
    newAssets.forEach(newA => {
        const oldA = assets.value.find(a => a.id === newA.id)
        if (oldA) {
            if (!oldA.sceneLabel && newA.sceneLabel) {
                hasUpdate = true
            }
            mergedAssets.push({
                ...newA,
                script: oldA.script,
                previewAspect: oldA.previewAspect
            })
        } else {
            mergedAssets.push({
                ...newA,
                script: ''
            })
            hasUpdate = true
        }
    })
    
    if (hasUpdate || newAssets.length !== assets.value.length) {
         assets.value = mergedAssets
         if (hasUpdate) showToast('AI 分析已更新')
    }

    if (!analysisDone.value) {
      const done = assets.value.length > 0 && assets.value.every(a => !!a.sceneLabel)
      if (done) {
        analysisDone.value = true
        stopTimelinePolling()
        showToast('AI 分析完成')
      }
    }

  }, 3000)
}

const stopTimelinePolling = () => {
  if (timelinePollTimer) clearInterval(timelinePollTimer)
  timelinePollTimer = null
}

const startScriptPolling = () => {
  stopScriptPolling()
  scriptPollTimer = setInterval(async () => {
    if (!isScriptGenerating.value) {
      stopScriptPolling()
      return
    }

    await projectStore.fetchProject(projectId)
    if (projectStore.currentProject.status === 'SCRIPT_GENERATED') {
      const fullScript = projectStore.currentProject.script
      const parts = distributeScript(fullScript, assets.value.length)
      assets.value.forEach((a, i) => {
        if (parts[i]) a.script = parts[i]
      })

      isScriptGenerating.value = false
      stopScriptPolling()
      showToast('脚本生成完成')
    }
  }, 1500)
}

const stopScriptPolling = () => {
  if (scriptPollTimer) clearInterval(scriptPollTimer)
  scriptPollTimer = null
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
  const updates = assets.value.map((asset, index) => {
    return projectApi.updateAsset(projectId, asset.id, { sortOrder: index })
  })
  
  try {
    await Promise.all(updates)
    projectStore.currentProject.assets = assets.value
  } catch (e) {
    showToast('排序保存失败')
  }
}

const removeAsset = (_index: number) => {
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
        startScriptPolling()
        showToast('正在生成解说词...')
    } catch (e) {
        isScriptGenerating.value = false
        stopScriptPolling()
        showToast('请求失败')
    }
}

const onGenerateVideo = async () => {
  const combinedScript = assets.value.map(a => a.script).join('\n')
  
  if (!combinedScript.trim()) {
    showToast('请先生成或填写解说词')
    return
  }
  
  isRendering.value = true
  try {
      await projectApi.generateAudio(projectId, combinedScript)
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
  padding: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
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
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  position: relative;
  transition: all 0.2s;
}

.ghost-item {
  opacity: 0.5;
  background: #e8f3ff;
}

.thumbnail-wrapper {
  width: 100%;
  height: clamp(180px, 28vw, 260px);
  background: #000;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumbnail-wrapper.portrait {
  height: clamp(180px, 28vw, 260px);
}

.video-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.thumbnail-wrapper.portrait .video-preview {
  width: auto;
  max-width: 100%;
}

.index-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 24px;
  height: 24px;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(2px);
  color: #fff;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
}

.duration-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  pointer-events: none;
}

.item-content {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.content-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-middle {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.scene-info {
  display: flex;
  align-items: center;
}

.scene-label {
  font-size: 16px;
  font-weight: 600;
  color: #323233;
}

.edit-icon {
  font-size: 16px;
  color: #1989fa;
  margin-left: 6px;
}

.actions {
    display: flex;
    align-items: center;
    gap: 16px;
}

.ai-tag {
  font-size: 11px;
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

.script-box {
    margin-top: 4px;
}

.clip-script-input {
    background: #f7f8fa;
    border-radius: 4px;
    padding: 8px;
}

.clip-script-input :deep(.van-field__control) {
    font-size: 14px;
    line-height: 1.5;
}

.drag-handle {
  cursor: grab;
  padding: 4px;
}

.delete-btn {
  padding: 4px;
}

.add-clip-btn {
  text-align: center;
  padding: 16px;
  background: #fff;
  color: #1989fa;
  font-size: 14px;
  font-weight: 500;
  margin: 16px;
  border-radius: 8px;
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
  margin-bottom: 12px;
}

.button-group {
    display: flex;
    gap: 12px;
}

.action-btn {
    flex: 1;
}

.main-btn {
    flex: 2;
}
</style>
