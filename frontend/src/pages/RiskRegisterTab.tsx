import { useEffect, useState } from 'react'
import { Table } from 'antd'
import { api } from '@/services/api'
import { TableSkeleton } from '@/components/skeletons/TableSkeleton'

interface RiskRow {
  id?: string
  title?: string
  category?: string
  probability?: number
  impact?: number
  mitigation?: string
}

function levelTag(level: string) {
  if (level === 'High') return { bg: '#FEE2E2', color: '#991B1B' }
  if (level === 'Medium') return { bg: '#FEF3C7', color: '#92400E' }
  return { bg: '#DCFCE7', color: '#166534' }
}

function toBand(value: number | undefined) {
  const numeric = Number(value || 0)
  if (numeric >= 0.67 || numeric >= 67) return 'High'
  if (numeric >= 0.34 || numeric >= 34) return 'Medium'
  return 'Low'
}

export function RiskRegisterTab() {
  const [rows, setRows] = useState<RiskRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = async () => {
    try {
      setLoading(true)
      setError(false)
      const response = await api.riskRegister()
      setRows((response.items || []) as RiskRow[])
    } catch {
      setError(true)
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const columns = [
    {
      title: 'Risk',
      dataIndex: 'title',
      key: 'title',
      render: (v: string | undefined) => v || '—',
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (v: string | undefined) => v || '—',
    },
    {
      title: 'Likelihood',
      dataIndex: 'probability',
      key: 'probability',
      render: (v: number | undefined) => {
        const band = toBand(v)
        const style = levelTag(band)
        return (
          <span style={{ background: style.bg, color: style.color, padding: '2px 8px', borderRadius: 999 }}>
            {band}
          </span>
        )
      },
    },
    {
      title: 'Impact',
      dataIndex: 'impact',
      key: 'impact',
      render: (v: number | undefined) => {
        const band = toBand(v)
        const style = levelTag(band)
        return (
          <span style={{ background: style.bg, color: style.color, padding: '2px 8px', borderRadius: 999 }}>
            {band}
          </span>
        )
      },
    },
    {
      title: 'Mitigation',
      dataIndex: 'mitigation',
      key: 'mitigation',
      render: (v: string | undefined) => v || '—',
    },
  ]

  if (error) {
    return <div className="card-p text-ink-secondary">Risk data could not be loaded.</div>
  }

  return (
    <section className="space-y-3">
      <div className="card-p">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-display text-lg">Risk Register</h2>
          <button type="button" className="btn-ghost" aria-label="Refresh risk register" onClick={() => void load()}>
            ↻
          </button>
        </div>
        <p className="text-sm text-ink-secondary">Operational and strategic risks with mitigation coverage.</p>
      </div>
      {loading ? <TableSkeleton rows={5} /> : null}
      <Table
        rowKey={(record) => record.id || `${record.title || 'risk'}-${record.category || 'cat'}`}
        columns={columns}
        dataSource={rows}
        pagination={{ pageSize: 8 }}
        loading={loading}
      />
    </section>
  )
}
