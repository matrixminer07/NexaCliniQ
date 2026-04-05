import { Component, Suspense, lazy, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/store'
import { Sidebar } from '@/components/Sidebar'
import { TabShell } from '@/components/TabShell'
import { PageErrorBoundary } from '@/components/PageErrorBoundary'
import { useAuth } from '@/contexts/AuthContext'
import { useSocketLiveStats } from '@/services/socket'
import type { TabKey } from '@/types'
import { MarketSizingTab } from '@/pages/MarketSizingTab'
import { RiskRegisterTab } from '@/pages/RiskRegisterTab'

const PredictTab = lazy(() => import('@/pages/PredictTab').then((m) => ({ default: m.PredictTab })))
const CompareTab = lazy(() => import('@/pages/CompareTab').then((m) => ({ default: m.CompareTab })))
const StrategyTab = lazy(() => import('@/pages/StrategyTab').then((m) => ({ default: m.StrategyTab })))
const FinancialDetailTab = lazy(() => import('@/pages/FinancialDetailTab').then((m) => ({ default: m.FinancialDetailTab })))
const ExecutiveSummaryTab = lazy(() => import('@/pages/ExecutiveSummaryTab').then((m) => ({ default: m.ExecutiveSummaryTab })))
const CompetitiveTab = lazy(() => import('@/pages/CompetitiveTab').then((m) => ({ default: m.CompetitiveTab })))
const RegulatoryTab = lazy(() => import('@/pages/RegulatoryTab').then((m) => ({ default: m.RegulatoryTab })))
const PartnershipsTab = lazy(() => import('@/pages/PartnershipsTab').then((m) => ({ default: m.PartnershipsTab })))
const RoadmapTab = lazy(() => import('@/pages/RoadmapTab').then((m) => ({ default: m.RoadmapTab })))
const PipelineTab = lazy(() => import('@/pages/PipelineTab').then((m) => ({ default: m.PipelineTab })))
const HistoryTab = lazy(() => import('@/pages/HistoryTab').then((m) => ({ default: m.HistoryTab })))
const ScenariosTab = lazy(() => import('@/pages/ScenariosTab').then((m) => ({ default: m.ScenariosTab })))
const FinancialTab = lazy(() => import('@/pages/FinancialTab').then((m) => ({ default: m.FinancialTab })))

const tabTitles: Record<TabKey, string> = {
  predict: 'Predict',
  compare: 'Compare',
  strategy: 'Strategy',
  'market-sizing': 'Market Sizing',
  'risk-register': 'Risk Register',
  'financial-detail': 'Financial Detail',
  'executive-summary': 'Executive Summary',
  competition: 'Competition',
  regulatory: 'Regulatory',
  partnerships: 'Partnerships',
  roadmap: 'Roadmap',
  pipeline: 'Pipeline',
  history: 'History',
  scenarios: 'Scenarios',
  financial: 'Budget',
}

const apiDrivenTabs = new Set<TabKey>([
  'predict',
  'scenarios',
  'executive-summary',
  'market-sizing',
  'risk-register',
  'roadmap',
  'financial-detail',
  'history',
])

class TabErrorBoundary extends Component<{
  resetKey: string
  onError: (error: unknown) => void
  children: React.ReactNode
}, {
  hasError: boolean
}> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: unknown) {
    this.props.onError(error)
  }

  componentDidUpdate(prevProps: Readonly<{ resetKey: string }>) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false })
    }
  }

  render() {
    if (this.state.hasError) {
      return null
    }
    return this.props.children
  }
}

function getInitials(name: string | null | undefined): string {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return 'U'
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? '').join('')
}

function getErrorInfo(error: unknown): { message: string; is401: boolean } {
  const fallback = { message: 'An unexpected error occurred while rendering this module.', is401: false }
  if (!error || typeof error !== 'object') return fallback
  const maybeError = error as { message?: string; response?: { status?: number }; status?: number }
  const status = maybeError.response?.status ?? maybeError.status
  return {
    message: maybeError.message || fallback.message,
    is401: status === 401,
  }
}

export function AppDashboard() {
  const navigate = useNavigate()
  const tab = useAppStore((s) => s.currentTab)
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const setSidebarOpen = useAppStore((s) => s.setSidebarOpen)
  const totalAnalysed = useAppStore((s) => s.totalAnalysed)
  const passRate = useAppStore((s) => s.passRate)
  const { user, logout } = useAuth()
  const isAdmin = String(user?.role ?? '').toLowerCase() === 'admin'
  const [tabError, setTabError] = useState<string | null>(null)
  const [tabError401, setTabError401] = useState(false)
  const [retryTick, setRetryTick] = useState(0)
  const [tabSwitchLoading, setTabSwitchLoading] = useState(false)

  useSocketLiveStats()

  useEffect(() => {
    setTabError(null)
    setTabError401(false)
    if (!apiDrivenTabs.has(tab)) {
      setTabSwitchLoading(false)
      return
    }
    setTabSwitchLoading(true)
    const timeout = window.setTimeout(() => setTabSwitchLoading(false), 450)
    return () => window.clearTimeout(timeout)
  }, [tab])

  function onRetry() {
    setTabError(null)
    setTabError401(false)
    setRetryTick((value) => value + 1)
  }

  function onRenderError(error: unknown) {
    const details = getErrorInfo(error)
    setTabError(details.message)
    setTabError401(details.is401)
  }

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const page = useMemo<React.ReactNode>(() => {
    switch (tab) {
      case 'predict':
        return <PredictTab />
      case 'compare':
        return <CompareTab />
      case 'strategy':
        return <StrategyTab />
      case 'market-sizing':
        return <MarketSizingTab />
      case 'risk-register':
        return <RiskRegisterTab />
      case 'financial-detail':
        return <FinancialDetailTab />
      case 'executive-summary':
        return <ExecutiveSummaryTab />
      case 'competition':
        return <CompetitiveTab />
      case 'regulatory':
        return <RegulatoryTab />
      case 'partnerships':
        return <PartnershipsTab />
      case 'roadmap':
        return <RoadmapTab />
      case 'pipeline':
        return <PipelineTab />
      case 'history':
        return <HistoryTab />
      case 'scenarios':
        return <ScenariosTab />
      case 'financial':
        return <FinancialTab />
      default:
        return <PredictTab />
    }
  }, [tab])

  const normalizedTab: TabKey = tabTitles[tab] ? tab : 'predict'
  const title = tabTitles[normalizedTab]
  const content = (
    <TabShell
      isLoading={apiDrivenTabs.has(normalizedTab) ? tabSwitchLoading : false}
      error={tabError}
      is401={tabError401}
      onRetry={onRetry}
    >
      <TabErrorBoundary resetKey={`${normalizedTab}-${retryTick}`} onError={onRenderError}>
        <Suspense
          fallback={(
            <TabShell isLoading>
              <div className="h-20" />
            </TabShell>
          )}
        >
          <PageErrorBoundary pageName={title}>
            {page}
          </PageErrorBoundary>
        </Suspense>
      </TabErrorBoundary>
    </TabShell>
  )

  return (
    <div
      className="pn-app-shell relative min-h-screen overflow-hidden bg-surface-base text-ink-primary"
      data-theme="novacura"
      style={{
        ['--sidebar-width' as string]: '220px',
        ['--topbar-height' as string]: '72px',
        ['--accent-purple' as string]: '#7F77DD',
        ['--dot-api' as string]: '#1D9E75',
        ['--dot-static' as string]: '#888780',
        ['--dot-live' as string]: '#D85A30',
      }}
    >
      <video
        className="pointer-events-none fixed inset-0 h-full w-full object-cover object-center scale-[1.03] opacity-35"
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        aria-hidden="true"
        disablePictureInPicture
      >
        <source src="/videos/video4.mp4" type="video/mp4" />
      </video>
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(127,119,221,0.20),transparent_34%),radial-gradient(circle_at_85%_10%,rgba(29,158,117,0.16),transparent_30%),linear-gradient(180deg,rgba(6,10,20,0.62)_0%,rgba(6,10,20,0.78)_100%)]" />
      <button
        className="md:hidden fixed z-50 top-2 left-2 px-3 py-1.5 text-xs rounded border border-line bg-surface-base/70 backdrop-blur"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle sidebar"
      >
        Menu
      </button>
      <div className="relative z-10 flex min-h-screen">
        <Sidebar />
        <div className="flex-1 md:ml-[var(--sidebar-width)]">
          <header className="pn-topbar-shell fixed top-0 right-0 left-0 md:left-[var(--sidebar-width)] h-[var(--topbar-height)] z-30">
            <div className="h-full px-5 md:px-6 flex items-center justify-between gap-4">
              <div className="min-w-0 flex items-center gap-3 md:gap-4">
                <div className="hidden md:block h-8 w-[3px] rounded-full bg-gradient-to-b from-cyan-300 via-indigo-400 to-emerald-300 opacity-90" />
                <div className="min-w-0">
                  <p className="pn-topbar-kicker">Decision Workspace</p>
                  <h1 className="pn-topbar-title truncate">{title}</h1>
                </div>
                <div className="hidden xl:flex items-center gap-2 text-[11px]">
                  <span className="pn-stat-pill inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5">
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: 'var(--dot-api)' }} />
                    <span className="text-ink-tertiary">Predictions</span>
                    <span className="font-semibold text-ink-primary">{totalAnalysed.toLocaleString()}</span>
                  </span>
                  <span className="pn-stat-pill inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-state-caution" />
                    <span className="text-ink-tertiary">Accuracy</span>
                    <span className="font-semibold text-ink-primary">{passRate.toFixed(1)}%</span>
                  </span>
                  <span className="pn-stat-pill inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full rounded-full animate-ping opacity-75" style={{ backgroundColor: 'var(--dot-live)' }} />
                      <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: 'var(--dot-live)' }} />
                    </span>
                    <span className="font-semibold text-ink-primary">Live</span>
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isAdmin ? (
                  <button
                    type="button"
                    className="pn-admin-btn rounded-md px-3 py-1.5 text-xs border"
                    onClick={() => navigate('/admin-site')}
                  >
                    Admin Console
                  </button>
                ) : null}
                <button
                  type="button"
                  className="pn-admin-btn rounded-md px-3 py-1.5 text-xs border"
                  onClick={() => void onLogout()}
                >
                  Logout
                </button>
                <div className="pn-avatar h-8 w-8 rounded-full text-[11px] font-semibold inline-flex items-center justify-center" aria-label="User avatar">
                  {getInitials(user?.name)}
                </div>
              </div>
            </div>
          </header>
          <main className="h-screen pt-[var(--topbar-height)] overflow-auto p-5">
            {content}
          </main>
        </div>
      </div>
    </div>
  )
}
