/**
 * Projects Monitoring API
 */
import request from './request'
import type { DashboardStats, ProjectListItem, ProjectDetail, PageResponse, ProjectStatus } from '@/types'

/**
 * Get dashboard statistics
 */
export function getDashboardStats(): Promise<DashboardStats> {
  return request.get<DashboardStats>('/admin/projects/stats').then((res) => res.data)
}

/**
 * Get paginated project list
 */
export function getProjects(params: {
  page?: number
  size?: number
  status?: ProjectStatus | null
  userId?: number | null
}): Promise<PageResponse<ProjectListItem>> {
  return request
    .get<PageResponse<ProjectListItem>>('/admin/projects', { params })
    .then((res) => res.data)
}

/**
 * Get project detail by ID
 */
export function getProjectDetail(id: string): Promise<ProjectDetail> {
  return request.get<ProjectDetail>(`/admin/projects/${id}`).then((res) => res.data)
}
