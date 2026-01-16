/**
 * User Store - Manages authentication state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminUser, LoginRequest, LoginResponse } from '@/types'
import { login as loginApi, getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('admin_token'))
  const user = ref<AdminUser | null>(null)

  // Initialize user from localStorage
  const storedUser = localStorage.getItem('admin_user')
  if (storedUser) {
    try {
      user.value = JSON.parse(storedUser)
    } catch {
      localStorage.removeItem('admin_user')
    }
  }

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'ADMIN')
  const username = computed(() => user.value?.username || '')
  const displayName = computed(() => user.value?.displayName || '')

  async function login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await loginApi(credentials)
    token.value = response.token
    localStorage.setItem('admin_token', response.token)

    // Store basic user info
    const userInfo: AdminUser = {
      id: '',
      username: response.username,
      displayName: response.displayName,
      email: '',
      role: response.role,
      isEnabled: true,
      lastLoginAt: null,
      createdAt: '',
    }
    user.value = userInfo
    localStorage.setItem('admin_user', JSON.stringify(userInfo))

    return response
  }

  async function fetchCurrentUser(): Promise<void> {
    if (!token.value) return
    try {
      const currentUser = await getCurrentUser()
      user.value = currentUser
      localStorage.setItem('admin_user', JSON.stringify(currentUser))
    } catch {
      // Token might be invalid, clear it
      logout()
    }
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_user')
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    username,
    displayName,
    login,
    fetchCurrentUser,
    logout,
  }
})
