<template>
  <a-layout class="admin-layout">
    <a-layout-sider v-model:collapsed="collapsed" collapsible theme="dark">
      <div class="logo">
        <span v-if="!collapsed">AI Scene Admin</span>
        <span v-else>AI</span>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="inline"
        @click="handleMenuClick"
      >
        <a-menu-item key="Dashboard">
          <template #icon><DashboardOutlined /></template>
          <span>Dashboard</span>
        </a-menu-item>
        <a-menu-item key="ProjectList">
          <template #icon><ProjectOutlined /></template>
          <span>Projects</span>
        </a-menu-item>
        <a-menu-item key="ModelList">
          <template #icon><ApiOutlined /></template>
          <span>AI Models</span>
        </a-menu-item>
        <a-menu-item key="SystemHealth">
          <template #icon><MonitorOutlined /></template>
          <span>System</span>
        </a-menu-item>
        <a-menu-item v-if="userStore.isAdmin" key="UserList">
          <template #icon><UserOutlined /></template>
          <span>Users</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>
    <a-layout>
      <a-layout-header class="header">
        <div class="header-content">
          <span class="page-title">{{ currentTitle }}</span>
          <div class="user-info">
            <a-dropdown>
              <a class="user-dropdown" @click.prevent>
                <UserOutlined />
                <span class="username">{{ userStore.displayName }}</span>
                <DownOutlined />
              </a>
              <template #overlay>
                <a-menu>
                  <a-menu-item @click="handleLogout">
                    <LogoutOutlined />
                    <span>Logout</span>
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
        </div>
      </a-layout-header>
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  DashboardOutlined,
  ProjectOutlined,
  ApiOutlined,
  MonitorOutlined,
  UserOutlined,
  DownOutlined,
  LogoutOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>([])

const pageTitles: Record<string, string> = {
  Dashboard: 'Dashboard',
  ProjectList: 'Project Monitor',
  ProjectDetail: 'Project Detail',
  ModelList: 'AI Model Monitor',
  SystemHealth: 'System Monitor',
  UserList: 'User Management',
}

const currentTitle = computed(() => {
  const name = route.name as string
  return pageTitles[name] || 'Admin'
})

// Update selected keys based on route
watch(
  () => route.name,
  (name) => {
    if (name) {
      // Map detail pages to their list pages for menu highlight
      const menuKey = name === 'ProjectDetail' ? 'ProjectList' : (name as string)
      selectedKeys.value = [menuKey]
    }
  },
  { immediate: true }
)

function handleMenuClick({ key }: { key: string }) {
  router.push({ name: key })
}

function handleLogout() {
  userStore.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  background: rgba(255, 255, 255, 0.1);
}

.header {
  background: #fff;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}

.user-info {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(0, 0, 0, 0.85);
}

.username {
  margin: 0 4px;
}

.content {
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 64px - 48px);
}
</style>
