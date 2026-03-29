import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import { useAppStore } from '@/store'
import { CardSkeleton } from '@/components/skeletons/CardSkeleton'
import { useTabCache } from '@/hooks/useTabCache'
import type { Scenario } from '@/types'

export function ScenariosTab() {
  const setFeatureA = useAppStore((s) => s.setFeatureA)
  const setCurrentTab = useAppStore((s) => s.setCurrentTab)
  const [items, setItems] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const cache = useTabCache<Scenario[]>()

  const load = async (force = false) => {
    if (!force) {
      const cached = cache.get('scenarios-tab')
      if (cached) {
        setItems(cached)
        setError(null)
        setLoading(false)
        return
      }
    }

    try {
      setLoading(true)
      setError(null)
      const data = await api.scenarios()
      setItems(data)
      cache.set('scenarios-tab', data)
    } catch (e) {
      setItems([])
      setError(e instanceof Error ? e.message : 'Failed to load scenarios')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(false)
  }, [])

  const onDelete = async (id: string) => {
    try {
      await api.deleteScenario(id)
      setItems((prev) => prev.filter((scenario) => scenario.id !== id))
    } catch {
      // Keep current list if deletion fails.
    }
  }

  const onLoad = (scenario: Scenario) => {
    if (scenario.inputs) {
      if (typeof scenario.inputs.toxicity === 'number') setFeatureA('toxicity', scenario.inputs.toxicity)
      if (typeof scenario.inputs.bioavailability === 'number') setFeatureA('bioavailability', scenario.inputs.bioavailability)
      if (typeof scenario.inputs.solubility === 'number') setFeatureA('solubility', scenario.inputs.solubility)
      if (typeof scenario.inputs.binding === 'number') setFeatureA('binding', scenario.inputs.binding)
      if (typeof scenario.inputs.molecular_weight === 'number') setFeatureA('molecular_weight', scenario.inputs.molecular_weight)
    }
    setCurrentTab('predict')
  }

  return (
    <section className="space-y-4">
      <div className="card-p">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-display text-lg">Saved Scenarios</h2>
          <button
            type="button"
            className="btn-ghost"
            aria-label="Refresh scenarios"
            onClick={() => {
              cache.invalidate('scenarios-tab')
              void load(true)
            }}
          >
            ↻
          </button>
        </div>
        <p className="text-sm text-ink-secondary">Load or remove previously saved what-if scenarios.</p>
      </div>
      {error ? <div className="text-sm text-ink-secondary">{error}</div> : null}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
        {loading ? (
          <>
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </>
        ) : null}
        {!loading && items.length === 0 ? (
          <div className="col-span-full text-center text-ink-secondary py-10">
            No saved scenarios yet. Run a financial model to save your first scenario.
          </div>
        ) : null}

        {items.map((scenario) => {
          const createdLabel = scenario.created_at
            ? new Date(scenario.created_at).toLocaleDateString('en-IN')
            : 'N/A'

          return (
            <article key={scenario.id} className="card-p">
              <div className="font-medium text-ink-primary">{scenario.name || 'Untitled'}</div>
              <div className="text-xs text-ink-secondary mt-1">Type: {scenario.tags?.[0] || 'Scenario'}</div>
              <div className="text-xs text-ink-secondary mt-1">Date: {createdLabel}</div>
              <div className="mt-3 flex items-center gap-2">
                <button className="btn-ghost" onClick={() => onLoad(scenario)}>Load</button>
                <button className="btn-ghost" onClick={() => onDelete(scenario.id)}>Delete</button>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
