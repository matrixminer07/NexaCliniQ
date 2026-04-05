import clsx from 'clsx'
import { useAppStore } from '@/store'
import type { TabKey } from '@/types'

type NavItem = {
  key: TabKey
  label: string
  isApiDriven: boolean
}

const navGroups: Array<{ label: string; items: NavItem[] }> = [
  {
    label: 'Prediction',
    items: [
      { key: 'predict', label: 'Predict', isApiDriven: true },
      { key: 'compare', label: 'Compare', isApiDriven: false },
    ],
  },
  {
    label: 'Strategy',
    items: [
      { key: 'executive-summary', label: 'Executive Summary', isApiDriven: true },
      { key: 'market-sizing', label: 'Market sizing', isApiDriven: true },
      { key: 'risk-register', label: 'Risk register', isApiDriven: true },
      { key: 'roadmap', label: 'Roadmap', isApiDriven: true },
      { key: 'regulatory', label: 'Regulatory', isApiDriven: false },
      { key: 'partnerships', label: 'Partnerships', isApiDriven: false },
      { key: 'strategy', label: 'Strategy', isApiDriven: false },
    ],
  },
  {
    label: 'Economics',
    items: [
      { key: 'financial', label: 'Budget', isApiDriven: false },
      { key: 'financial-detail', label: 'Financial detail', isApiDriven: true },
      { key: 'pipeline', label: 'Pipeline', isApiDriven: false },
    ],
  },
  {
    label: 'Records',
    items: [
      { key: 'history', label: 'History', isApiDriven: true },
    ],
  },
]

export function Sidebar() {
  const {
    currentTab,
    setCurrentTab,
    sidebarOpen,
    setSidebarOpen,
  } = useAppStore()

  const baseItemClasses = 'w-full text-left text-[14px] py-2 rounded-xl transition-all duration-200 hover:bg-surface-2/80 hover:text-ink-primary'

  return (
    <aside
      className={clsx(
        'fixed md:fixed z-40 top-0 left-0 h-screen w-[82vw] max-w-[320px] md:w-[var(--sidebar-width)] border-r border-line bg-surface-1 transition-transform duration-200 flex flex-col',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      )}
    >
      <div className="flex-1 overflow-y-auto px-2 py-3">
        {navGroups.map((group) => (
          <section key={group.label} className="mb-4">
            <h3 className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-tertiary">{group.label}</h3>
            <div>
              {group.items.map((item) => {
                const active = currentTab === item.key
                return (
                  <button
                    key={item.key}
                    type="button"
                    className={clsx(
                      baseItemClasses,
                      active
                        ? 'font-semibold border border-[rgba(127,119,221,0.45)] bg-[rgba(127,119,221,0.14)] px-3 text-ink-primary shadow-[0_8px_20px_rgba(24,32,70,0.35)]'
                        : 'border border-transparent px-3 font-medium text-ink-secondary'
                    )}
                    style={active ? { borderLeftColor: 'transparent' } : undefined}
                    onClick={() => {
                      setCurrentTab(item.key)
                      setSidebarOpen(false)
                    }}
                  >
                    <span className="inline-flex items-center gap-2.5">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: item.isApiDriven ? 'var(--dot-api)' : 'var(--dot-static)' }}
                      />
                      {item.label}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>
        ))}
      </div>

    </aside>
  )
}
