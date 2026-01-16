/**
 * System Monitoring API
 */
import request from './request'
import type { SystemHealth } from '@/types'

/**
 * Get system health status
 */
export function getSystemHealth(): Promise<SystemHealth> {
  return request.get<SystemHealth>('/admin/system/health').then((res) => res.data)
}
