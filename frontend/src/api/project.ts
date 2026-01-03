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

export interface PresignedUrlResponse {
  uploadUrl: string
  publicUrl: string
  objectKey: string
  signedHeaders: Record<string, string>
}

export interface AssetConfirmRequest {
  objectKey: string
  filename: string
  contentType: string
  size: number
}

export const projectApi = {
  create: (data: CreateProjectParams) => {
    return client.post('/v1/projects', data)
  },

  getPresignedUrl: (projectId: string, filename: string, contentType: string) => {
    return client.post<PresignedUrlResponse>(`/v1/projects/${projectId}/assets/presign`, null, {
      params: { filename, contentType }
    })
  },

  confirmAsset: (projectId: string, data: AssetConfirmRequest) => {
    return client.post(`/v1/projects/${projectId}/assets/confirm`, data)
  },

  uploadAsset: (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return client.post(`/v1/projects/${projectId}/assets`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  uploadAssetLocal: (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return client.post(`/v1/projects/${projectId}/assets/local`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  updateAsset: (projectId: string, assetId: string, data: UpdateAssetParams) => {
    return client.put(`/v1/projects/${projectId}/assets/${assetId}`, data)
  },

  getTimeline: (projectId: string) => {
    return client.get(`/v1/projects/${projectId}/timeline`)
  },

  generateScript: (projectId: string) => {
    return client.post(`/v1/projects/${projectId}/script`)
  },

  generateAudio: (projectId: string, scriptContent: string) => {
    return client.post(`/v1/projects/${projectId}/audio`, scriptContent, {
        headers: {
            'Content-Type': 'text/plain; charset=utf-8'
        }
    })
  },

  renderVideo: (projectId: string) => {
    return client.post(`/v1/projects/${projectId}/render`)
  },

  getProject: (projectId: string) => {
    return client.get(`/v1/projects/${projectId}`)
  }
}
