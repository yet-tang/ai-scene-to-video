/**
 * Authentication API
 */
import request from './request'
import type { LoginRequest, LoginResponse, AdminUser } from '@/types'

/**
 * Admin user login
 */
export function login(data: LoginRequest): Promise<LoginResponse> {
  return request.post<LoginResponse>('/admin/auth/login', data).then((res) => res.data)
}

/**
 * Get current user info
 */
export function getCurrentUser(): Promise<AdminUser> {
  return request.get<AdminUser>('/admin/auth/me').then((res) => res.data)
}
