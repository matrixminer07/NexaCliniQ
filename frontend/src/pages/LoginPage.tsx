import React, { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { CredentialResponse, GoogleLogin } from '@react-oauth/google'
import { api } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'

type TabType = 'login' | 'register'

interface FormState {
  email: string
  password: string
  name?: string
  confirmPassword?: string
}

interface LoginResult {
  token: string
  user: {
    id: string
    email: string
    name?: string
    picture?: string
    role?: 'admin' | 'researcher' | 'viewer'
  }
  mfa_required?: boolean
  mfa_session_token?: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const locationState = (location.state as { tab?: string; from?: { pathname?: string } } | null) ?? null
  const redirectPath = locationState?.from?.pathname || '/app'
  const { login, isAuthenticated, loading: authLoading } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [mfaSessionToken, setMfaSessionToken] = useState<string | null>(null)
  const [mfaCode, setMfaCode] = useState('')
  const [mfaEmail, setMfaEmail] = useState('')
  const [googleLoginAvailable, setGoogleLoginAvailable] = useState(false)
  const [formData, setFormData] = useState<FormState>({
    email: '',
    password: '',
    name: '',
    confirmPassword: '',
  })

  const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined)?.trim() ?? ''
  const googleOAuthConfigured = Boolean(googleClientId) && !googleClientId.startsWith('your-google-client-id')

  // Redirect authenticated users away from login page.
  useEffect(() => {
    if (locationState?.tab === 'register') {
      setActiveTab('register')
    }
    if (!authLoading && isAuthenticated) {
      navigate(redirectPath, { replace: true })
    }
  }, [authLoading, isAuthenticated, locationState, navigate, redirectPath])

  useEffect(() => {
    let cancelled = false

    async function checkGoogleAvailability() {
      if (!googleOAuthConfigured) {
        if (!cancelled) setGoogleLoginAvailable(false)
        return
      }

      try {
        const state = await api.getGoogleOAuthState()
        if (!cancelled) setGoogleLoginAvailable(state.configured !== false && Boolean(state.state))
      } catch {
        if (!cancelled) setGoogleLoginAvailable(false)
      }
    }

    void checkGoogleAvailability()

    return () => {
      cancelled = true
    }
  }, [googleOAuthConfigured])


  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
    setError('')
  }

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    const normalizedEmail = formData.email.trim().toLowerCase()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError('Please enter a valid email address.')
      setLoading(false)
      return
    }

    try {
      const data = (await api.loginWithEmail(normalizedEmail, formData.password)) as LoginResult
      if (data.mfa_required) {
        setMfaSessionToken(data.mfa_session_token ?? null)
        setMfaEmail(normalizedEmail)
        setMfaCode('')
        return
      }
      login(data.token, data.user)
      navigate(redirectPath, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleMfaVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!mfaSessionToken) {
      setError('MFA session expired. Please sign in again.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await api.verifyMfaLogin(mfaSessionToken, mfaCode)
      login(data.token, data.user)
      setMfaSessionToken(null)
      setMfaCode('')
      navigate(redirectPath, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid MFA code. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const resetMfaFlow = () => {
    setMfaSessionToken(null)
    setMfaCode('')
    setMfaEmail('')
    setError('')
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    try {
      const data = await api.registerWithEmail(formData.name || '', formData.email, formData.password)
      login(data.token, data.user)
      navigate(redirectPath, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    const idToken = credentialResponse.credential
    if (!idToken) {
      setError('Google authentication failed: missing ID token')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await api.loginWithGoogle(idToken)
      login(data.token, data.user)
      navigate(redirectPath, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google authentication failed. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }


  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Video Background - Landscape Fill */}
      <video
        autoPlay
        muted
        loop
        className="absolute inset-0 w-full h-full object-cover scale-110 md:scale-105 [filter:brightness(1.22)_contrast(1.18)_saturate(1.28)]"
      >
        <source src="/loginvideo.mp4" type="video/mp4" />
      </video>

      {/* Dark Overlay for Content Readability */}
      <div className="absolute inset-0 bg-black/18 dark:bg-black/28"></div>

      {/* Content Container */}
      <div className="relative z-20 flex min-h-screen">
        {/* Left Panel - Brand (hidden on mobile) */}
        <div className="hidden md:flex md:w-[55%] bg-gradient-to-br from-[rgba(6,15,35,0.85)] to-[rgba(10,22,40,0.85)] flex-col justify-between p-12 backdrop-blur-sm">
          {/* Logo and Wordmark */}
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl overflow-hidden ring-2 ring-blue-300/40 shadow-[0_0_30px_rgba(37,99,235,0.65)] bg-white/10">
              <img
                src="/logo.png"
                alt="NEXUSCLINIQ logo"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="text-white font-semibold text-3xl tracking-[0.08em] drop-shadow-[0_0_14px_rgba(37,99,235,0.35)]">
              NEXUSCLIN<span className="text-blue-600">I</span>Q
            </div>
          </div>

          {/* Hero Section */}
          <div className="flex-1 flex flex-col justify-center">
            <p className="text-blue-400 font-semibold text-xs uppercase tracking-widest mb-6">
              Clinical intelligence platform
            </p>
            <h1 className="text-white font-medium text-4xl leading-normal mb-6 max-w-sm">
              Redefining how discoveries become cures
            </h1>
            <p className="text-gray-200 text-sm leading-relaxed max-w-sm mb-8">
              From compound screening to portfolio decisions — NEXUSCLINIQ brings AI precision to every stage of drug development.
            </p>

            {/* Features List */}
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-1 h-1 rounded-full bg-blue-400 mt-2 flex-shrink-0"></div>
                <span className="text-gray-200 text-sm">AI-powered success probability scoring</span>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-1 h-1 rounded-full bg-blue-400 mt-2 flex-shrink-0"></div>
                <span className="text-gray-200 text-sm">SHAP explainability on every prediction</span>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-1 h-1 rounded-full bg-blue-400 mt-2 flex-shrink-0"></div>
                <span className="text-gray-200 text-sm">Audit-ready logs and governance tools</span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <p className="text-gray-400 text-xs">© 2025 NEXUSCLINIQ. Research use only.</p>
        </div>

        {/* Right Panel - Form */}
        <div className="w-full md:w-[45%] bg-gradient-to-br from-[rgba(15,23,42,0.85)] to-[rgba(30,41,59,0.85)] flex items-center justify-center p-6 backdrop-blur-sm">
          <div className="w-full max-w-sm">
            {/* Form Header */}
            <h2 className="text-white font-medium text-2xl mb-2">
              Welcome back
            </h2>
            <p className="text-gray-200 text-sm mb-8">
              Sign in to your NEXUSCLINIQ workspace
            </p>
            {activeTab === 'login' && (
              <button
                type="button"
                onClick={() => setActiveTab('register')}
                className="mb-6 inline-flex items-center rounded-full border border-blue-300/40 bg-blue-500/20 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-blue-100 transition-colors hover:bg-blue-500/30"
              >
                New here? Sign up
              </button>
            )}

            {mfaSessionToken ? (
              <form onSubmit={handleMfaVerify} className="space-y-4">
                <div className="rounded-xl border border-blue-400/40 bg-blue-500/10 p-4 text-sm text-blue-100">
                  Enter the 6-digit MFA code for {mfaEmail || 'your account'}.
                </div>

                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={mfaCode}
                  onChange={(e) => {
                    setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))
                    setError('')
                  }}
                  placeholder="123456"
                  className="w-full rounded-lg border border-white/30 bg-white/10 px-4 py-3 text-white placeholder:text-gray-300 outline-none focus:border-blue-400"
                  required
                />

                {error && (
                  <div className="rounded-lg border border-red-400/40 bg-red-500/20 p-3 text-sm text-red-100">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || mfaCode.length !== 6}
                  className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Verifying code...' : 'Verify and continue'}
                </button>

                <button
                  type="button"
                  onClick={resetMfaFlow}
                  className="w-full rounded-lg border border-white/30 bg-white/5 px-4 py-3 text-sm font-medium text-gray-200 transition hover:bg-white/10"
                >
                  Back to sign in
                </button>
              </form>
            ) : (
              <>
            {/* Google Button */}
            <div className="mb-6 flex justify-center">
              {googleLoginAvailable ? (
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => setError('Google authentication failed')}
                  theme="filled_blue"
                  size="large"
                  text="continue_with"
                  shape="rectangular"
                  width="320"
                />
              ) : (
                <div className="w-full p-3 bg-amber-500/20 border border-amber-400/50 rounded-lg backdrop-blur">
                  <p className="text-amber-100 text-sm">
                    Google sign-in is not configured. Use email/password sign-in.
                  </p>
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/20"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-2 bg-gradient-to-br from-[rgba(15,23,42,0.85)] to-[rgba(30,41,59,0.85)] text-gray-300">
                  or continue with email
                </span>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-6 mb-6 border-b border-white/20">
              <button
                onClick={() => setActiveTab('login')}
                className={`pb-3 text-sm font-medium transition-colors ${
                  activeTab === 'login'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-300 hover:text-gray-200'
                }`}
              >
                Sign in
              </button>
              <button
                onClick={() => setActiveTab('register')}
                className={`pb-3 text-sm font-medium transition-colors ${
                  activeTab === 'register'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-300 hover:text-gray-200'
                }`}
              >
                Sign up
              </button>
            </div>

            {/* Form Content */}
              </>
            )}
            {!mfaSessionToken && (
            <form onSubmit={activeTab === 'login' ? handleEmailLogin : handleRegister}>
              {/* Register - Full Name */}
              {activeTab === 'register' && (
                <div className="mb-4">
                  <label className="block text-gray-200 text-xs font-semibold uppercase tracking-wide mb-2">
                    Full name
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required={activeTab === 'register'}
                    placeholder="John Doe"
                    className="w-full h-9 px-3 border border-white/20 rounded-lg bg-white/10 backdrop-blur text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                </div>
              )}

              {/* Email */}
              <div className="mb-4">
                <label className="block text-gray-200 text-xs font-semibold uppercase tracking-wide mb-2">
                  Work email
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  placeholder="you@organization.com"
                  className="w-full h-9 px-3 border border-white/20 rounded-lg bg-white/10 backdrop-blur text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </div>

              {/* Password */}
              <div className="mb-4">
                <label className="block text-gray-200 text-xs font-semibold uppercase tracking-wide mb-2">
                  Password
                </label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                  placeholder="••••••••"
                  className="w-full h-9 px-3 border border-white/20 rounded-lg bg-white/10 backdrop-blur text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                {activeTab === 'login' && (
                  <div className="text-right mt-2">
                    <a href="#" className="text-blue-400 text-xs hover:text-blue-300 transition-colors">
                      Forgot password?
                    </a>
                  </div>
                )}
              </div>

              {/* Register - Confirm Password */}
              {activeTab === 'register' && (
                <div className="mb-4">
                  <label className="block text-gray-200 text-xs font-semibold uppercase tracking-wide mb-2">
                    Confirm password
                  </label>
                  <input
                    type="password"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    required={activeTab === 'register'}
                    placeholder="••••••••"
                    className="w-full h-9 px-3 border border-white/20 rounded-lg bg-white/10 backdrop-blur text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="mb-4 p-3 bg-red-500/20 border border-red-400/50 rounded-lg backdrop-blur">
                  <p className="text-red-200 text-sm">{error}</p>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full h-10 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg text-sm transition-colors disabled:opacity-70 flex items-center justify-center"
              >
                {loading ? (
                  <svg
                    className="animate-spin h-4 w-4"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                ) : activeTab === 'login' ? (
                  'Sign in to NexusCliQ'
                ) : (
                  'Create your account'
                )}
              </button>
            </form>
            )}

            {/* Footer Disclaimer */}
            <p className="text-center text-gray-300 text-xs leading-relaxed mt-6">
              By continuing, you agree to NEXUSCLINIQ's Terms of Use and Privacy Policy.
              <br />
              Not intended for clinical decision-making.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
