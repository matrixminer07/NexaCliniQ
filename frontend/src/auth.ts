const AUTH_USER_KEY = 'pharma_nexus_auth_user'
const AUTH_REFRESH_TOKEN_KEY = 'pharma_nexus_auth_refresh_token'
const AUTH_ACCESS_TOKEN_KEY = 'pharma_nexus_auth_access_token'
let accessTokenMemory: string | null = null
let refreshTokenMemory: string | null = null

export type AuthUser = {
  id?: string
  email: string
  name?: string
  picture?: string
  role?: 'admin' | 'researcher' | 'viewer'
}

export function setAuthSession(token: string, user: AuthUser, refreshToken?: string | null) {
  accessTokenMemory = token
  sessionStorage.setItem(AUTH_ACCESS_TOKEN_KEY, token)
  sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
  if (typeof refreshToken === 'string' && refreshToken) {
    refreshTokenMemory = refreshToken
    localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, refreshToken)
  }
}

export function clearAuthSession() {
  accessTokenMemory = null
  refreshTokenMemory = null
  sessionStorage.removeItem(AUTH_ACCESS_TOKEN_KEY)
  sessionStorage.removeItem(AUTH_USER_KEY)
  localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY)
}

export function getAuthToken() {
  if (accessTokenMemory) return accessTokenMemory
  const stored = sessionStorage.getItem(AUTH_ACCESS_TOKEN_KEY)
  if (!stored) return null
  accessTokenMemory = stored
  return stored
}

export function setAccessToken(token: string | null) {
  accessTokenMemory = token
  if (token) {
    sessionStorage.setItem(AUTH_ACCESS_TOKEN_KEY, token)
  } else {
    sessionStorage.removeItem(AUTH_ACCESS_TOKEN_KEY)
  }
}

export function setRefreshToken(token: string | null) {
  refreshTokenMemory = token
  if (token) {
    localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY)
  }
}

export function getRefreshToken() {
  if (refreshTokenMemory) return refreshTokenMemory
  const stored = localStorage.getItem(AUTH_REFRESH_TOKEN_KEY)
  if (!stored) return null
  refreshTokenMemory = stored
  return stored
}

export function isAuthenticated() {
  return Boolean(accessTokenMemory)
}

export function getAuthenticatedUser() {
  const raw = sessionStorage.getItem(AUTH_USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}