/**
 * Admin Users Management API
 */
import request from './request'
import type { AdminUser, PageResponse } from '@/types'

export interface CreateUserRequest {
  username: string
  password: string
  displayName: string
  email?: string
  role: 'ADMIN' | 'VIEWER'
}

/**
 * Get paginated admin users list
 */
export function getUsers(params: { page?: number; size?: number }): Promise<PageResponse<AdminUser>> {
  return request.get<PageResponse<AdminUser>>('/admin/users', { params }).then((res) => res.data)
}

/**
 * Get single admin user by ID
 */
export function getUser(id: string): Promise<AdminUser> {
  return request.get<AdminUser>(`/admin/users/${id}`).then((res) => res.data)
}

/**
 * Create new admin user
 */
export function createUser(data: CreateUserRequest): Promise<AdminUser> {
  return request.post<AdminUser>('/admin/users', data).then((res) => res.data)
}

/**
 * Update user enabled status
 */
export function updateUserStatus(id: string, enabled: boolean): Promise<AdminUser> {
  return request.put<AdminUser>(`/admin/users/${id}/status`, null, { params: { enabled } }).then((res) => res.data)
}

/**
 * Delete admin user
 */
export function deleteUser(id: string): Promise<void> {
  return request.delete(`/admin/users/${id}`)
}
