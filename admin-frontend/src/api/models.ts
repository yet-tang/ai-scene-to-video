/**
 * AI Models Monitoring API
 */
import request from './request'
import type { ModelStatus } from '@/types'

/**
 * Get all AI models status
 */
export function getModels(): Promise<ModelStatus[]> {
  return request.get<ModelStatus[]>('/admin/models').then((res) => res.data)
}

/**
 * Get single model status by ID
 */
export function getModel(id: string): Promise<ModelStatus> {
  return request.get<ModelStatus>(`/admin/models/${id}`).then((res) => res.data)
}

/**
 * Test model connectivity
 */
export function testModel(id: string): Promise<ModelStatus> {
  return request.post<ModelStatus>(`/admin/models/${id}/test`).then((res) => res.data)
}
