/**
 * Admin Frontend TypeScript Type Definitions
 */

// Auth Types
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  username: string
  displayName: string
  role: 'ADMIN' | 'VIEWER'
  expiresAt: string
}

export interface AdminUser {
  id: string
  username: string
  displayName: string
  email: string
  role: 'ADMIN' | 'VIEWER'
  isEnabled: boolean
  lastLoginAt: string | null
  createdAt: string
}

// Project Types
export type ProjectStatus =
  | 'DRAFT'
  | 'UPLOADING'
  | 'ANALYZING'
  | 'REVIEW'
  | 'SCRIPT_GENERATING'
  | 'SCRIPT_GENERATED'
  | 'AUDIO_GENERATING'
  | 'AUDIO_GENERATED'
  | 'RENDERING'
  | 'COMPLETED'
  | 'FAILED'

export interface ProjectListItem {
  id: string
  userId: number
  title: string
  status: ProjectStatus
  errorStep: string | null
  errorAt: string | null
  createdAt: string
  assetCount: number
}

export interface AssetSummary {
  id: string
  ossUrl: string
  sceneLabel: string
  sortOrder: number
  duration: number | null
}

export interface TimelineNode {
  step: string
  status: 'SUCCESS' | 'FAILED' | 'PENDING' | 'RUNNING'
  startedAt: string | null
  completedAt: string | null
  duration: number | null
  errorMessage: string | null
}

export interface ProcessingTimeline {
  nodes: TimelineNode[]
}

export interface ProjectDetail {
  id: string
  userId: number
  title: string
  status: ProjectStatus
  houseInfo: Record<string, unknown> | null
  scriptContent: Record<string, unknown> | null
  audioUrl: string | null
  bgmUrl: string | null
  finalVideoUrl: string | null
  errorLog: string | null
  errorTaskId: string | null
  errorRequestId: string | null
  errorStep: string | null
  errorAt: string | null
  createdAt: string
  assets: AssetSummary[]
  timeline: ProcessingTimeline
}

export interface DashboardStats {
  totalProjects: number
  todayCreated: number
  todayCompleted: number
  todayFailed: number
  processingCount: number
  healthyModelCount: number
  unhealthyModelCount: number
}

// Model Types
export interface ModelStatus {
  id: string
  provider: string
  modelName: string
  agentType: string
  description: string | null
  isEnabled: boolean
  apiKeyConfigured: boolean
  lastTestAt: string | null
  lastTestStatus: string | null
  lastTestLatencyMs: number | null
  lastTestError: string | null
}

// System Types
export interface ServiceHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN'
  responseTimeMs: number
  message: string | null
}

export interface WorkerInfo {
  name: string
  status: string
  activeTasks: number
  processed: number
}

export interface CeleryStatus {
  queueName: string
  pendingTasks: number
  activeTasks: number
  workers: WorkerInfo[]
}

export interface SystemHealth {
  backend: ServiceHealth
  database: ServiceHealth
  redis: ServiceHealth
  celery: CeleryStatus
}

// Pagination Types
export interface PageRequest {
  page?: number
  size?: number
}

export interface PageResponse<T> {
  content: T[]
  totalElements: number
  totalPages: number
  number: number
  size: number
}

// API Response Types
export interface ApiError {
  timestamp: string
  status: number
  error: string
  message: string
}
