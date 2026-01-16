<template>
  <div class="container">
  <div class="review-timeline">
    <van-nav-bar
      title="智能分段确认"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <div class="process-card app-card" :class="{ done: analysisDone, error: timelinePollHasError }">
      <div class="process-top">
        <div class="process-title">
          <van-loading v-if="processBusy" size="16" type="spinner" color="#1989fa" />
          <van-icon v-else name="passed" color="#07c160" />
          <span class="process-title-text">{{ processTitle }}</span>
        </div>
        <div class="process-actions">
          <van-button
            size="small"
            plain
            type="primary"
            :loading="timelinePollInFlight"
            @click="manualRefresh"
          >
            刷新
          </van-button>
        </div>
      </div>

      <div class="process-progress" v-if="processShowProgress">
        <van-progress :percentage="analysisProgressPercent" stroke-width="8" />
        <div class="process-sub">
          <span>{{ analysisProgressText }}</span>
          <span class="process-meta">{{ timelinePollMeta }}</span>
        </div>
      </div>

    <div class="process-error" v-if="timelinePollHasError">
      {{ timelinePollErrorText }}
    </div>
  </div>

    <template v-if="!showProgressOnly">
    <!-- 片头文案编辑区 -->
    <div class="intro-card app-card" v-if="introText || isScriptGenerating">
      <div class="intro-header">
        <span class="intro-label">🎬 片头开场白</span>
        <span class="intro-hint">视频开头的语音介绍</span>
      </div>
      <van-field
        v-model="introText"
        rows="2"
        autosize
        type="textarea"
        placeholder="大家好，今天带大家看的这套是..."
        class="intro-input"
      />

      <!-- 新增：片头卡片编辑区 -->
      <div class="intro-card-editor" v-if="introCard">
        <div class="field-row">
          <van-field v-model="introCard.headline" label="片头标题" placeholder="小区名 · 户型" input-align="right" />
        </div>
        <div class="field-row">
          <van-field v-model="introCard.specs" label="房源规格" placeholder="面积 | 装修" input-align="right" />
        </div>
        <div class="highlights-box">
          <div class="highlights-label">核心卖点</div>
          <div class="highlights-tags">
            <van-tag
              v-for="(tag, idx) in introCard.highlights"
              :key="idx"
              closeable
              size="medium"
              type="primary"
              @close="introCard.highlights.splice(idx, 1)"
              class="h-tag"
            >
              {{ tag }}
            </van-tag>
            <van-button size="mini" icon="plus" plain type="primary" @click="addHighlight" class="add-tag-btn">
              添加
            </van-button>
          </div>
        </div>
      </div>

      <div class="intro-tips">
        <span>建议 30-50 字，包含小区名、户型、一个亮点</span>
        <span class="intro-length" :class="{ warning: introText.length > 60 }">{{ introText.length }} 字</span>
      </div>
    </div>

    <div class="overview-card app-card">
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

      <div class="timeline-skeleton app-card" v-if="assets.length === 0">
        <van-skeleton title :row="6" />
      </div>

      <draggable
        v-else
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
                <div class="script-header">
                    <span class="script-label">解说词</span>
                    <span class="script-budget" :class="{ warning: (element.script || '').length > Math.floor(element.duration * 4) }">
                        {{ (element.script || '').length }} / {{ Math.floor(element.duration * 4) }} 字
                    </span>
                </div>
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
    </template>

    <van-overlay :show="isRendering" class="render-overlay">
      <div class="render-overlay-content app-card">
        <van-loading size="42" type="spinner" color="#1989fa" />
        <div class="render-overlay-title">后台正在提交合成任务</div>
        <div class="render-overlay-sub">语音生成、剪辑与字幕合成会在结果页持续更新</div>
      </div>
    </van-overlay>
  </div>
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

const isMock = computed(() => {
  const v = route.query.mock
  return v === '1' || v === 'true'
})

const mockMode = computed(() => (route.query.mockMode as string) || 'full')
const mockAssets = computed(() => Number(route.query.mockAssets ?? 5))

const assets = ref<UIAsset[]>([])
const introText = ref('')  // 片头开场白文案
const introCard = ref({
    headline: '',
    specs: '',
    highlights: [] as string[]
})
const isScriptGenerating = ref(false)
const isRendering = ref(false)
let timelinePollTimer: any = null
let scriptPollTimer: any = null
const analysisDone = ref(false)

const timelinePollActive = ref(false)
const timelinePollInFlight = ref(false)
const timelinePollCount = ref(0)
const timelinePollLastOkAt = ref<number | null>(null)
const timelinePollErrorCount = ref(0)
const timelinePollLastErrorAt = ref<number | null>(null)
const timelinePollLastErrorMessage = ref('')
const timelinePollLastUpdateAt = ref<number | null>(null)
const timelinePollLastUpdateToastAt = ref(0)

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

  if (isMock.value) {
    const count = Number.isFinite(mockAssets.value) ? mockAssets.value : 5
    if (mockMode.value === 'progress') {
      projectStore.applyMockProject(projectId, 'ANALYZING')
      projectStore.applyMockTimeline(0)
    } else {
      projectStore.applyMockProject(projectId, 'REVIEW')
      projectStore.applyMockTimeline(count)
    }

    const storeAssets = projectStore.currentProject.assets
    const globalScript = projectStore.currentProject.script || ''
    const distributed = distributeScript(globalScript, storeAssets.length, storeAssets)
    introText.value = distributed.intro
    introCard.value = distributed.card
    assets.value = storeAssets.map((a, i) => ({
      ...a,
      script: distributed.scripts[i] || ''
    }))
    analysisDone.value = mockMode.value !== 'progress'
    return
  }

  await loadData()
  if (!analysisDone.value) {
    startTimelinePolling()
  }
})

onUnmounted(() => {
  stopTimelinePolling()
  stopScriptPolling()
})

const loadData = async () => {
  if (isMock.value) return
  try {
    await projectStore.fetchProject(projectId)
    await projectStore.fetchTimeline(projectId)
    
    const storeAssets = projectStore.currentProject.assets
    const globalScript = projectStore.currentProject.script || ''
    
    const distributed = distributeScript(globalScript, storeAssets.length, storeAssets)
    introText.value = distributed.intro
    
    assets.value = storeAssets.map((a, i) => ({
        ...a,
        script: distributed.scripts[i] || ''
    }))
    analysisDone.value = assets.value.length > 0 && isSplitDoneStatus(projectStore.currentProject.status)

  } catch (e) {
    showToast('加载失败')
  }
}

const formatClock = (ts: number | null) => {
  if (!ts) return ''
  const d = new Date(ts)
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  const ss = d.getSeconds().toString().padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

const projectStatus = computed(() => projectStore.currentProject.status || '')

const isSplitDoneStatus = (status: string) => {
  return [
    'REVIEW',
    'SCRIPT_GENERATING',
    'SCRIPT_GENERATED',
    'AUDIO_GENERATING',
    'AUDIO_GENERATED',
    'RENDERING',
    'COMPLETED',
    'FAILED'
  ].includes(status)
}

const showProgressOnly = computed(() => !analysisDone.value)

const analysisLabeledCount = computed(() => assets.value.filter(a => !!a.sceneLabel).length)
const analysisTotalCount = computed(() => assets.value.length)
const analysisProgressPercent = computed(() => {
  const total = analysisTotalCount.value
  if (analysisDone.value) return 100
  if (total <= 0) return projectStatus.value === 'ANALYZING' ? 8 : 0
  const pct = Math.floor((analysisLabeledCount.value / total) * 100)
  return Math.max(0, Math.min(99, pct))
})

const analysisProgressText = computed(() => {
  if (analysisDone.value) return `已识别 ${analysisTotalCount.value} / ${analysisTotalCount.value}`
  if (analysisTotalCount.value <= 0) return '正在创建片段…'
  return `已识别 ${analysisLabeledCount.value} / ${analysisTotalCount.value}`
})

const timelinePollHasError = computed(() => timelinePollErrorCount.value > 0 && !!timelinePollLastErrorAt.value)
const timelinePollErrorText = computed(() => {
  const at = formatClock(timelinePollLastErrorAt.value)
  const msg = timelinePollLastErrorMessage.value
  return `最近一次刷新失败（${at}），将自动重试：${msg || '网络异常'}`
})

const timelinePollMeta = computed(() => {
  const okAt = formatClock(timelinePollLastOkAt.value)
  const updAt = formatClock(timelinePollLastUpdateAt.value)
  const parts = []
  if (timelinePollActive.value) parts.push(`轮询中 · 第 ${timelinePollCount.value} 次`)
  if (updAt) parts.push(`更新 ${updAt}`)
  if (okAt) parts.push(`刷新 ${okAt}`)
  return parts.join(' · ')
})

const processBusy = computed(() => {
  if (isRendering.value) return true
  if (isScriptGenerating.value) return true
  if (!analysisDone.value) return true
  return false
})

const processTitle = computed(() => {
  if (isRendering.value) return '正在提交合成任务'
  if (projectStatus.value === 'RENDERING') return '正在合成视频'
  if (projectStatus.value === 'AUDIO_GENERATING') return '正在生成语音'
  if (isScriptGenerating.value || projectStatus.value === 'SCRIPT_GENERATING') return '正在生成解说词'
  if (!analysisDone.value) {
    if (projectStatus.value === 'ANALYZING') return '后台正在智能切片与识别'
    return '正在准备智能分段'
  }
  return '分析完成，可开始确认与编辑'
})

const processShowProgress = computed(() => {
  if (isRendering.value) return false
  if (isScriptGenerating.value || projectStatus.value === 'SCRIPT_GENERATING') return false
  return true
})

const distributeScript = (text: string, count: number, assetsList: Asset[] = []): { intro: string, card: any, scripts: string[] } => {
    const result = { 
        intro: '', 
        card: { headline: '', specs: '', highlights: [] },
        scripts: new Array(count).fill('') 
    }
    if (count <= 0) return result
    if (!text) return result
    
    // Clean up text before parsing
    let cleanText = text.trim()
    
    // Remove BOM and other invisible characters
    cleanText = cleanText.replace(/^\uFEFF/, '').replace(/^\u00EF\u00BB\u00BF/, '')
    
    // Try to extract JSON if wrapped in markdown code blocks
    if (cleanText.startsWith('```json')) {
        cleanText = cleanText.slice(7)
    } else if (cleanText.startsWith('```')) {
        cleanText = cleanText.slice(3)
    }
    if (cleanText.endsWith('```')) {
        cleanText = cleanText.slice(0, -3)
    }
    cleanText = cleanText.trim()
    
    // Debug log
    console.log('distributeScript input (first 200 chars):', cleanText.slice(0, 200))
    
    // Try parse JSON
    try {
        const data = JSON.parse(cleanText)
        console.log('JSON parsed successfully:', typeof data)
        
        // New format: { intro_text: "...", intro_card: {...}, segments: [...] }
        if (data && typeof data === 'object' && !Array.isArray(data)) {
            result.intro = data.intro_text || ''
            result.card = data.intro_card || { headline: '', specs: '', highlights: [] }
            const segments = data.segments || []
            console.log('New format detected, intro:', result.intro.slice(0, 50), 'segments:', segments.length)
            
            // Map by asset_id
            const map: Record<string, string> = {}
            segments.forEach((item: any) => {
                if (item.asset_id) map[item.asset_id] = item.text || ''
            })
            
            // Return array matching assetsList order
            if (assetsList.length > 0) {
                result.scripts = assetsList.map(a => map[a.id] || '')
            } else {
                result.scripts = segments.map((item: any) => item.text || '').slice(0, count)
            }
            return result
        }
        
        // Old format: array
        if (Array.isArray(data)) {
            console.log('Old format (array) detected, length:', data.length)
            const map: Record<string, string> = {}
            data.forEach((item: any) => {
                if (item.asset_id) map[item.asset_id] = item.text || ''
            })
            
            if (assetsList.length > 0) {
                result.scripts = assetsList.map(a => map[a.id] || '')
            } else {
                result.scripts = data.map((item: any) => item.text || '').slice(0, count)
            }
            return result
        }
    } catch (e) {
        console.warn('JSON parse failed:', e)
        const jsonStart = cleanText.indexOf('{')
        const jsonEnd = cleanText.lastIndexOf('}')
        if (jsonStart !== -1 && jsonEnd > jsonStart) {
            try {
                const jsonPart = cleanText.slice(jsonStart, jsonEnd + 1)
                const data = JSON.parse(jsonPart)
                if (data && typeof data === 'object' && !Array.isArray(data)) {
                    result.intro = data.intro_text || ''
                    result.card = data.intro_card || { headline: '', specs: '', highlights: [] }
                    const segments = data.segments || []
                    const map: Record<string, string> = {}
                    segments.forEach((item: any) => {
                        if (item.asset_id) map[item.asset_id] = item.text || ''
                    })
                    if (assetsList.length > 0) {
                        result.scripts = assetsList.map(a => map[a.id] || '')
                    } else {
                        result.scripts = segments.map((item: any) => item.text || '').slice(0, count)
                    }
                    return result
                }
            } catch (e2) {}
        }
    }
    
    console.warn('Falling back to plain text split')
    const sentences = text.match(/[^。！？.!?]+[。！？.!?]+/g) || [text]
    
    if (sentences.length <= count) {
        sentences.forEach((s, i) => result.scripts[i] = s)
    } else {
        const perClip = Math.ceil(sentences.length / count)
        for (let i = 0; i < count; i++) {
            result.scripts[i] = sentences.slice(i * perClip, (i + 1) * perClip).join('')
        }
    }
    return result
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

const mergeTimelineAssets = (newAssets: Asset[]) => {
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
    timelinePollLastUpdateAt.value = Date.now()
    const now = Date.now()
    if (hasUpdate && now - timelinePollLastUpdateToastAt.value > 8000) {
      showToast('AI 分析结果已更新')
      timelinePollLastUpdateToastAt.value = now
    }
  }

  // 检查是否分析完成
  const done = assets.value.length > 0 && isSplitDoneStatus(projectStatus.value)
  if (done) {
    if (!analysisDone.value) {
      analysisDone.value = true
      showToast('AI 分析完成')
    }
    stopTimelinePolling()
  }
}

const pollTimelineOnce = async () => {
  if (timelinePollInFlight.value) return
  timelinePollInFlight.value = true
  timelinePollCount.value += 1
  try {
    await projectStore.fetchTimeline(projectId)

    timelinePollLastOkAt.value = Date.now()
    timelinePollErrorCount.value = 0
    timelinePollLastErrorAt.value = null
    timelinePollLastErrorMessage.value = ''

    const newAssets = projectStore.currentProject.assets
    mergeTimelineAssets(newAssets)
  } catch (e: any) {
    timelinePollErrorCount.value += 1
    timelinePollLastErrorAt.value = Date.now()
    timelinePollLastErrorMessage.value = (e && (e.message || e.toString())) || ''

    if (timelinePollErrorCount.value === 1) {
      showToast('刷新失败，将自动重试')
    }
  } finally {
    timelinePollInFlight.value = false
  }
}

const manualRefresh = async () => {
  if (isMock.value) {
    showToast('Mock 模式下不刷新')
    return
  }
  await pollTimelineOnce()
}

const startTimelinePolling = () => {
  stopTimelinePolling()
  timelinePollActive.value = true
  pollTimelineOnce()
  timelinePollTimer = setInterval(async () => {
    await pollTimelineOnce()

  }, 3000)
}

const stopTimelinePolling = () => {
  if (timelinePollTimer) clearInterval(timelinePollTimer)
  timelinePollTimer = null
  timelinePollActive.value = false
}

const startScriptPolling = () => {
  stopScriptPolling()
  scriptPollTimer = setInterval(async () => {
    // 先检查当前状态是否已完成，避免不必要的请求
    if (isScriptDoneStatus(projectStatus.value)) {
      isScriptGenerating.value = false
      stopScriptPolling()
      return
    }

    await projectStore.fetchProject(projectId)
    
    // 如果达到或超过已生成状态，更新数据并停止
    if (isScriptDoneStatus(projectStatus.value)) {
      const fullScript = projectStore.currentProject.script
      const distributed = distributeScript(fullScript, assets.value.length, assets.value)
      introText.value = distributed.intro
      introCard.value = distributed.card
      assets.value.forEach((a, i) => {
        if (distributed.scripts[i]) a.script = distributed.scripts[i]
      })

      isScriptGenerating.value = false
      stopScriptPolling()
      showToast('脚本生成完成')
    }
  }, 1500)
}

const isScriptDoneStatus = (status: string) => {
  return [
    'SCRIPT_GENERATED',
    'AUDIO_GENERATING',
    'AUDIO_GENERATED',
    'RENDERING',
    'COMPLETED'
  ].includes(status)
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
  if (isMock.value) {
    showToast('Mock 模式下不保存排序')
    return
  }
  const updates = assets.value.map((asset, index) => {
    return projectApi.updateAsset(projectId, asset.id, { sortOrder: index })
  })
  
  try {
    await Promise.all(updates)
    projectStore.currentProject.assets = assets.value
    showToast('排序已保存')
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
        if (isMock.value) {
          showToast('Mock 模式下不保存修改')
        } else {
        await projectApi.updateAsset(projectId, asset.id, { userLabel: newVal })
        }
    } catch (e) {
        showToast('修改失败')
    }
  }
  showPicker.value = false
}

const addHighlight = () => {
  const val = window.prompt('请输入核心卖点标签')
  if (val && val.trim()) {
    if (!introCard.value.highlights) introCard.value.highlights = []
    introCard.value.highlights.push(val.trim())
  }
}

const onGenerateScript = async () => {
    if (isMock.value) {
      showToast('Mock 模式下不生成解说')
      return
    }
    isScriptGenerating.value = true
    try {
        await projectApi.generateScript(projectId)
        startScriptPolling()
        showToast('已提交生成解说词任务')
    } catch (e) {
        isScriptGenerating.value = false
        stopScriptPolling()
        showToast('请求失败')
    }
}

const onGenerateVideo = async () => {
  if (isMock.value) {
    router.push(`/result/${projectId}?mock=1&mockStatus=loading`)
    return
  }
  
  const scriptSegments = assets.value.map(a => ({
      asset_id: a.id,
      text: a.script || ''
  }))
  const hasText = scriptSegments.some(s => s.text.trim().length > 0)
  
  if (!hasText) {
    showToast('请先生成或填写解说词')
    return
  }
  
  // 组装新格式：包含 intro_text, intro_card 和 segments
  const combinedScript = JSON.stringify({
    intro_text: introText.value || '',
    intro_card: introCard.value,
    segments: scriptSegments
  })
  
  isRendering.value = true
  try {
      await projectApi.updateScript(projectId, combinedScript)
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

/* 片头文案编辑区 */
.intro-card {
  margin: 12px 16px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f5f9ff 0%, #fff8f5 100%);
  border: 1px solid #e8f3ff;
}

.intro-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.intro-label {
  font-size: 14px;
  font-weight: 600;
  color: #1989fa;
}

.intro-hint {
  font-size: 12px;
  color: #94a3b8;
}

.intro-input {
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.intro-input :deep(.van-field__control) {
  font-size: 14px;
  line-height: 1.6;
  color: #334155;
}

.intro-card-editor {
  margin-top: 12px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  padding: 4px 0;
}

.intro-card-editor :deep(.van-field) {
  background: transparent;
  padding: 8px 0;
}

.highlights-box {
  padding: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.highlights-label {
  font-size: 13px;
  color: #64748b;
  padding-left: 0;
}

.highlights-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.h-tag {
  padding: 4px 8px;
}

.add-tag-btn {
  height: 24px;
  padding: 0 8px;
}

.intro-tips {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 11px;
  color: #94a3b8;
  padding: 0 4px;
}

.intro-length {
  color: #64748b;
}

.intro-length.warning {
  color: #ff976a;
}

.overview-card {
  margin: 12px 16px;
  padding: 16px 8px;
  display: flex;
  align-items: center;
  justify-content: space-around;
}

.process-card {
  margin: 12px 16px;
  padding: 12px 12px;
  border: var(--app-card-border);
}

.process-card.done {
  border-color: rgba(7, 193, 96, 0.25);
}

.process-card.error {
  border-color: rgba(238, 10, 36, 0.25);
}

.process-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.process-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.process-title-text {
  font-size: 14px;
  font-weight: 600;
  color: #323233;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.process-actions {
  flex-shrink: 0;
}

.process-progress {
  margin-top: 10px;
}

.process-sub {
  margin-top: 8px;
  font-size: 12px;
  color: #475569;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.process-meta {
  color: #94a3b8;
  white-space: nowrap;
}

.process-error {
  margin-top: 10px;
  font-size: 12px;
  color: #ee0a24;
  line-height: 1.4;
}

.timeline-skeleton {
  margin: 0 16px;
  padding: 12px;
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
  margin: 0 16px 12px;
  display: flex;
  flex-direction: column;
  border-radius: var(--app-card-radius);
  overflow: hidden;
  border: var(--app-card-border);
  box-shadow: var(--app-card-shadow);
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
  cursor: pointer;
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

.script-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
    padding: 0 4px;
}

.script-label {
    font-size: 12px;
    color: #64748b;
}

.script-budget {
    font-size: 11px;
    color: #94a3b8;
}

.script-budget.warning {
    color: #ff976a;
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
  cursor: pointer;
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
  cursor: pointer;
}

.render-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
}

.render-overlay-content {
  width: min(360px, calc(100vw - 48px));
  background: rgba(255, 255, 255, 0.96);
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.render-overlay-title {
  font-size: 15px;
  font-weight: 600;
  color: #323233;
}

.render-overlay-sub {
  font-size: 12px;
  color: #64748b;
  text-align: center;
  line-height: 1.5;
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
