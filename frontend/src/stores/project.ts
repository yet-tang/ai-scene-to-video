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

  return {
    currentProject,
    fetchProject,
    fetchTimeline
  }
})
