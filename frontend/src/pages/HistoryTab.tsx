import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { TableSkeleton } from '@/components/skeletons/TableSkeleton'
import { useTabCache } from '@/hooks/useTabCache'
import type { HistoryRecord } from '@/types'

export function HistoryTab() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [rows, setRows] = useState<HistoryRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)
  const cache = useTabCache<HistoryRecord[]>()

  const load = async (force = false) => {
    if (!force) {
      const cached = cache.get('history-tab')
      if (cached) {
        setRows(cached)
        setError(null)
        setLoading(false)
        return
      }
    }
    setLoading(true)
    try {
      const data = await api.history()
      setRows(data)
      cache.set('history-tab', data)
      setError(null)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'History fetch failed'
      setRows([])
      setError(message)

      if (axios.isAxiosError(e) && e.response?.status === 401) {
        await logout()
        navigate('/login', { replace: true })
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const run = async () => {
      try {
        await load(false)
      } catch {
        setLoading(false)
      }
    }

    run()
  }, [logout, navigate])

  const filtered = useMemo(() => rows.filter((r) => r.compound_name.toLowerCase().includes(query.toLowerCase())), [rows, query])

  const resultClass = (score: number) => {
    if (score >= 0.7) return 'bg-[#DCFCE7] text-[#166534]'
    if (score >= 0.4) return 'bg-[#FEF3C7] text-[#92400E]'
    return 'bg-[#FEE2E2] text-[#991B1B]'
  }

  return (
    <section className="card-p space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-lg">Prediction History</h2>
          <p className="text-sm text-ink-secondary">Recent model outputs and outcomes.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn-ghost"
            aria-label="Refresh history"
            onClick={() => {
              cache.invalidate('history-tab')
              void load(true)
            }}
          >
            ↻
          </button>
          <input className="input max-w-xs" placeholder="Search by compound" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
      </div>
      {error ? <div className="text-sm text-ink-secondary">{error}</div> : null}
      {loading ? <TableSkeleton rows={8} /> : null}
      <div className="overflow-auto max-h-[420px]">
        {!loading ? (
        <table className="w-full text-sm">
          <thead className="text-ink-secondary">
            <tr>
              <th className="text-left py-2">Date</th>
              <th className="text-left">Compound ID</th>
              <th className="text-left">Score</th>
              <th className="text-left">Result</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-6 text-center text-ink-secondary">
                  No prediction history found. Run your first prediction to see results here.
                </td>
              </tr>
            ) : null}
            {filtered.map((r) => (
              <tr key={r.id} className="border-t border-[rgba(0,200,150,0.08)]">
                <td className="py-2 text-ink-secondary">{new Date(r.timestamp).toLocaleString('en-IN')}</td>
                <td>{r.id}</td>
                <td className="font-mono">{(r.probability * 100).toFixed(1)}%</td>
                <td>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${resultClass(r.probability)}`}>
                    {r.probability >= 0.7 ? 'PASS' : r.probability >= 0.4 ? 'CAUTION' : 'FAIL'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        ) : null}
      </div>
    </section>
  )
}
