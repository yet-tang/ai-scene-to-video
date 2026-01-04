import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectApi } from '../api/project'

export interface ProjectInfo {
  communityName: string
  layout: {
    room: number
    hall: number
    restroom: number
  }
  area: number | undefined
  price: number | undefined
  sellingPoints: string[]
  remarks: string
}

export interface Asset {
  id: string
  url: string // OSS URL
  sceneLabel: string
  userLabel: string
  duration: number
  sortOrder: number
  sceneScore?: number
}

export const useProjectStore = defineStore('project', () => {
  const currentProject = ref<{
    id: string
    title: string
    info: ProjectInfo
    assets: Asset[]
    script: string
    audioUrl: string
    finalVideoUrl: string
    status: string
  }>({
    id: '',
    title: '',
    info: {
      communityName: '',
      layout: { room: 2, hall: 1, restroom: 1 },
      area: undefined,
      price: undefined,
      sellingPoints: [],
      remarks: ''
    },
    assets: [],
    script: '',
    audioUrl: '',
    finalVideoUrl: '',
    status: 'DRAFT'
  })

  async function fetchProject(id: string) {
    try {
      const { data } = await projectApi.getProject(id)
      // Map backend response to store state
      currentProject.value.id = data.id
      currentProject.value.title = data.title
      currentProject.value.status = data.status
      currentProject.value.script = data.scriptContent
      currentProject.value.audioUrl = data.audioUrl
      currentProject.value.finalVideoUrl = data.finalVideoUrl
      
      // Parse houseInfo (JSON)
      if (data.houseInfo) {
        const h = data.houseInfo
        currentProject.value.info = {
            communityName: h.community || '',
            layout: { 
                room: h.room || 0, 
                hall: h.hall || 0, 
                restroom: h.restroom || 0 
            },
            area: h.area,
            price: h.price,
            sellingPoints: h.sellingPoints || [],
            remarks: h.remarks || ''
        }
      }
    } catch (error) {
      console.error('Failed to fetch project', error)
      throw error
    }
  }

  async function fetchTimeline(id: string) {
    try {
      const { data } = await projectApi.getTimeline(id)
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
      let origin = ''
      try {
        origin = new URL(apiBaseUrl).origin
      } catch (e) {
        origin = ''
      }
      
      currentProject.value.assets = data.assets.map((a: any) => {
        let url = a.ossUrl
        if (origin && url) {
          if (url.startsWith('file://')) {
            const filename = url.split('/').pop()
            url = `${origin}/assets/ai-video/public/${filename}`
          } else if (url.startsWith('http://ai-scene-backend:8090/public/')) {
            const filename = url.split('/').pop()
            url = `${origin}/assets/ai-video/public/${filename}`
          }
        }
        
        return {
            id: a.id,
            url: url,
            sceneLabel: a.sceneLabel,
            userLabel: a.userLabel || a.sceneLabel,
            duration: a.duration || 0,
            sortOrder: a.sortOrder,
            sceneScore: a.sceneScore
        }
      })
      if (data.scriptContent) {
        currentProject.value.script = data.scriptContent
      }
    } catch (error) {
        console.error('Failed to fetch timeline', error)
        throw error
    }
  }

  function applyMockProject(id: string, status: string) {
    const mockVideoUrl = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
    const mockAudioUrl = 'https://interactive-examples.mdn.mozilla.net/media/examples/t-rex-roar.mp3'

    currentProject.value.id = id
    currentProject.value.title = 'Mock 项目 - 阳光花园 2室1厅'
    currentProject.value.status = status
    currentProject.value.script = '欢迎来到阳光花园，小区环境优美，配套成熟。客厅通透明亮，卧室安静舒适。'
    currentProject.value.info = {
      communityName: '阳光花园',
      layout: { room: 2, hall: 1, restroom: 1 },
      area: 89,
      price: 268,
      sellingPoints: ['南北通透', '地铁沿线', '学区房'],
      remarks: 'Mock 数据，仅用于页面预览。'
    }

    if (status === 'COMPLETED') {
      currentProject.value.audioUrl = mockAudioUrl
      currentProject.value.finalVideoUrl = mockVideoUrl
      return
    }

    if (status === 'AUDIO_GENERATED' || status === 'RENDERING') {
      currentProject.value.audioUrl = mockAudioUrl
      currentProject.value.finalVideoUrl = ''
      return
    }

    currentProject.value.audioUrl = ''
    currentProject.value.finalVideoUrl = ''
  }

  function applyMockTimeline(assetCount = 5) {
    const mockVideoUrl = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
    const labels = ['小区环境', '客厅', '餐厅', '主卧', '厨房', '卫生间']

    const count = Math.max(0, Math.min(12, assetCount))
    currentProject.value.assets = Array.from({ length: count }).map((_, idx) => {
      const label = labels[idx % labels.length] ?? '其他'
      return {
        id: `mock-asset-${idx + 1}`,
        url: mockVideoUrl,
        sceneLabel: label,
        userLabel: label,
        duration: 10 + (idx % 4) * 3,
        sortOrder: idx
      }
    })
  }

  return {
    currentProject,
    fetchProject,
    fetchTimeline,
    applyMockProject,
    applyMockTimeline
  }
})
