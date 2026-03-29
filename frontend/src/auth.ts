const AUTH_USER_KEY = 'pharma_nexus_auth_user'
let accessTokenMemory: string | null = null

export type AuthUser = {
  id?: string
  email: string
  name?: string
  picture?: string
  role?: 'admin' | 'researcher' | 'viewer'
}

export function setAuthSession(token: string, user: AuthUser) {
  accessTokenMemory = token
  sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

export function clearAuthSession() {
  accessTokenMemory = null
  sessionStorage.removeItem(AUTH_USER_KEY)
}

export function getAuthToken() {
  return accessTokenMemory
}

export function setAccessToken(token: string | null) {
  accessTokenMemory = token
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