import axios, { AxiosError } from 'axios'
import { message } from 'antd'
import { z } from 'zod'
import { clearAuthSession, getAuthToken, setAccessToken } from '@/auth'
import { safeGet, safePost } from '@/lib/safeApi'
import type {
  CompetitiveLandscape,
  CounterfactualResponse,
  FeatureSet,
  HistoryRecord,
  MarketSizingResponse,
  PartnershipItem,
  PredictionResponse,
  RiskRegisterResponse,
  RegulatoryMilestone,
  RoadmapPhase,
  Scenario,
  StrategyOptionsResponse,
  TherapeuticArea,
} from '@/types'

type StrategyFeedOption = {
  id: string
  name: string
  summary: string
  timeline: string
  focus: string
}

type AdminUserQuery = {
  limit?: number
  offset?: number
  role?: 'admin' | 'researcher' | 'viewer' | 'all'
  search?: string
}

type AdminAuditQuery = {
  limit?: number
  offset?: number
  method?: string
  status?: string | number
  path?: string
  requestId?: string
}

type AdminApprovalDecision = 'approved' | 'rejected'

export type AdminAnalyticsStats = {
  total_predictions: number
  average_probability: number
  pass_rate: number
  verdict_breakdown: Record<string, number>
  daily_volume_7d: Array<{ date: string; count: number }>
  model_version?: string
  features_monitored?: number
  database_type?: string
  total_users?: number
  audit_events_24h?: number
  audit_anomalies_24h?: number
  drift_alert_count_30d?: number
  latest_model?: Record<string, unknown> | null
}

export type AdminModelAnalytics = {
  latest: Record<string, unknown>
  history: Array<Record<string, unknown>>
  drift_alerts: Array<Record<string, unknown>>
  summary: {
    versions_tracked: number
    drift_alert_count_30d: number
  }
}

export type AdminControlApproval = {
  id: string
  title: string
  category: string
  status: string
  requested_by: string
  requested_at: string
  reviewed_by?: string
  reviewed_at?: string
  reason?: string
}

export type AdminFeatureFlag = {
  key: string
  enabled: boolean
  description?: string
}

const predictResponseRuntimeSchema = z.object({
  success_probability: z.number().min(0).max(1),
  verdict: z.record(z.string(), z.unknown()),
  confidence_interval: z.record(z.string(), z.unknown()),
  shap_breakdown: z.record(z.string(), z.unknown()),
  phase_probabilities: z.record(z.string(), z.number()),
  admet: z.record(z.string(), z.unknown()),
  warnings: z.array(z.string()),
})

const historyRuntimeSchema = z.array(
  z.object({
    id: z.string(),
    timestamp: z.string(),
    toxicity: z.number(),
    bioavailability: z.number(),
    solubility: z.number(),
    binding: z.number(),
    molecular_weight: z.number(),
    probability: z.number(),
    verdict: z.string(),
    warnings: z.array(z.string()).optional().default([]),
    tags: z.array(z.string()).optional().default([]),
    notes: z.string().optional().default(''),
    compound_name: z.string().optional().default('Unnamed'),
    shap_breakdown: z.record(z.string(), z.unknown()).nullable().optional(),
  })
)

const scenariosRuntimeSchema = z.array(
  z.object({
    id: z.string(),
    name: z.string(),
    created_at: z.string().optional(),
    inputs: z.record(z.string(), z.unknown()).optional().default({}),
    outputs: z.record(z.string(), z.unknown()).optional(),
    tags: z.array(z.string()).optional(),
  })
)

const strategyOptionsRuntimeSchema = z.object({
  recommended: z.string(),
  recommendation_summary: z.string(),
  options: z.array(z.record(z.string(), z.unknown())),
})

const strategyFeedRuntimeSchema = z.object({
  options: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      summary: z.string(),
      timeline: z.string(),
      focus: z.string(),
    })
  ),
})

const competitiveLandscapeRuntimeSchema = z.object({
  positioning_axes: z.object({ x: z.string(), y: z.string() }),
  players: z.array(z.record(z.string(), z.unknown())),
  regional_signal: z.array(z.record(z.string(), z.unknown())).optional().default([]),
})

const regulatoryTimelineRuntimeSchema = z.object({
  timeline: z.array(z.record(z.string(), z.unknown())),
})

const partnershipsRuntimeSchema = z.object({
  partners: z.array(z.record(z.string(), z.unknown())),
})

const roadmapRuntimeSchema = z.object({
  roadmap: z.array(z.record(z.string(), z.unknown())),
})

const marketSizingRuntimeSchema = z.record(z.string(), z.unknown())

const riskRegisterRuntimeSchema = z.record(z.string(), z.unknown())

const executiveSummaryRuntimeSchema = z.record(z.string(), z.unknown())

function normalizeApiBase(raw: string | undefined): string {
  const fallback = 'http://localhost:5000/api/v1'
  if (!raw) return fallback
  const trimmed = raw.replace(/\/$/, '')
  if (trimmed.startsWith('/')) return trimmed
  if (/\/api(?:\/v\d+)?(?:\/|$)/i.test(trimmed)) return trimmed
  return `${trimmed}/api/v1`
}

const apiBaseURL = normalizeApiBase(import.meta.env.VITE_API_URL as string | undefined)

const client = axios.create({
  baseURL: apiBaseURL,
  timeout: 12000,
  withCredentials: true,
})

const nodeApiBaseURL = (import.meta.env.VITE_NODE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '/api'

const nodeClient = axios.create({
  baseURL: nodeApiBaseURL,
  timeout: 12000,
  withCredentials: true,
})

const refreshClient = axios.create({
  baseURL: apiBaseURL,
  timeout: 12000,
  withCredentials: true,
})

function attachAuth(config: import('axios').InternalAxiosRequestConfig) {
  const token = getAuthToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

client.interceptors.request.use(attachAuth)
nodeClient.interceptors.request.use(attachAuth)

let refreshInFlight: Promise<string | null> | null = null

function shouldRedirectToLogin(pathname: string): boolean {
  if (pathname === '/') {
    return false
  }
  if (pathname.startsWith('/login')) {
    return false
  }
  return true
}

async function attemptRefreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const { data } = await refreshClient.post('/auth/refresh')
        const token = unwrap<{ access_token?: string }>(data)?.access_token ?? null
        setAccessToken(token)
        return token
      } catch {
        setAccessToken(null)
        return null
      } finally {
        refreshInFlight = null
      }
    })()
  }
  return refreshInFlight
}

async function handleAuthError(error: unknown) {
  if (!axios.isAxiosError(error)) return Promise.reject(error)
  const original = error.config
  if (!original) return Promise.reject(error)

  const status = error.response?.status
  const isRefreshRequest = original.url?.includes('/auth/refresh')
  if (status === 401 && !isRefreshRequest && !(original as { _retry?: boolean })._retry) {
    ;(original as { _retry?: boolean })._retry = true
    const nextToken = await attemptRefreshAccessToken()
    if (nextToken) {
      original.headers = original.headers ?? {}
      original.headers.Authorization = `Bearer ${nextToken}`
      return axios.request(original)
    }
  }

  if (status === 401) {
    clearAuthSession()
    if (typeof window !== 'undefined') {
      const pathname = window.location.pathname
      if (!isRefreshRequest && shouldRedirectToLogin(pathname)) {
        window.location.href = '/login'
      }
    }
  }

  return Promise.reject(error)
}

client.interceptors.response.use((response) => response, handleAuthError)
nodeClient.interceptors.response.use((response) => response, handleAuthError)

function unwrap<T>(data: unknown): T {
  if (typeof data === 'object' && data !== null && 'data' in data) {
    const maybe = data as { data: T }
    if (maybe.data !== null && maybe.data !== undefined) {
      return maybe.data
    }
  }
  return data as T
}

function toErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ error?: string; message?: string }>
    return axiosError.response?.data?.error ?? axiosError.response?.data?.message ?? axiosError.message
  }
  return 'Unexpected request error'
}

function shouldRetryFlaskV1Auth(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false
  const status = error.response?.status
  const messageText = String(error.response?.data?.error ?? error.response?.data?.message ?? '').toLowerCase()
  const requestUrl = String(error.config?.url ?? '').toLowerCase()
  const isAuthRoute = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register')
  if (status === 400 && messageText.includes('id token is required')) return true
  return status === 404 && isAuthRoute
}

function handleShapeMismatch(error: unknown): void {
  if (error instanceof Error && error.message.includes('Unexpected response shape from')) {
    message.error('Server response format has changed. Please contact support.')
  }
}

function normalizeStrategyFeedOptions(rawOptions: Array<Record<string, unknown>>): StrategyFeedOption[] {
  return rawOptions.map((option, index) => {
    const id = typeof option.id === 'string' ? option.id : `strategy-${index + 1}`
    const name = typeof option.name === 'string' ? option.name : `Strategy ${index + 1}`
    const summary = typeof option.summary === 'string' ? option.summary : 'Strategy profile available.'
    const timelineYears = typeof option.timeline_years === 'number' ? option.timeline_years : null
    const timeline =
      typeof option.timeline === 'string'
        ? option.timeline
        : timelineYears !== null
          ? `${timelineYears}-year roadmap`
          : 'Roadmap available'
    const focus =
      typeof option.focus === 'string'
        ? option.focus
        : typeof option.recommendation === 'string'
          ? option.recommendation
          : 'Portfolio strategy optimization'

    return {
      id,
      name,
      summary,
      timeline,
      focus,
    }
  })
}

export const api = {
  async getGoogleOAuthState() {
    try {
      const { data } = await client.get('/auth/google/state')
      return unwrap<{ state: string; expires_in: number }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async me() {
    try {
      const { data } = await client.get('/auth/me')
      return unwrap<{ id: string; email: string; name?: string; picture?: string; role?: 'admin' | 'researcher' | 'viewer' }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async logout() {
    try {
      const { data } = await client.post('/auth/logout')
      return unwrap<{ success: boolean }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async refreshAccessToken() {
    try {
      const { data } = await client.post('/auth/refresh')
      const payload = unwrap<{ access_token: string }>(data)
      setAccessToken(payload.access_token)
      return payload
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async forgotPassword(email: string) {
    try {
      const { data } = await nodeClient.post('/auth/forgot-password', { email })
      return unwrap<{ success: boolean; message: string }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async loginWithGoogle(idToken: string) {
    try {
      const oauthState = await api.getGoogleOAuthState()
      const { data } = await client.post('/auth/google/verify', { idToken, state: oauthState.state })
      const payload = unwrap<{ access_token: string; user: { id: string; email: string; name?: string; picture?: string; role?: 'admin' | 'researcher' | 'viewer' } }>(data)
      setAccessToken(payload.access_token)
      return { token: payload.access_token, user: payload.user }
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async loginWithEmail(email: string, password: string) {
    try {
      const { data } = await client.post('/auth/login', { email, password })
      const payload = unwrap<{ access_token?: string; user?: { id: string; email: string; name?: string; picture?: string; role?: 'admin' | 'researcher' | 'viewer' }; mfa_required?: boolean; mfa_session_token?: string }>(data)
      if (payload.mfa_required) {
        return { token: '', user: { id: '', email }, mfa_required: true, mfa_session_token: payload.mfa_session_token }
      }
      const token = payload.access_token ?? ''
      setAccessToken(token)
      return { token, user: payload.user ?? { id: '', email } }
    } catch (error) {
      if (shouldRetryFlaskV1Auth(error)) {
        try {
          const { data } = await client.post('/v1/auth/login', { email, password })
          const payload = unwrap<{ access_token?: string; user?: { id: string; email: string; name?: string; picture?: string; role?: 'admin' | 'researcher' | 'viewer' }; mfa_required?: boolean; mfa_session_token?: string }>(data)
          if (payload.mfa_required) {
            return { token: '', user: { id: '', email }, mfa_required: true, mfa_session_token: payload.mfa_session_token }
          }
          const token = payload.access_token ?? ''
          setAccessToken(token)
          return { token, user: payload.user ?? { id: '', email } }
        } catch (retryError) {
          throw new Error(toErrorMessage(retryError))
        }
      }
      throw new Error(toErrorMessage(error))
    }
  },
  async registerWithEmail(name: string, email: string, password: string) {
    try {
      const { data } = await client.post('/auth/register', { name, email, password })
      const payload = unwrap<{ access_token: string; user: { id: string; email: string; name?: string; picture?: string; role?: 'admin' | 'researcher' | 'viewer' } }>(data)
      setAccessToken(payload.access_token)
      return { token: payload.access_token, user: payload.user }
    } catch (error) {
      if (shouldRetryFlaskV1Auth(error)) {
        try {
          const { data } = await client.post('/v1/auth/register', { name, email, password })
          const payload = unwrap<{ access_token: string; user: { id: string; email: string; name?: string; picture?: string; role?: 'admin' | 'researcher' | 'viewer' } }>(data)
          setAccessToken(payload.access_token)
          return { token: payload.access_token, user: payload.user }
        } catch (retryError) {
          throw new Error(toErrorMessage(retryError))
        }
      }
      throw new Error(toErrorMessage(error))
    }
  },
  async verifyMfaLogin(mfaSessionToken: string, code: string) {
    try {
      const { data } = await client.post('/auth/mfa/verify', { mfa_session_token: mfaSessionToken, code })
      const payload = unwrap<{ access_token: string; user: { id: string; email: string; name?: string; picture?: string; role?: 'admin' | 'researcher' | 'viewer' } }>(data)
      setAccessToken(payload.access_token)
      return { token: payload.access_token, user: payload.user }
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async setupMfa() {
    try {
      const { data } = await client.post('/auth/mfa/setup')
      return unwrap<{ secret: string; qr_code_base64: string; mfa_setup_token: string }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async verifyMfaSetup(code: string, mfaSetupToken: string) {
    try {
      const { data } = await client.post('/auth/mfa/verify-setup', { code, mfa_setup_token: mfaSetupToken })
      return unwrap<{ mfa_enabled: boolean }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminSystemHealth() {
    try {
      const { data } = await client.get('/admin/system-health')
      return unwrap<Record<string, unknown>>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminListUsers(query: AdminUserQuery = {}) {
    const { limit = 50, offset = 0, role, search } = query
    const params: Record<string, string | number> = { limit, offset }
    if (role && role !== 'all') {
      params.role = role
    }
    if (search) {
      params.search = search
    }
    try {
      const { data } = await client.get('/admin/users', { params })
      return unwrap<{
        items: Array<{ id: string; email: string; name: string; role: 'admin' | 'researcher' | 'viewer'; mfa_enabled?: boolean; created_at?: string; last_login?: string | null }>
        count: number
        limit: number
        offset: number
        total: number
      }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminUpdateUserRole(userId: string, role: 'admin' | 'researcher' | 'viewer') {
    try {
      const { data } = await client.patch(`/admin/users/${userId}/role`, { role })
      return unwrap<{ id: string; email: string; name: string; role: 'admin' | 'researcher' | 'viewer' }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminAuditLogs(query: AdminAuditQuery = {}) {
    const { limit = 100, offset = 0, method, status, path, requestId } = query
    const params: Record<string, string | number> = { limit, offset }
    if (method && method.toLowerCase() !== 'all') {
      params.method = method
    }
    if (status && status !== 'all') {
      params.status = typeof status === 'string' ? status : String(status)
    }
    if (path) {
      params.path = path
    }
    if (requestId) {
      params.request_id = requestId
    }
    try {
      const { data } = await client.get('/admin/audit-logs', { params })
      return unwrap<{
        items: Array<{ id: string; timestamp: string; method: string; path: string; status: number; request_id?: string | null }>
        count: number
        limit: number
        offset: number
        total: number
      }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminAnalyticsStats() {
    try {
      const { data } = await client.get('/admin/analytics/stats')
      return unwrap<AdminAnalyticsStats>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminAnalyticsModels() {
    try {
      const { data } = await client.get('/admin/analytics/models')
      return unwrap<AdminModelAnalytics>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminControlsOverview() {
    try {
      const { data } = await client.get('/admin/controls/overview')
      return unwrap<{
        approvals: { pending_count: number; items: AdminControlApproval[] }
        feature_flags: Record<string, { enabled: boolean; description?: string }>
        rollback_candidates: Array<Record<string, unknown>>
      }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminControlsApprovals(status?: string) {
    try {
      const { data } = await client.get('/admin/controls/approvals', { params: status ? { status } : undefined })
      return unwrap<{ items: AdminControlApproval[]; count: number }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminControlsDecision(approvalId: string, decision: AdminApprovalDecision) {
    try {
      const { data } = await client.post(`/admin/controls/approvals/${approvalId}`, { decision })
      return unwrap<AdminControlApproval>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminControlsFeatureFlags() {
    try {
      const { data } = await client.get('/admin/controls/feature-flags')
      return unwrap<{ items: AdminFeatureFlag[]; count: number }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminControlsUpdateFeatureFlag(flagKey: string, payload: { enabled?: boolean; description?: string }) {
    try {
      const { data } = await client.patch(`/admin/controls/feature-flags/${flagKey}`, payload)
      return unwrap<AdminFeatureFlag>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminControlsModels(limit = 20) {
    try {
      const { data } = await client.get('/admin/controls/models', { params: { limit } })
      return unwrap<{ items: Array<Record<string, unknown>>; count: number; limit: number }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async adminControlsRollback(version: string, reason: string) {
    try {
      const { data } = await client.post('/admin/controls/models/rollback', { version, reason })
      return unwrap<{ accepted: boolean; version: string; event: AdminControlApproval }>(data)
    } catch (error) {
      throw new Error(toErrorMessage(error))
    }
  },
  async predict(payload: FeatureSet & { compound_name?: string }): Promise<PredictionResponse> {
    try {
      return await safePost('/predict', payload, predictResponseRuntimeSchema) as PredictionResponse
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async predictTA(payload: FeatureSet & { therapeutic_area: TherapeuticArea; compare_all?: boolean }) {
    try {
      return await safePost('/predict-ta', payload, z.record(z.string(), z.unknown()))
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async predictSmiles(smiles: string, compound_name: string) {
    try {
      return await safePost('/predict-smiles', { smiles, compound_name }, z.record(z.string(), z.unknown()))
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async counterfactual(payload: FeatureSet & { target_probability: number }): Promise<CounterfactualResponse> {
    try {
      return await safePost('/counterfactual', payload, z.record(z.string(), z.unknown())) as CounterfactualResponse
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async history(): Promise<HistoryRecord[]> {
    try {
      return await safeGet('/history', historyRuntimeSchema) as HistoryRecord[]
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async stats() {
    const { data } = await client.get('/stats')
    return unwrap<Record<string, unknown>>(data)
  },
  async scenarios(): Promise<Scenario[]> {
    try {
      return await safeGet('/scenarios', scenariosRuntimeSchema) as Scenario[]
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async saveScenario(payload: { name: string; inputs: FeatureSet; outputs: Record<string, unknown>; tags: string[] }) {
    try {
      return await safePost('/scenarios', payload, z.record(z.string(), z.unknown()))
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async deleteScenario(id: string) {
    const { data } = await client.delete(`/scenarios/${id}`)
    return unwrap<Record<string, unknown>>(data)
  },
  async financialNPV(payload: Record<string, number>) {
    const { data } = await client.post('/financial/npv', payload)
    return unwrap<Record<string, unknown>>(data)
  },
  async financialSensitivity(payload: Record<string, unknown>) {
    const { data } = await client.post('/financial/sensitivity', payload)
    return unwrap<Record<string, unknown>>(data)
  },
  async modelInfo() {
    const { data } = await client.get('/model/info')
    return unwrap<Record<string, unknown>>(data)
  },
  async strategyOptions(): Promise<StrategyOptionsResponse> {
    try {
      return await safeGet('/strategy/options', strategyOptionsRuntimeSchema) as StrategyOptionsResponse
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async competitiveLandscape(): Promise<CompetitiveLandscape> {
    try {
      return await safeGet('/strategy/competitive-landscape', competitiveLandscapeRuntimeSchema) as CompetitiveLandscape
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async regulatoryTimeline(): Promise<{ timeline: RegulatoryMilestone[] }> {
    try {
      return await safeGet('/strategy/regulatory-timeline', regulatoryTimelineRuntimeSchema) as { timeline: RegulatoryMilestone[] }
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async partnerships(): Promise<{ partners: PartnershipItem[] }> {
    try {
      return await safeGet('/strategy/partnerships', partnershipsRuntimeSchema) as { partners: PartnershipItem[] }
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async roadmap(): Promise<{ roadmap: RoadmapPhase[] }> {
    try {
      return await safeGet('/strategy/roadmap', roadmapRuntimeSchema) as { roadmap: RoadmapPhase[] }
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async marketSizing(): Promise<MarketSizingResponse> {
    try {
      return await safeGet('/strategy/market-sizing', marketSizingRuntimeSchema) as MarketSizingResponse
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async riskRegister(): Promise<RiskRegisterResponse> {
    try {
      return await safeGet('/strategy/risk-register', riskRegisterRuntimeSchema) as RiskRegisterResponse
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async financialDetail() {
    const { data } = await client.get('/strategy/financial-detail')
    return unwrap<Record<string, unknown>>(data)
  },
  async executiveSummary() {
    try {
      return await safeGet('/strategy/executive-summary', executiveSummaryRuntimeSchema)
    } catch (error) {
      handleShapeMismatch(error)
      throw new Error(toErrorMessage(error))
    }
  },
  async nexusStrategies() {
    try {
      const { data } = await nodeClient.get('/strategies')
      const parsed = strategyFeedRuntimeSchema.safeParse(unwrap<unknown>(data))
      if (parsed.success) {
        return parsed.data
      }
      throw new Error('Unexpected strategy feed shape from node backend')
    } catch {
      const strategyOptions = await safeGet('/strategy/options', strategyOptionsRuntimeSchema)
      return {
        options: normalizeStrategyFeedOptions(strategyOptions.options),
      }
    }
  },
  async nexusAnalysis(payload: Record<string, string>) {
    const { data } = await nodeClient.post('/analysis', payload)
    return unwrap<{
      betterOption: string
      rationale: string
      riskNote: string
    }>(data)
  },
  async nexusContact(payload: { name: string; email: string; company: string; message: string }) {
    const { data } = await nodeClient.post('/contact', payload)
    return unwrap<{ success: boolean; message: string }>(data)
  }
}
