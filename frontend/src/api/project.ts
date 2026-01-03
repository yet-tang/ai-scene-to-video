import client from './client'

export interface CreateProjectParams {
  userId: number
  title: string
  houseInfo: {
    community: string
    room: number
    hall: number
    price: number
    area?: number
    sellingPoints?: string[]
    remarks?: string
  }
}

export interface UpdateAssetParams {
  userLabel?: string
  sortOrder?: number
}

export const projectApi = {
  create: (data: CreateProjectParams) => {
    return client.post('/projects', data)
  },

  uploadAsset: (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return client.post(`/projects/${projectId}/assets`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  updateAsset: (projectId: string, assetId: string, data: UpdateAssetParams) => {
    return client.put(`/projects/${projectId}/assets/${assetId}`, data)
  },

  getTimeline: (projectId: string) => {
    return client.get(`/projects/${projectId}/timeline`)
  },

  generateScript: (projectId: string) => {
    return client.post(`/projects/${projectId}/script`)
  },

  generateAudio: (projectId: string, scriptContent: string) => {
    return client.post(`/projects/${projectId}/audio`, scriptContent, {
        headers: {
            'Content-Type': 'text/plain; charset=utf-8'
        }
    })
  },

  renderVideo: (projectId: string) => {
    return client.post(`/projects/${projectId}/render`)
  },

  getProject: (projectId: string) => {
    return client.get(`/projects/${projectId}`)
  }
}
