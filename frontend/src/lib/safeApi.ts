import { ZodSchema } from 'zod'
import axios from 'axios'
import { clearAuthSession, getAuthToken, getRefreshToken, setAccessToken } from '@/auth'

function normalizeApiBase(raw: string | undefined): string {
  const fallback = import.meta.env.DEV ? 'http://127.0.0.1:5000/api' : '/api'
  if (!raw) return fallback
  const trimmed = raw.replace(/\/$/, '')
  if (trimmed.startsWith('/')) return trimmed
  if (/\/api\/v\d+(?:\/|$)/i.test(trimmed)) {
    return trimmed.replace(/\/api\/v\d+(?=\/|$)/i, '/api')
  }
  if (/\/api(?:\/|$)/i.test(trimmed)) return trimmed
  return `${trimmed}/api`
}

const BASE = normalizeApiBase(import.meta.env.VITE_API_URL as string | undefined)

function getToken() {
  return getAuthToken()
}

function authHeaders() {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

function pickAccessToken(payload: { access_token?: string; token?: string }): string {
  return payload.access_token ?? payload.token ?? ''
}

function unwrap<T>(data: unknown): T {
  if (typeof data === 'object' && data !== null && 'data' in data) {
    const maybe = data as { data: T }
    if (maybe.data !== null && maybe.data !== undefined) {
      return maybe.data
    }
  }
  return data as T
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  const { data } = await axios.post(
    `${BASE}/auth/refresh`,
    refreshToken ? { refresh_token: refreshToken } : {},
    { withCredentials: true, timeout: 12000 },
  )
  const payload = unwrap<{ access_token?: string; token?: string }>(data)
  const token = pickAccessToken(payload)
  setAccessToken(token || null)
  return token || null
}

async function requestWithAuthRetry(method: 'get' | 'post', path: string, body?: unknown) {
  const url = `${BASE}${path}`
  const makeRequest = (headers: Record<string, string>) =>
    axios.request({
      method,
      url,
      data: body,
      headers,
      withCredentials: true,
      timeout: 12000,
    })

  try {
    return await makeRequest(authHeaders())
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      try {
        const nextToken = await refreshAccessToken()
        if (nextToken) {
          return await makeRequest({ Authorization: `Bearer ${nextToken}` })
        }
      } catch {
        clearAuthSession()
      }
    }
    throw error
  }
}

export async function safeGet<T>(path: string, schema: ZodSchema<T>): Promise<T> {
  const res = await requestWithAuthRetry('get', path)
  const parsed = schema.safeParse(res.data?.data ?? res.data)
  if (!parsed.success) {
    console.error('[Shape mismatch]', path, parsed.error.flatten())
    throw new Error(`Unexpected response shape from ${path}`)
  }
  return parsed.data
}

export async function safePost<T>(path: string, body: unknown, schema: ZodSchema<T>): Promise<T> {
  const res = await requestWithAuthRetry('post', path, body)
  const parsed = schema.safeParse(res.data?.data ?? res.data)
  if (!parsed.success) {
    console.error('[Shape mismatch]', path, parsed.error.flatten())
    throw new Error(`Unexpected response shape from ${path}`)
  }
  return parsed.data
}
