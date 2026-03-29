import { ZodSchema } from 'zod'
import axios from 'axios'

function normalizeApiBase(raw: string | undefined): string {
  const fallback = 'http://localhost:5000/api/v1'
  if (!raw) return fallback
  const trimmed = raw.replace(/\/$/, '')
  if (trimmed.startsWith('/')) return trimmed
  if (/\/api(?:\/v\d+)?(?:\/|$)/i.test(trimmed)) return trimmed
  return `${trimmed}/api/v1`
}

const BASE = normalizeApiBase(import.meta.env.VITE_API_URL as string | undefined)

function getToken() {
  return sessionStorage.getItem('access_token')
}

function authHeaders() {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export async function safeGet<T>(path: string, schema: ZodSchema<T>): Promise<T> {
  const res = await axios.get(`${BASE}${path}`, { headers: authHeaders() })
  const parsed = schema.safeParse(res.data?.data ?? res.data)
  if (!parsed.success) {
    console.error('[Shape mismatch]', path, parsed.error.flatten())
    throw new Error(`Unexpected response shape from ${path}`)
  }
  return parsed.data
}

export async function safePost<T>(path: string, body: unknown, schema: ZodSchema<T>): Promise<T> {
  const res = await axios.post(`${BASE}${path}`, body, { headers: authHeaders() })
  const parsed = schema.safeParse(res.data?.data ?? res.data)
  if (!parsed.success) {
    console.error('[Shape mismatch]', path, parsed.error.flatten())
    throw new Error(`Unexpected response shape from ${path}`)
  }
  return parsed.data
}
