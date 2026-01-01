import { defineStore } from 'pinia'
import { ref } from 'vue'

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
  file?: File
  url: string // Local preview URL or OSS URL
  sceneLabel: string
  userLabel: string
  duration: number
  sortOrder: number
  thumbnail?: string
}

export const useProjectStore = defineStore('project', () => {
  const currentProject = ref<{
    id: string
    info: ProjectInfo
    assets: Asset[]
    script: string
    finalVideoUrl: string
    status: 'draft' | 'uploading' | 'analyzing' | 'review' | 'rendering' | 'completed' | 'failed'
  }>({
    id: '',
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
    finalVideoUrl: '',
    status: 'draft'
  })

  function setProjectInfo(info: ProjectInfo) {
    currentProject.value.info = info
  }

  function addAssets(newAssets: Asset[]) {
    currentProject.value.assets.push(...newAssets)
  }

  function updateAsset(id: string, updates: Partial<Asset>) {
    const asset = currentProject.value.assets.find(a => a.id === id)
    if (asset) {
      Object.assign(asset, updates)
    }
  }

  function setTimeline(assets: Asset[]) {
    currentProject.value.assets = assets
  }

  return {
    currentProject,
    setProjectInfo,
    addAssets,
    updateAsset,
    setTimeline
  }
})
