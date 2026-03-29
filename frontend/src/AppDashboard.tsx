import { Suspense, lazy, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/store'
import { Sidebar } from '@/components/Sidebar'
import { LiveMetricsHeader } from '@/components/LiveMetricsHeader'
import { useAuth } from '@/contexts/AuthContext'

const PredictTab = lazy(() => import('@/pages/PredictTab').then((m) => ({ default: m.PredictTab })))
const CompareTab = lazy(() => import('@/pages/CompareTab').then((m) => ({ default: m.CompareTab })))
const StrategyTab = lazy(() => import('@/pages/StrategyTab').then((m) => ({ default: m.StrategyTab })))
const MarketSizingTab = lazy(() => import('@/pages/MarketSizingTab').then((m) => ({ default: m.MarketSizingTab })))
const RiskRegisterTab = lazy(() => import('@/pages/RiskRegisterTab').then((m) => ({ default: m.RiskRegisterTab })))
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

export function AppDashboard() {
  const navigate = useNavigate()
  const tab = useAppStore((s) => s.currentTab)
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const setSidebarOpen = useAppStore((s) => s.setSidebarOpen)
  const { user, logout } = useAuth()
  const isAdmin = String(user?.role ?? '').toLowerCase() === 'admin'

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const page = useMemo(() => {
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

  return (
    <div className="min-h-screen bg-surface-base text-ink-primary" data-theme="novacura">
      <button
        className="md:hidden fixed z-30 top-4 left-4 btn-ghost"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle sidebar"
      >
        Menu
      </button>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 md:pl-8 pl-16">
          <div className="max-w-[1400px] mx-auto space-y-6 animate-fade-in">
            <div className="card-p flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-ink-tertiary">Authenticated Workspace</p>
                <p className="text-sm text-ink-secondary">{user?.email ?? 'Signed in user'}</p>
              </div>
              <div className="flex items-center gap-2">
                {isAdmin ? (
                  <button
                    type="button"
                    className="rounded-[8px] px-[14px] py-[6px] text-[13px] text-ink-secondary transition-colors hover:bg-[#F8FAFC]"
                    style={{ border: '0.5px solid #E2E8F0' }}
                    onClick={() => navigate('/admin-site')}
                  >
                    Admin Console
                  </button>
                ) : null}
                <button
                  type="button"
                  className="rounded-[8px] px-[14px] py-[6px] text-[13px] text-ink-secondary transition-colors hover:bg-[#F8FAFC]"
                  style={{ border: '0.5px solid #E2E8F0' }}
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </div>
            </div>
            <LiveMetricsHeader />
            <Suspense
              fallback={(
                <div className="card-p flex items-center gap-3">
                  <div className="dna-loader" />
                  <span className="text-sm text-ink-secondary">Loading module...</span>
                </div>
              )}
            >
              {page}
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  )
}
