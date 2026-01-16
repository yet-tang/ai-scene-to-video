<template>
  <div class="user-list">
    <div class="toolbar">
      <a-button type="primary" @click="showCreateModal">
        <template #icon><PlusOutlined /></template>
        Create User
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="users"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'role'">
          <a-tag :color="record.role === 'ADMIN' ? 'blue' : 'default'">
            {{ record.role }}
          </a-tag>
        </template>
        <template v-if="column.key === 'isEnabled'">
          <a-switch
            :checked="record.isEnabled"
            :loading="updatingIds.includes(record.id)"
            @change="(checked: boolean) => handleStatusChange(record.id, checked)"
          />
        </template>
        <template v-if="column.key === 'lastLoginAt'">
          {{ record.lastLoginAt ? formatDate(record.lastLoginAt) : 'Never' }}
        </template>
        <template v-if="column.key === 'createdAt'">
          {{ formatDate(record.createdAt) }}
        </template>
        <template v-if="column.key === 'action'">
          <a-popconfirm
            title="Are you sure to delete this user?"
            @confirm="handleDelete(record.id)"
            :disabled="deletingIds.includes(record.id)"
          >
            <a-button type="link" danger :loading="deletingIds.includes(record.id)">
              Delete
            </a-button>
          </a-popconfirm>
        </template>
      </template>
    </a-table>

    <!-- Create User Modal -->
    <a-modal
      v-model:open="createModalVisible"
      title="Create Admin User"
      @ok="handleCreate"
      :confirmLoading="creating"
    >
      <a-form :model="createForm" :rules="createRules" ref="createFormRef" layout="vertical">
        <a-form-item label="Username" name="username">
          <a-input v-model:value="createForm.username" placeholder="Enter username" />
        </a-form-item>
        <a-form-item label="Password" name="password">
          <a-input-password v-model:value="createForm.password" placeholder="Enter password" />
        </a-form-item>
        <a-form-item label="Display Name" name="displayName">
          <a-input v-model:value="createForm.displayName" placeholder="Enter display name" />
        </a-form-item>
        <a-form-item label="Email" name="email">
          <a-input v-model:value="createForm.email" placeholder="Enter email (optional)" />
        </a-form-item>
        <a-form-item label="Role" name="role">
          <a-select v-model:value="createForm.role">
            <a-select-option value="ADMIN">ADMIN</a-select-option>
            <a-select-option value="VIEWER">VIEWER</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { getUsers, createUser, updateUserStatus, deleteUser } from '@/api/users'
import type { AdminUser, PageResponse } from '@/types'
import type { CreateUserRequest } from '@/api/users'
import type { FormInstance, TablePaginationConfig } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'

const loading = ref(false)
const users = ref<AdminUser[]>([])
const updatingIds = ref<string[]>([])
const deletingIds = ref<string[]>([])

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `Total ${total} items`,
})

// Create modal
const createModalVisible = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive<CreateUserRequest>({
  username: '',
  password: '',
  displayName: '',
  email: '',
  role: 'VIEWER',
})

const createRules: Record<string, Rule[]> = {
  username: [
    { required: true, message: 'Please enter username' },
    { min: 3, max: 50, message: 'Username must be 3-50 characters' },
  ],
  password: [
    { required: true, message: 'Please enter password' },
    { min: 6, message: 'Password must be at least 6 characters' },
  ],
  displayName: [{ required: true, message: 'Please enter display name' }],
  role: [{ required: true, message: 'Please select role' }],
}

const columns = [
  { title: 'Username', dataIndex: 'username', key: 'username' },
  { title: 'Display Name', dataIndex: 'displayName', key: 'displayName' },
  { title: 'Email', dataIndex: 'email', key: 'email' },
  { title: 'Role', dataIndex: 'role', key: 'role', width: 100 },
  { title: 'Enabled', dataIndex: 'isEnabled', key: 'isEnabled', width: 100 },
  { title: 'Last Login', dataIndex: 'lastLoginAt', key: 'lastLoginAt', width: 180 },
  { title: 'Created At', dataIndex: 'createdAt', key: 'createdAt', width: 180 },
  { title: 'Action', key: 'action', width: 100 },
]

function formatDate(date: string): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

async function fetchUsers() {
  loading.value = true
  try {
    const response: PageResponse<AdminUser> = await getUsers({
      page: pagination.current - 1,
      size: pagination.pageSize,
    })
    users.value = response.content
    pagination.total = response.totalElements
  } finally {
    loading.value = false
  }
}

function handleTableChange(pag: TablePaginationConfig) {
  pagination.current = pag.current || 1
  pagination.pageSize = pag.pageSize || 10
  fetchUsers()
}

function showCreateModal() {
  createForm.username = ''
  createForm.password = ''
  createForm.displayName = ''
  createForm.email = ''
  createForm.role = 'VIEWER'
  createModalVisible.value = true
}

async function handleCreate() {
  try {
    await createFormRef.value?.validate()
  } catch {
    return
  }

  creating.value = true
  try {
    await createUser(createForm)
    message.success('User created successfully')
    createModalVisible.value = false
    fetchUsers()
  } catch {
    message.error('Failed to create user')
  } finally {
    creating.value = false
  }
}

async function handleStatusChange(id: string, enabled: boolean) {
  updatingIds.value.push(id)
  try {
    await updateUserStatus(id, enabled)
    const index = users.value.findIndex((u) => u.id === id)
    if (index !== -1 && users.value[index]) {
      users.value[index]!.isEnabled = enabled
    }
    message.success('User status updated')
  } catch {
    message.error('Failed to update user status')
  } finally {
    updatingIds.value = updatingIds.value.filter((i) => i !== id)
  }
}

async function handleDelete(id: string) {
  deletingIds.value.push(id)
  try {
    await deleteUser(id)
    message.success('User deleted successfully')
    fetchUsers()
  } catch {
    message.error('Failed to delete user')
  } finally {
    deletingIds.value = deletingIds.value.filter((i) => i !== id)
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-list {
  width: 100%;
}

.toolbar {
  margin-bottom: 16px;
}
</style>
